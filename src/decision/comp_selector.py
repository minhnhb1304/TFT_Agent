"""Comp Selection Algorithm - SPEC 3.5.2.

Vai tro kep:
    1. Tu van huong doi hinh cho nguoi choi (top 3 + huong chuyen tiep).
    2. CAP DU LIEU CHO BoardFit: comp dang theo la thu cho biet trait nao dang
       thuc su quan trong. Do la ly do no la uu tien 2 ngay sau augment advisor.

HAI CHE DO, chon bang `comp_selector.adaptive` trong scoring_weights.yaml:

    adaptive = false  -> trong so CO DINH cho moi comp o moi stage:
                         0.40*unit + 0.25*item + 0.23*meta + 0.12*augment
    adaptive = true   -> trong so theo KIEU DOI HINH x GIAI DOAN (comp_signals):
                         reroll chot bang tuong loi; fast 8/9 giu board tam va
                         chot bang loai do + an cho toi luc xoay bai.

Che do co dinh duoc GIU LAI co chu dich: no la dong doi chung cua ablation
"trong so co dinh vs trong so theo kieu doi hinh" (SPEC 12.4). Comp khong
xac dinh duoc kieu doi hinh cung roi ve che do nay.

DO ON DINH HUONG: cong diem cho khuyen nghi truoc do va tru diem khi pivot doi
hoi ban qua nhieu unit. Khong co no, advisor se doi huong moi vong theo nhung
dao dong nho cua diem so - va mot advisor lat lat nhu the con te hon khong co.
Rieng fast 8/9 KHONG bi tru: ban ca board khi xoay bai la ke hoach cua no.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from ..game_state.models import GameState
from ..knowledge.comp_database import CompDatabase, MetaComp
from .comp_signals import (
    FAST_ARCHETYPES,
    PivotReadiness,
    emblem_trait,
    is_emblem,
    item_profile,
    pivot_readiness,
    resolve_archetype,
)
from .contest_analyzer import ContestResult, analyze as analyze_contest
from .item_advisor import ItemRecipes
from .scoring.board_fit import trait_key
from .scoring.types import ScoringConfig, clamp01

DEFAULT_WEIGHTS = {"unit": 0.40, "item": 0.25, "meta": 0.23, "augment": 0.12, "contest": 0.20}
DEFAULT_STABILITY = {
    "same_direction_bonus": 0.15,
    "same_direction_min_score": 0.60,
    "pivot_penalty": 0.10,
    "pivot_sell_threshold": 3,
    "pivot_flag_below": 0.30,
}
# Moi con so duoi day la GIA DINH TIEN NGHIEM tu kinh nghiem nguoi choi hang
# cao, chua fit tren du lieu. Ban chinh thuc nam o config/scoring_weights.yaml.
DEFAULT_ADAPTIVE: dict[str, Any] = {
    "adaptive": True,
    "profiles": {
        "reroll": {"unit": 0.40, "item": 0.20, "emblem": 0.10, "meta": 0.20, "augment": 0.10},
        "fast_holding": {"unit": 0.00, "item": 0.40, "emblem": 0.15, "meta": 0.30, "augment": 0.15},
        "fast_pivoted": {"unit": 0.35, "item": 0.25, "emblem": 0.10, "meta": 0.20, "augment": 0.10},
    },
    "pivot": {
        "fast8": {"window_start": "4-1", "deadline": "4-5", "target_level": 8},
        "fast9": {"window_start": "4-2", "deadline": "5-1", "target_level": 9},
    },
    "economy": {
        "xp_per_buy": 4,
        "gold_per_buy": 4,
        "xp_to_next": {2: 2, 3: 6, 4: 10, 5: 20, 6: 36, 7: 56, 8: 64, 9: 64},
    },
    "item_type": {"component_weight": 0.3, "full_mass": 2.0, "exact_match_weight": 0.2},
    "emblem": {"top4_low": 0.40, "top4_high": 0.70, "min_sample_n": 200},
    "commitment": {"min_evidence": 0.25, "lean_margin": 0.05, "lock_margin": 0.12},
}
ARCHETYPE_LABEL = {"reroll": "Reroll", "fast8": "Fast 8", "fast9": "Fast 9"}
BOARD_PARTS = ("unit", "item", "emblem", "augment")

COMMIT_NONE = "chưa nên chốt"
COMMIT_LEAN = "nghiêng về"
COMMIT_LOCK = "chốt"


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
    archetype: str = ""
    readiness: float | None = None        # fast 8/9: du tien xoay bai den dau (hien thi)
    pivoted: bool | None = None           # fast 8/9: da xoay that chua (doi trong so)
    weights: dict[str, float] = field(default_factory=dict)
    # Muc do board THAT SU ung ho comp nay (bo phan meta - meta giong nhau voi
    # moi board nen khong phai tin hieu ve van dau dang choi).
    evidence: float = 0.0

    @property
    def name(self) -> str:
        return self.comp.name

    def transition_guide(self) -> str:
        """Huong chuyen tiep: giu gi, tim gi, ban bao nhieu."""
        if not self.missing_units:
            return "Đã đủ đội hình lõi — tập trung nâng sao và trang bị"
        need = ", ".join(self.missing_units[:4])
        if self.archetype in FAST_ARCHETYPES and not self.pivoted:
            return f"Khi xoay bài tìm: {need}"
        tail = f"; cần bán {self.sell_count} đơn vị" if self.sell_count else ""
        return f"Cần thêm: {need}{tail}"


@dataclass
class CompAdvice:
    """Ket qua tu van huong doi hinh."""

    top: list[CompScore] = field(default_factory=list)
    should_pivot: bool = False
    note: str = ""
    commitment: str = COMMIT_NONE
    commitment_reason: str = ""

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
        recipes: ItemRecipes | None = None,
        unit_costs: Mapping[str, int] | None = None,
        item_stats: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> None:
        self.database = database or CompDatabase()
        cfg = config or ScoringConfig.default()
        raw = dict(DEFAULT_WEIGHTS)
        raw.update(cfg.tuning.get("comp_selector", {}) or {})
        self.stability = dict(DEFAULT_STABILITY)
        self.stability.update(raw.pop("stability", {}) or {})
        self.adaptive = bool(raw.pop("adaptive", DEFAULT_ADAPTIVE["adaptive"]))
        self.tune = {
            key: {**DEFAULT_ADAPTIVE[key], **(raw.pop(key, None) or {})}
            for key in ("profiles", "pivot", "economy", "item_type", "emblem", "commitment")
        }
        self.weights = {k: float(v) for k, v in raw.items()}
        self.enable_scouting = enable_scouting
        self.recipes = recipes or ItemRecipes()
        self.unit_costs = dict(unit_costs or {})
        self.item_stats = dict(item_stats or {})

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
        """Do khop TEN giua trang bi dang co va trang bi loi cua comp.

        Tinh tren item DA GHEP thoi. Che do co dinh dung thang cai nay; che do
        theo kieu doi hinh chi dung no lam phan thuong nho (item_type_score).
        """
        if not comp.core_items:
            return 0.0
        owned = {i.lower() for i in state.completed_items}
        core = {i.lower() for i in comp.core_items}
        return len(owned & core) / len(core)

    def item_type_score(self, comp: MetaComp, state: GameState) -> tuple[float, str, bool]:
        """Do khop LOAI do (AP/AD) giua board va comp. Do tank khong chi huong.

        Returns: (diem, ly do, board co do tan cong de noi len huong khong).
        """
        tune = self.tune["item_type"]
        weight = float(tune["component_weight"])
        player = item_profile(state.completed_items, state.item_components, self.recipes, weight)
        target = item_profile(comp.core_items, (), self.recipes, weight)

        if target.ap_share is None:
            type_score, reason = 0.5, "Không có dữ liệu đồ tấn công của đội hình"
        elif player.mass == 0:
            type_score, reason = 0.5, "Chưa có đồ tấn công — đồ chưa nói lên hướng"
        else:
            match = 1.0 - abs(player.ap_share - target.ap_share)
            confidence = clamp01(player.mass / float(tune["full_mass"]))
            type_score = 0.5 + (match - 0.5) * confidence
            reason = f"Đồ đang nghiêng {player.lean}, đội hình cần {target.lean}"

        exact_weight = float(tune["exact_match_weight"])
        score = (1.0 - exact_weight) * type_score + exact_weight * self.item_score(comp, state)
        return clamp01(score), reason, player.mass > 0

    def emblem_score(self, comp: MetaComp, state: GameState) -> tuple[float, str]:
        """An khop trait cua comp -> 0.5..1.0 theo do manh thong ke. Khong khop -> 0."""
        tune = self.tune["emblem"]
        comp_traits = {trait_key(t) for t in comp.traits}
        best, best_reason = 0.0, ""
        for item in state.completed_items:
            if not is_emblem(item) or emblem_trait(item) not in comp_traits:
                continue
            stats = self.item_stats.get(item) or {}
            count = int(stats.get("count") or 0)
            if count:
                low, high = float(tune["top4_low"]), float(tune["top4_high"])
                raw = clamp01((float(stats.get("top4_rate", 0.0)) - low) / (high - low))
                trust = clamp01(count / float(tune["min_sample_n"]))
                quality = 0.5 + (raw - 0.5) * trust
                detail = f"top4 {float(stats.get('top4_rate', 0.0)):.0%}, n={count}"
            else:
                quality = 0.5
                detail = "chưa có số liệu thống kê của ấn"
            score = 0.5 + 0.5 * quality
            if score > best:
                best, best_reason = score, f"Có ấn {item} khớp tộc/hệ của đội hình ({detail})"
        return best, best_reason

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

    # -- trong so theo kieu doi hinh -----------------------------------------

    def _adaptive_weights(
        self, archetype: str, readiness: PivotReadiness | None
    ) -> dict[str, float]:
        profiles = self.tune["profiles"]
        if archetype not in FAST_ARCHETYPES:
            return {k: float(v) for k, v in profiles["reroll"].items()}
        phase = "fast_pivoted" if readiness and readiness.pivoted else "fast_holding"
        return {k: float(v) for k, v in profiles[phase].items()}

    @staticmethod
    def _evidence(
        parts: dict[str, float],
        weights: dict[str, float],
        present: dict[str, bool],
        adaptive: bool,
    ) -> float:
        """Board ung ho comp bao nhieu, chi tren nhung tin hieu board CO.

        Khong cam an hay chua co augment la THIEU tin hieu, khong phai bang
        chung chong lai comp - neu tinh chung vao mau so thi moi board dau tran
        deu bi xem la "chua co gi" du do da noi ro huong.
        """
        signal = dict(parts)
        if adaptive and "item" in signal:
            signal["item"] = max(0.0, signal["item"] - 0.5) * 2.0
        used = {
            k: weights.get(k, 0.0)
            for k in BOARD_PARTS
            if k in signal and present.get(k) and weights.get(k, 0.0) > 0.0
        }
        total = sum(used.values())
        return sum(w * signal[k] for k, w in used.items()) / total if total else 0.0

    # -- tong hop ----------------------------------------------------------

    def score_comp(
        self, comp: MetaComp, state: GameState, previous: str | None = None
    ) -> CompScore:
        owned = {c.name.lower() for c in state.board + state.bench}
        unit, missing = self.unit_score(comp, owned)
        meta = self.meta_score(comp)
        augment = self.augment_score(comp, state)

        archetype = resolve_archetype(comp) if self.adaptive else ""
        reasons: list[str] = []
        readiness: PivotReadiness | None = None

        item_signal = False
        if archetype:
            item, item_reason, item_signal = self.item_type_score(comp, state)
            emblem, emblem_reason = self.emblem_score(comp, state)
            parts = {"unit": unit, "item": item, "emblem": emblem, "meta": meta, "augment": augment}
            if archetype in FAST_ARCHETYPES:
                readiness = pivot_readiness(
                    archetype, state, missing, self.unit_costs,
                    self.tune["pivot"], self.tune["economy"],
                )
            weights = self._adaptive_weights(archetype, readiness)

            reasons.append(f"Kiểu đội hình: {ARCHETYPE_LABEL[archetype]}")
            if readiness and readiness.reason:
                reasons.append(readiness.reason)
            if weights.get("unit", 0.0) > 0.0:
                reasons.append(f"Đã có {round(unit * len(comp.core_units))}/{len(comp.core_units)} đơn vị lõi")
            reasons.append(item_reason)
            if emblem_reason:
                reasons.append(emblem_reason)
        else:
            parts = {
                "unit": unit, "item": self.item_score(comp, state),
                "meta": meta, "augment": augment,
            }
            weights = {k: self.weights.get(k, 0.0) for k in parts}
            reasons.append(f"Đã có {round(unit * len(comp.core_units))}/{len(comp.core_units)} đơn vị lõi")
            if parts["item"]:
                reasons.append(f"Trang bị khớp {parts['item']:.0%} bộ lõi")

        total = sum(weights.get(k, 0.0) * v for k, v in parts.items())
        present = {
            "unit": True,
            "item": item_signal if archetype else bool(state.completed_items),
            "emblem": any(is_emblem(i) for i in state.completed_items),
            "augment": bool(state.augments),
        }
        evidence = self._evidence(parts, weights, present, adaptive=bool(archetype))

        contest = analyze_contest(comp, state, enabled=self.enable_scouting)
        if contest.score:
            parts["contest"] = contest.score
            total += self.weights.get("contest", 0.0) * contest.score

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
        elif (
            previous
            and previous != comp.name
            and archetype not in FAST_ARCHETYPES
            and sell_count > self.stability["pivot_sell_threshold"]
        ):
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
            archetype=archetype,
            readiness=readiness.value if readiness else None,
            pivoted=readiness.pivoted if readiness else None,
            weights=weights,
            evidence=evidence,
        )

    @staticmethod
    def _sell_count(comp: MetaComp, state: GameState) -> int:
        """So unit tren san khong nam trong comp dich - chi phi cua mot lan pivot."""
        keep = {u.lower() for u in comp.core_units + comp.flex_units}
        return sum(1 for c in state.board if c.name.lower() not in keep)

    def commitment(self, scored: list[CompScore]) -> tuple[str, str]:
        """Muc do chot bai: tin hieu tren board ro den dau va hon huong #2 bao xa."""
        if not scored:
            return COMMIT_NONE, ""
        tune = self.tune["commitment"]
        best = scored[0]
        if best.evidence < float(tune["min_evidence"]):
            return COMMIT_NONE, "Tín hiệu trên board còn yếu — thứ hạng mới chỉ dựa vào số liệu meta"
        margin = best.total - scored[1].total if len(scored) > 1 else best.total
        if margin >= float(tune["lock_margin"]):
            return COMMIT_LOCK, f"{best.name} hơn hướng thứ hai {margin:.2f} điểm"
        if margin >= float(tune["lean_margin"]):
            return COMMIT_LEAN, f"{best.name} nhỉnh hơn hướng thứ hai {margin:.2f} điểm"
        second = scored[1]
        if best.archetype in FAST_ARCHETYPES and best.archetype == second.archetype and not best.pivoted:
            return COMMIT_NONE, (
                f"Các hướng đầu cùng kiểu {ARCHETYPE_LABEL[best.archetype]} — đồ đã đúng hướng, "
                "giữ board tạm và chọn đội hình cụ thể khi xoay bài"
            )
        return COMMIT_NONE, f"Hai hướng đầu sát điểm ({margin:.2f}) — chờ thêm tín hiệu"

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

        level, level_reason = self.commitment(scored)
        note = f"Nguồn dữ liệu: {', '.join(self.database.sources)}"
        return CompAdvice(scored[:top_n], should_pivot, note, level, level_reason)


def as_dict(advice: CompAdvice) -> dict[str, Any]:
    """Ket xuat cho ScenarioLogger / overlay."""
    return {
        "should_pivot": advice.should_pivot,
        "note": advice.note,
        "commitment": advice.commitment,
        "commitment_reason": advice.commitment_reason,
        "top": [
            {
                "name": s.name,
                "total": round(s.total, 4),
                "archetype": s.archetype,
                "readiness": None if s.readiness is None else round(s.readiness, 4),
                "pivoted": s.pivoted,
                "evidence": round(s.evidence, 4),
                "parts": {k: round(v, 4) for k, v in s.parts.items()},
                "weights": {k: round(v, 4) for k, v in s.weights.items()},
                "reasons": s.reasons,
                "transition": s.transition_guide(),
            }
            for s in advice.top
        ],
    }
