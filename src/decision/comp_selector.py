"""Comp Selection Algorithm - SPEC 3.5.2.

Vai tro kep:
    1. Tu van huong doi hinh cho nguoi choi (top 3 + huong chuyen tiep).
    2. CAP DU LIEU CHO BoardFit: comp dang theo la thu cho biet trait nao dang
       thuc su quan trong. Do la ly do no la uu tien 2 ngay sau augment advisor.

Diem = 0.40*unit + 0.25*item + 0.23*meta + 0.12*augment  (+ contest o Phase 7)
Tat ca trong so doc tu config/scoring_weights.yaml, KHONG hardcode.

DO ON DINH HUONG: cong diem cho khuyen nghi truoc do va tru diem khi pivot doi
hoi ban qua nhieu unit. Khong co no, advisor se doi huong moi vong theo nhung
dao dong nho cua diem so - va mot advisor lat lat nhu the con te hon khong co.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..game_state.models import GameState
from ..knowledge.comp_database import CompDatabase, MetaComp
from .contest_analyzer import ContestResult, analyze as analyze_contest
from .scoring.types import ScoringConfig, clamp01

DEFAULT_WEIGHTS = {"unit": 0.40, "item": 0.25, "meta": 0.23, "augment": 0.12, "contest": 0.20}
DEFAULT_STABILITY = {
    "same_direction_bonus": 0.15,
    "same_direction_min_score": 0.60,
    "pivot_penalty": 0.10,
    "pivot_sell_threshold": 3,
    "pivot_flag_below": 0.30,
}


@dataclass
class CompScore:
    """Diem cua mot comp kem tach bach tung thanh phan."""

    comp: MetaComp
    total: float
    parts: dict[str, float] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)
    contest: ContestResult | None = None
    missing_units: list[str] = field(default_factory=list)
    sell_count: int = 0

    @property
    def name(self) -> str:
        return self.comp.name

    def transition_guide(self) -> str:
        """Huong chuyen tiep: giu gi, tim gi, ban bao nhieu."""
        if not self.missing_units:
            return "Đã đủ đội hình lõi — tập trung nâng sao và trang bị"
        need = ", ".join(self.missing_units[:4])
        tail = f"; cần bán {self.sell_count} đơn vị" if self.sell_count else ""
        return f"Cần thêm: {need}{tail}"


@dataclass
class CompAdvice:
    """Ket qua tu van huong doi hinh."""

    top: list[CompScore] = field(default_factory=list)
    should_pivot: bool = False
    note: str = ""

    @property
    def best(self) -> CompScore | None:
        return self.top[0] if self.top else None

    def target_traits(self) -> dict[str, int]:
        """Trait cua comp dang nham toi - dau vao cho BoardFit."""
        return dict(self.best.comp.traits) if self.best else {}


class CompSelector:
    """Xep hang huong doi hinh theo board hien tai."""

    def __init__(
        self,
        database: CompDatabase | None = None,
        config: ScoringConfig | None = None,
        enable_scouting: bool = False,
    ) -> None:
        self.database = database or CompDatabase()
        cfg = config or ScoringConfig.default()
        raw = dict(DEFAULT_WEIGHTS)
        raw.update(cfg.tuning.get("comp_selector", {}) or {})
        self.stability = dict(DEFAULT_STABILITY)
        self.stability.update(raw.pop("stability", {}) or {})
        self.weights = {k: float(v) for k, v in raw.items()}
        self.enable_scouting = enable_scouting

    # -- tung thanh phan ---------------------------------------------------

    @staticmethod
    def unit_score(comp: MetaComp, owned: set[str]) -> tuple[float, list[str]]:
        """Ti le core unit da co. Tra kem danh sach con thieu de dan duong."""
        if not comp.core_units:
            return 0.0, []
        core = {u.lower(): u for u in comp.core_units}
        have = {k for k in core if k in owned}
        missing = [core[k] for k in core if k not in have]
        return len(have) / len(core), missing

    @staticmethod
    def item_score(comp: MetaComp, state: GameState) -> float:
        """Do khop giua trang bi dang co va trang bi loi cua comp.

        Tinh tren item DA GHEP thoi. Component roi chua noi len huong gi, va
        doan huong tu component la kieu suy dien de sai.
        """
        if not comp.core_items:
            return 0.0
        owned = {i.lower() for i in state.completed_items}
        core = {i.lower() for i in comp.core_items}
        return len(owned & core) / len(core)

    @staticmethod
    def meta_score(comp: MetaComp) -> float:
        """Chuan hoa top4_rate. Comp khong co co mau -> keo ve trung tinh.

        Nguong 200 tran giong nguong cua AugmentStats: duoi muc do, chenh lech
        top4 giua cac comp nho hon sai so cua chinh phep do.
        """
        raw = clamp01((comp.top4_rate - 0.4) / 0.3)
        trust = clamp01(comp.sample_n / 200) if comp.sample_n else 0.0
        return 0.5 + (raw - 0.5) * trust

    @staticmethod
    def augment_score(comp: MetaComp, state: GameState) -> float:
        """Ti le augment dang cam nam trong danh sach augment tot cua comp."""
        if not comp.best_augments or not state.augments:
            return 0.0
        best = {a.lower() for a in comp.best_augments}
        have = {a.lower() for a in state.augments}
        return len(best & have) / len(have) if have else 0.0

    # -- tong hop ----------------------------------------------------------

    def score_comp(
        self, comp: MetaComp, state: GameState, previous: str | None = None
    ) -> CompScore:
        owned = {c.name.lower() for c in state.board + state.bench}
        unit, missing = self.unit_score(comp, owned)
        item = self.item_score(comp, state)
        meta = self.meta_score(comp)
        augment = self.augment_score(comp, state)

        parts = {"unit": unit, "item": item, "meta": meta, "augment": augment}
        total = sum(self.weights.get(k, 0.0) * v for k, v in parts.items())

        contest = analyze_contest(comp, state, enabled=self.enable_scouting)
        if contest.score:
            parts["contest"] = contest.score
            total += self.weights.get("contest", 0.0) * contest.score

        reasons = [
            f"Đã có {int(unit * len(comp.core_units))}/{len(comp.core_units)} đơn vị lõi",
        ]
        if item:
            reasons.append(f"Trang bị khớp {item:.0%} bộ lõi")
        if comp.sample_n:
            reasons.append(
                f"Top4 {comp.top4_rate:.0%} (n={comp.sample_n}, nguồn: {comp.source})"
            )
        else:
            reasons.append(f"Chưa có cỡ mẫu cho comp này (nguồn: {comp.source})")
        if contest.is_contested:
            reasons.append(contest.reason)

        # Do on dinh huong: chi thuong khi comp cu VAN con du tot.
        sell_count = self._sell_count(comp, state)
        if previous == comp.name and total >= self.stability["same_direction_min_score"]:
            total += self.stability["same_direction_bonus"]
            reasons.append("Giữ nguyên hướng đang đi — tránh đổi hướng vô cớ")
        elif previous and previous != comp.name and sell_count > self.stability["pivot_sell_threshold"]:
            total -= self.stability["pivot_penalty"]
            reasons.append(f"Đổi hướng sẽ phải bán {sell_count} đơn vị")

        return CompScore(
            comp=comp,
            total=clamp01(total),
            parts=parts,
            reasons=reasons,
            contest=contest,
            missing_units=missing,
            sell_count=sell_count,
        )

    @staticmethod
    def _sell_count(comp: MetaComp, state: GameState) -> int:
        """So unit tren san khong nam trong comp dich - chi phi cua mot lan pivot."""
        keep = {u.lower() for u in comp.core_units + comp.flex_units}
        return sum(1 for c in state.board if c.name.lower() not in keep)

    def select(
        self, state: GameState, previous: str | None = None, top_n: int = 3
    ) -> CompAdvice:
        """Tra ve top N huong doi hinh, co co canh bao nen doi huong."""
        if self.database.is_empty:
            return CompAdvice(
                [], False, "Chưa có dữ liệu đội hình meta — bỏ qua tư vấn hướng"
            )

        scored = [self.score_comp(c, state, previous) for c in self.database]
        scored.sort(key=lambda s: (-s.total, s.name))

        should_pivot = False
        if previous:
            current = next((s for s in scored if s.name == previous), None)
            should_pivot = current is None or current.total < self.stability["pivot_flag_below"]

        note = f"Nguồn dữ liệu: {', '.join(self.database.sources)}"
        return CompAdvice(scored[:top_n], should_pivot, note)


def as_dict(advice: CompAdvice) -> dict[str, Any]:
    """Ket xuat cho ScenarioLogger / overlay."""
    return {
        "should_pivot": advice.should_pivot,
        "note": advice.note,
        "top": [
            {
                "name": s.name,
                "total": round(s.total, 4),
                "parts": {k: round(v, 4) for k, v in s.parts.items()},
                "reasons": s.reasons,
                "transition": s.transition_guide(),
            }
            for s in advice.top
        ],
    }
