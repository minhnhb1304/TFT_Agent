"""Tach mot man chon augment trong video thanh cac offer on dinh - de SINH NHAN NHAP.

Day KHONG phai bo theo doi reroll cua san pham (do la M2, trong src/live/).
Nguong o day chi can du tot de nguoi gan nhan sua it: sai thi nguoi choi sua
tren file nhap, khong ai dung ket qua nay lam su that.

Thuat toan, cho moi mau (t, co man?, trang thai 3 nut, anh thu nho 3 o):
    1. Mau "yen" = khong o nao lech qua `settle_thr` so voi mau truoc. Do tren
       VOD s7h-jHMpFmQ: the dung yen lech <= 0.6, doi chu khi reroll 6-12, the
       dang lat 20-90. Nguong doi chu va nguong yen vi the phai TACH RIENG.
    2. >= `stable_n` mau yen lien tiep = mot trang thai the da hien xong.
    3. Tin hieu reroll CHINH la nut: o i chuyen active -> pressed/disabled.
       (Roll hai o lien tay cach nhau ~0.8 s, nen sau khi bam chi doi 2 mau yen.)
       Trang thai yen dau tien sau do MA o i da doi noi dung = offer moi,
       rerolled_slot = i. Phai cho o i doi: tren record cua nguoi choi the lat
       lau hon 3 mau, chot som thi offer moi van mang the cu.
    4. Du phong: noi dung lech >= `change_thr` so voi offer da chot ma khong
       co su kien nut -> van la offer moi, KHONG gan rerolled_slot.
    5. Man dong (hoac hinh nhap nhay) truoc khi the kip yen ma van co man chua
       chot / o da bam chua chot -> lay mau IT CHUYEN DONG NHAT, settled=False.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from typing import Iterable, Sequence

import numpy as np

from ..knowledge.augment_catalog import normalize
from ..knowledge.name_index import NameIndex

THUMB_SIZE = (48, 12)     # (w, h) - du thay chu doi, du nho de on dinh voi nhieu nen


@dataclass
class Sample:
    t: float
    present: bool
    thumbs: tuple[np.ndarray, ...] = ()     # 3 anh xam float32, cung kich thuoc
    buttons: tuple[str, ...] = ()           # trang thai nut tung o: active/pressed/disabled/unknown


@dataclass
class DraftOffer:
    at_s: float
    sample_index: int                        # mau dai dien de doc OCR / chup anh
    rerolled_slot: int | None = None
    changed_slots: list[int] = field(default_factory=list)
    settled: bool = True


@dataclass
class DraftScreen:
    open_s: float
    close_s: float
    offers: list[DraftOffer]


def make_thumb(gray_crop: np.ndarray) -> np.ndarray:
    import cv2

    return cv2.resize(gray_crop, THUMB_SIZE, interpolation=cv2.INTER_AREA).astype(np.float32)


def slot_diffs(a: Sequence[np.ndarray], b: Sequence[np.ndarray]) -> list[float]:
    """Do lech trung binh tuyet doi (0-255) cua tung o."""
    return [float(np.mean(np.abs(x - y))) for x, y in zip(a, b)]


def group_screens(times: Sequence[float], present: Sequence[bool], gap_s: float = 3.0) -> list[tuple[float, float]]:
    """Gom cac moc co man chon augment thanh khoang [open, close].

    Nguoi choi hay AN man chon augment de xem ban co roi mo lai (record 2026-09-16:
    khoang an 9-10 s). Mot vong chon van la MOT man - goi voi `gap_s` du lon.
    """
    spans: list[tuple[float, float]] = []
    for t, p in zip(times, present):
        if not p:
            continue
        if spans and t - spans[-1][1] <= gap_s:
            spans[-1] = (spans[-1][0], t)
        else:
            spans.append((t, t))
    return spans


def segment_screen(
    samples: Sequence[Sample], stable_n: int = 3, settle_thr: float = 2.0, change_thr: float = 4.0
) -> DraftScreen | None:
    """Tach mot chuoi mau (da cat quanh mot man) thanh cac offer."""
    shown = [i for i, s in enumerate(samples) if s.present and s.thumbs]
    if not shown:
        return None

    offers: list[DraftOffer] = []
    committed: tuple[np.ndarray, ...] | None = None
    pending: list[int] = []                 # o da bam reroll, chua chot offer moi
    since_change: list[int] = []            # mau co man ke tu lan chot / lan bam cuoi
    run_len = 0
    for n, cur in enumerate(shown):
        prev = shown[n - 1] if n else None
        # So nut voi mau CO MAN truoc do, ke ca khi giua chung hinh nhap nhay mat man.
        pressed = _pressed_slots(samples[prev].buttons, samples[cur].buttons) if prev is not None else []
        if pressed:
            pending += pressed
            since_change = []               # the doi SAU khi bam - khung truoc do la noi dung cu
        else:
            since_change.append(cur)
        # Vua bam: the chua kip doi, phai dem lai tu dau de khong chot noi dung cu.
        steady = (
            not pressed and prev is not None and cur == prev + 1
            and max(slot_diffs(samples[prev].thumbs, samples[cur].thumbs)) < settle_thr
        )
        run_len = run_len + 1 if steady else 1
        # Sau khi bam reroll chi can 2 mau yen: doi hai roll lien tay chi cach nhau
        # ~0.8 s, doi du stable_n thi roll thu hai bi nuot (record 2026-09-16, game 2 3-2).
        need = 2 if pending else stable_n
        if run_len < need:
            continue

        thumbs = samples[cur].thumbs
        at_s = samples[cur - need + 1].t
        if committed is None:
            offers.append(DraftOffer(at_s=at_s, sample_index=cur))
        elif pending:
            diffs = slot_diffs(committed, thumbs)
            if not any(diffs[i] >= change_thr for i in set(pending)):
                continue                    # da bam nhung the chua doi xong
            slots = sorted(set(pending))
            offers.append(DraftOffer(at_s, cur, slots[0] if len(slots) == 1 else None, slots))
        else:
            changed = [i for i, d in enumerate(slot_diffs(committed, thumbs)) if d >= change_thr]
            if not changed:
                committed = thumbs          # troi nhe (hover, hieu ung) - bam theo
                continue
            offers.append(DraftOffer(at_s, cur, None, changed))
        committed, pending, since_change = thumbs, [], []

    if committed is None or pending:
        best = _calmest(samples, since_change or shown[-1:])
        slots = sorted(set(pending))
        offers.append(
            DraftOffer(samples[best].t, best, slots[0] if len(slots) == 1 else None, slots, settled=False)
        )
    return DraftScreen(open_s=samples[shown[0]].t, close_s=samples[shown[-1]].t, offers=offers)


def _calmest(samples: Sequence[Sample], indices: Sequence[int]) -> int:
    """Mau lech it nhat so voi mau lien truoc - gan voi 'the da hien xong' nhat."""
    def motion(i: int) -> float:
        prev = samples[i - 1] if i > 0 else None
        if prev is None or not prev.thumbs:
            return float("inf")
        return max(slot_diffs(prev.thumbs, samples[i].thumbs))

    return min(indices, key=lambda i: (motion(i), -i))


def _pressed_slots(before: Sequence[str], after: Sequence[str]) -> list[int]:
    return [
        i for i, (a, b) in enumerate(zip(before, after))
        if a == "active" and b in ("pressed", "disabled")
    ]


def resolve_card_title(lines: Iterable[str], index: NameIndex, cutoff: float = 0.85) -> list[str]:
    """Goi y apiName tu cac dong OCR cua mot the. Rong = khong doan.

    Thu dong tieu de va tieu de ghep dong ke (ten dai xuong hai dong): khop
    chinh xac, roi khop theo goc (bo token tier), roi moi khop gan dung voi
    nguong CHAT. OCR tieng Viet hay roi dau ("Bai Hc So Khai") nen can buoc
    cuoi; nguong chat vi mot goi y sai ma trong co ve dung se neo nguoi gan nhan.
    """
    texts = [x.strip() for x in lines if x and x.strip()]
    if not texts:
        return []
    candidates = [texts[0]] + ([f"{texts[0]} {texts[1]}"] if len(texts) > 1 else [])
    for text in candidates:
        hits = index.resolve(text, "augments", "vi")
        if hits:
            return hits
    for text in candidates:
        if len(normalize(text)) >= 4:
            hits = index.resolve_stem(text, "augments", "vi")
            if hits:
                return hits
    table = index.by_norm.get("augments", {}).get("vi", {})
    best, best_ratio = None, cutoff
    for text in candidates:
        norm = normalize(text)
        for name in difflib.get_close_matches(norm, table.keys(), n=1, cutoff=cutoff):
            ratio = difflib.SequenceMatcher(None, norm, name).ratio()
            if ratio >= best_ratio:
                best, best_ratio = name, ratio
    return list(table[best]) if best else []
