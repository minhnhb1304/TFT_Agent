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

from ..decision import margin

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
    edge: str = ""                   # chenh lech do tach ve thanh phan (A2)

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
    sources: list[str] = field(default_factory=list)    # xuat xu bang diem - noi MOT lan
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
    shared, drop = _shared_reasons(slots)
    for s in slots:
        s.reasons = [r for r in s.reasons if r not in drop][:MAX_REASONS]

    verdict = _verdict(bundle, slots, ranking)
    for s in slots:
        s.recommended = verdict.slot is not None and s.slot == verdict.slot
    strip = _strip(event, bundle, shared)
    strip.sources = _sources(ranking)
    return strip, verdict, slots


def _sources(ranking) -> list[str]:
    """Xuat xu cua bang diem - giong het nhau tren moi the, nen noi MOT lan.

    Truoc khi tach ra, menh de nay nam trong chinh `reason` cua thanh phan
    `base` va lap nguyen van tren tung cot: 10/33 o tren nhan playtest. Bo
    han thi khong duoc - no la rao chan giua "y kien" va "so do".
    """
    out: list[str] = []
    for entry in getattr(ranking, "entries", []) or []:
        comp = entry.components.get("base")
        text = str((comp.detail or {}).get("caveat") or "") if comp else ""
        if text and text not in out:
            out.append(text)
    return out


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


def _shared_reasons(slots: Sequence[SlotVM]) -> tuple[list[str], set[str]]:
    """Cau dung cho TU HAI O TRO LEN - gom len dai trang thai.

    Nguong la HAI, khong phai "tat ca ba". Luat cu chi gom khi ca ba o deu co
    cau do, ma dang lap thuong gap nhat lai la HAI the cung bac ("Bac B theo
    bang tier") - no lot luoi va nguoi choi doc lai nguyen doan. Do duoc o
    buoc A3 tren nhan playtest: 30/66 o mang cau trung.

    Cau dung cho mot phan phai NOI RO O NAO. Khong noi thi dai trang thai
    dang phat bieu mot dieu sai ve o con lai - do la mot loi nang hon lap.

    Tra ve (dong hien tren dai, tap cau phai cat khoi cac cot).
    """
    scored = [s for s in slots if s.score is not None]
    if len(scored) < 2:
        return [], set()

    owners: dict[str, list[int]] = {}
    for s in scored:
        for reason in s.reasons:
            owners.setdefault(reason, []).append(s.slot)

    lines: list[str] = []
    drop: set[str] = set()
    for reason in (r for s in scored for r in s.reasons):    # giu thu tu xuat hien
        if reason in drop or len(owners[reason]) < 2:
            continue
        drop.add(reason)
        if len(owners[reason]) == len(scored):
            lines.append(reason)
        else:
            where = ", ".join(f"Ô {i + 1}" for i in owners[reason])
            lines.append(f"{where}: {reason}")
    return lines, drop


def _verdict(bundle, slots: Sequence[SlotVM], ranking=None) -> VerdictVM:
    advice = getattr(bundle, "reroll", None)
    ranked = sorted((s for s in slots if s.score is not None), key=lambda s: -s.score)
    delta = (ranked[0].score - ranked[1].score) if len(ranked) >= 2 else None
    # Cau nay noi ve XEP HANG, khong noi ve hanh dong - nen no dung ca khi
    # khuyen nghi la DOI.
    edge = margin.explain(margin.compare(ranking), ranking) if ranking is not None else ""

    if advice is None:
        if not ranked:
            return VerdictVM()
        best = ranked[0]
        return VerdictVM("CHỌN", best.slot, best.name, delta, edge=edge)

    slot = int(getattr(advice, "target_slot", 0))
    target = next((s for s in slots if s.slot == slot), None)
    action = "ĐỔI" if getattr(advice, "action", "PICK") == "REROLL" else "CHỌN"
    if action == "ĐỔI":
        gain = getattr(advice, "expected_gain", None)
        delta = float(gain) if gain is not None else None
    return VerdictVM(action, slot, target.name if target else "", delta,
                     str(getattr(advice, "reason", "") or ""), edge)


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
    note = str(getattr(event, "state_note", "") or "")
    if note:
        strip.shared = [note] + list(strip.shared)

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
