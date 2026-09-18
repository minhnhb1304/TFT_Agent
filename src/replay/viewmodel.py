"""Bien `AdviceReady` thanh du lieu de VE - thuan Python, khong Qt (moc M1b).

Tach ra vi hai ly do:
  - test duoc cach hien thi ma khong can dung cua so;
  - vo chi con viec do du lieu vao widget, khong tu tinh lai gi.

Hai quy tac trinh bay nam o day, khong nam trong widget:
  1. Cot xep theo O TREN MAN GAME, khong theo thu hang. Thu hang the hien bang
     thanh diem va vien vang - mat nhin tu game sang panel la khop.
  2. Cau ly do xuat hien o CA BA the bi gom len dai trang thai. Lap ba lan mot
     cau khong them thong tin, chi lam loang cai dang thuc su chi phoi.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

MAX_REASONS = 3
LOW_CONFIDENCE = 0.75


@dataclass
class SlotVM:
    """Mot cot the."""

    slot: int
    name: str
    api_name: str = ""
    tier: str = ""
    rarity: int | None = None
    score: float | None = None
    rank: int | None = None
    reasons: list[str] = field(default_factory=list)
    reroll: str = "unknown"          # available | used | unknown
    recommended: bool = False
    unread: bool = False
    ambiguous: bool = False
    low_confidence: bool = False
    raw_text: str = ""

    @property
    def score_text(self) -> str:
        return f"{self.score:.2f}" if self.score is not None else "—"


@dataclass
class VerdictVM:
    """Dai ket luan: dong tu truoc, chenh lech sau."""

    action: str = ""                 # CHỌN | ĐỔI
    slot: int | None = None
    name: str = ""
    delta: float | None = None       # chenh lech voi lua chon ke tiep
    note: str = ""

    @property
    def headline(self) -> str:
        if not self.action:
            return "chưa có khuyến nghị"
        where = f" Ô {self.slot + 1}" if self.slot is not None else ""
        return f"{self.action}{where} · {self.name}" if self.name else f"{self.action}{where}"

    @property
    def delta_text(self) -> str:
        if self.delta is None:
            return ""
        return f"hơn lựa chọn kế +{self.delta:.2f}" if self.delta >= 0 else f"kém {abs(self.delta):.2f}"


@dataclass
class StripVM:
    """Dai trang thai tran dau."""

    stage: str = "?"
    level: str = "?"
    xp: str = "?"
    gold: str = "?"
    hp: str = "?"
    streak: str = "?"
    rerolls_left: int | None = None
    unknown: list[str] = field(default_factory=list)
    econ: str = ""
    shared: list[str] = field(default_factory=list)     # cau ly do chung cua ca ba the
    warnings: list[str] = field(default_factory=list)

    @property
    def line(self) -> str:
        return (f"{self.stage}  ·  Cấp {self.level} ({self.xp} XP)  ·  {self.gold} vàng  "
                f"·  HP {self.hp}  ·  chuỗi {self.streak}")


def build_view(
    event: Any, rarity_of: Callable[[str], int | None] | None = None
) -> tuple[StripVM, VerdictVM, list[SlotVM]]:
    """`AdviceReady` -> (dai trang thai, dai ket luan, ba cot)."""
    bundle = getattr(event, "bundle", None)
    ranking = getattr(bundle, "ranking", None)
    entries = {e.api_name: e for e in getattr(ranking, "entries", [])}
    order = [e.api_name for e in getattr(ranking, "entries", [])]

    slots = _slots(event, entries, order, rarity_of)
    shared = _shared_reasons(slots)
    for s in slots:
        s.reasons = [r for r in s.reasons if r not in shared][:MAX_REASONS]

    verdict = _verdict(bundle, slots)
    for s in slots:
        s.recommended = verdict.slot is not None and s.slot == verdict.slot
    return _strip(event, bundle, shared), verdict, slots


def _slots(event, entries, order, rarity_of) -> list[SlotVM]:
    out: list[SlotVM] = []
    for card in getattr(event, "cards", []):
        api = card.api_names[0] if card.api_names else ""
        entry = entries.get(api)
        vm = SlotVM(
            slot=card.slot,
            name=(entry.name if entry else card.title) or "chưa đọc được",
            api_name=api,
            unread=not card.api_names,
            ambiguous=len(card.api_names) > 1,
            low_confidence=bool(card.api_names) and card.confidence < LOW_CONFIDENCE,
            raw_text=card.reason if not card.api_names else "",
            rarity=rarity_of(api) if rarity_of and api else None,
            reroll=_reroll_state(event, card.slot),
        )
        if entry is not None:
            vm.score = entry.total
            vm.rank = order.index(api) + 1
            vm.tier = str((entry.components.get("base").detail or {}).get("tier") or "") \
                if entry.components.get("base") else ""
            vm.reasons = list(entry.reasons)
        out.append(vm)
    return sorted(out, key=lambda s: s.slot)


def _reroll_state(event, slot: int) -> str:
    available = getattr(getattr(event, "rerolls", None), "available", ())
    if slot >= len(available) or available[slot] is None:
        return "unknown"
    return "available" if available[slot] else "used"


def _shared_reasons(slots: Sequence[SlotVM]) -> list[str]:
    """Cau xuat hien o MOI the co diem so - gom len dai trang thai."""
    scored = [s for s in slots if s.score is not None]
    if len(scored) < 2:
        return []
    common = set(scored[0].reasons)
    for s in scored[1:]:
        common &= set(s.reasons)
    return [r for r in scored[0].reasons if r in common]


def _verdict(bundle, slots: Sequence[SlotVM]) -> VerdictVM:
    advice = getattr(bundle, "reroll", None)
    ranked = sorted((s for s in slots if s.score is not None), key=lambda s: -s.score)
    delta = (ranked[0].score - ranked[1].score) if len(ranked) >= 2 else None

    if advice is None:
        if not ranked:
            return VerdictVM()
        best = ranked[0]
        return VerdictVM("CHỌN", best.slot, best.name, delta)

    slot = int(getattr(advice, "target_slot", 0))
    target = next((s for s in slots if s.slot == slot), None)
    action = "ĐỔI" if getattr(advice, "action", "PICK") == "REROLL" else "CHỌN"
    if action == "ĐỔI":
        gain = getattr(advice, "expected_gain", None)
        delta = float(gain) if gain is not None else None
    return VerdictVM(action, slot, target.name if target else "", delta,
                     str(getattr(advice, "reason", "") or ""))


def _strip(event, bundle, shared: list[str]) -> StripVM:
    state = getattr(event, "state", None)
    unknown = sorted(set(getattr(event, "never_seen", ())) | set(getattr(event, "stale_fields", ())))

    def show(field_name: str, value: Any) -> str:
        return "?" if field_name in unknown or value is None else str(value)

    strip = StripVM(
        stage=show("stage", getattr(state, "stage", None)),
        level=show("level", getattr(state, "level", None)),
        xp=f"{show('xp', getattr(state, 'xp', None))}/{show('xp_needed', getattr(state, 'xp_needed', None))}",
        gold=show("gold", getattr(state, "gold", None)),
        hp=show("hp", getattr(state, "hp", None)),
        streak=show("streak", getattr(state, "streak", None)),
        unknown=unknown,
        shared=shared,
    )
    economy = list(getattr(bundle, "economy", None) or [])
    strip.econ = " · ".join(str(getattr(a, "message", a)) for a in economy[:2])

    available = getattr(getattr(event, "rerolls", None), "available", ())
    if available:
        strip.rerolls_left = sum(1 for ok in available if ok is not False)
    if unknown:
        strip.warnings.append("số chưa đọc được: " + ", ".join(unknown))
    unread = [c.slot + 1 for c in getattr(event, "cards", []) if not c.api_names]
    if unread:
        strip.warnings.append("chưa đọc được ô " + ", ".join(map(str, unread)))
    stale = list(getattr(bundle, "stale_data", None) or [])
    if stale:
        strip.warnings.append(f"dữ liệu cũ hơn patch hiện tại ({len(stale)} bảng)")
    return strip
