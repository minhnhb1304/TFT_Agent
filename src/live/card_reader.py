"""Doc TEN LOI tren mot o cua man chon augment (moc M1).

Hai ban, cung mot giao dien, chon bang config `live.card_reader`:

    OcrCardReader     - OCR tieng Viet + khop ten, chay cuc bo, khong cham mang.
    GeminiCardReader  - boc AugmentReader san co (Gemini Vision, co cache aHash).

Vi sao la Protocol chu khong phai mot lop duy nhat: ca hai deu co diem yeu
khac nhau, va cach duy nhat de biet ban nao tot hon tren mot ban record la
doi duoc chung tren CUNG bo nhan (scripts/eval_playtest.py).

DOC THEO TUNG O, khong doc ca man: sau mot lan reroll chi mot o doi, doc lai
ca ba la lang phi va - voi Gemini - la tra tien ba lan cho mot o.
"""

from __future__ import annotations

import difflib
import re
import time
from typing import Any, Protocol, Sequence

import numpy as np

from ..capture.regions import ScreenRegions
from ..knowledge.augment_catalog import normalize
from ..knowledge.name_index import NameIndex
from ..vision.augment_reader import AugmentReader, CardRead

SCREEN = "augment_select"
SLOTS = 3

# OCR tieng Viet hay roi dau ("Bai Hc So Khai"), nen sau khop chinh xac va khop
# theo goc van con mot buoc khop gan dung. Nguong CHAT: mot goi y sai ma trong
# co ve dung con te hon la khong doc duoc, vi nguoi choi khong co cach nao biet.
FUZZY_CUTOFF = 0.82
TRAIT_COUNT = re.compile(r"^\d$")
TRAIT_NOISE = re.compile(r"[/>]")


def resolve_name(
    lines: Sequence[str], index: NameIndex, namespace: str = "augments", cutoff: float = FUZZY_CUTOFF
) -> list[str]:
    """Cac dong OCR -> apiName. Rong = khong doan.

    Thu dong dau VA dong dau ghep dong ke: ten dai xuong hai dong la chuyen
    thuong gap, va bo cu chi lay `texts[0]` nen doc thieu.
    Ten ung voi HAI apiName tra ve ca hai - do la cap map mo that su.
    """
    texts = [x.strip() for x in lines if x and x.strip()]
    if not texts:
        return []
    candidates = [texts[0]] + ([f"{texts[0]} {texts[1]}"] if len(texts) > 1 else [])

    for text in candidates:
        hits = index.resolve(text, namespace, "vi")
        if hits:
            return hits
    for text in candidates:
        if len(normalize(text)) >= 4:
            hits = index.resolve_stem(text, namespace, "vi")
            if hits:
                return hits

    table = index.by_norm.get(namespace, {}).get("vi", {})
    best, best_ratio = None, cutoff
    for text in candidates:
        norm = normalize(text)
        for name in difflib.get_close_matches(norm, table.keys(), n=1, cutoff=cutoff):
            ratio = difflib.SequenceMatcher(None, norm, name).ratio()
            if ratio >= best_ratio:
                best, best_ratio = name, ratio
    return list(table[best]) if best else []


class CardReader(Protocol):
    """Giao dien ma LiveSession phu thuoc vao."""

    name: str

    def read_slot(self, frame: np.ndarray, slot: int) -> CardRead: ...

    def read_traits(self, frame: np.ndarray) -> dict[str, int]: ...


class OcrCardReader:
    """OCR o chu cua the roi khop voi NameIndex."""

    name = "ocr"

    def __init__(
        self,
        regions: ScreenRegions,
        name_index: NameIndex,
        *,
        ocr: Any | None = None,
        cutoff: float = FUZZY_CUTOFF,
    ) -> None:
        self.regions = regions
        self.name_index = name_index
        self.cutoff = cutoff
        self._ocr = ocr

    @property
    def ocr(self) -> Any:
        if self._ocr is None:
            from ..vision.ocr_engine import engine  # noqa: PLC0415 - nap tre, model nang

            self._ocr = engine()
        return self._ocr

    def read_slot(self, frame: np.ndarray, slot: int) -> CardRead:
        from ..vision.preprocess import ocr_texts  # noqa: PLC0415

        crop = self.regions.crop(frame, SCREEN, f"card_text_{slot}")
        texts = [t for t in ocr_texts(self.ocr(crop)) if t.strip()]
        raw_title = texts[0] if texts else ""
        body = " ".join(texts[1:])

        api_names = resolve_name(texts, self.name_index, "augments", self.cutoff)
        if not api_names:
            return CardRead(
                slot=slot,
                title=raw_title,
                body=body,
                api_names=(),
                confidence=0.0,
                reason=(f"không khớp tên nào (OCR đọc: {raw_title!r})" if raw_title
                        else "OCR không đọc được chữ nào trên thẻ"),
            )

        display = self.name_index.display_name(api_names[0], "augments", "vi") or raw_title
        ambiguous = len(api_names) > 1
        return CardRead(
            slot=slot,
            title=display,
            body=body,
            api_names=tuple(api_names),
            confidence=0.6 if ambiguous else 1.0,
            reason=(f"OCR {raw_title!r} khớp {display}"
                    + (" — cặp trùng tên, giữ cả hai" if ambiguous else "")),
        )

    def read_traits(self, frame: np.ndarray) -> dict[str, int]:
        """Doc bang toc/he ben trai: OCR tra ve so va ten xen ke nhau.

        Vi du that tren ban record: ['5', '3', 'Mat Tri', '3/3', '2', 'Lien Kich',
        '2 > 3 > 4']. So dung TRUOC ten la so don vi dang co; token kieu '3/3'
        hay '2 > 3 > 4' la moc kich hoat, khong phai so luong.
        """
        from ..vision.preprocess import ocr_texts  # noqa: PLC0415

        try:
            crop = self.regions.crop(frame, "hud", "traits")
        except Exception:                                   # noqa: BLE001 - thieu ROI thi bo qua
            return {}

        out: dict[str, int] = {}
        count: int | None = None
        for token in (t.strip() for t in ocr_texts(self.ocr(crop))):
            if not token:
                continue
            if TRAIT_COUNT.fullmatch(token):
                count = int(token)
                continue
            if TRAIT_NOISE.search(token) or token.isdigit():
                continue
            if count is None:
                continue
            hits = resolve_name([token], self.name_index, "traits", self.cutoff)
            if len(hits) == 1:
                out[hits[0]] = count
                count = None
        return out


class GeminiCardReader:
    """Boc AugmentReader: doc ca man mot lan, phuc vu tung o tu ket qua do.

    AugmentReader da co cache aHash rieng, nen goi `read_slot` ba lan tren cung
    mot khung khong ton ba lan goi mang. Cache cua chinh lop nay chi de khong
    bam lai aHash ba lan.
    """

    name = "gemini"

    def __init__(self, reader: AugmentReader) -> None:
        self.reader = reader
        self._last_key: int | None = None
        self._last: Any = None

    def _reading(self, frame: np.ndarray) -> Any:
        key = int(frame.sum())      # dinh danh re cho "van la khung vua roi"
        if key != self._last_key or self._last is None:
            t0 = time.perf_counter()
            self._last = self.reader.read(frame)
            self._last_key = key
            self.last_latency_ms = (time.perf_counter() - t0) * 1000.0
        return self._last

    def read_slot(self, frame: np.ndarray, slot: int) -> CardRead:
        reading = self._reading(frame)
        for card in reading.cards:
            if card.slot == slot:
                return card
        return CardRead(slot, "", "", (), 0.0, f"Gemini không trả về ô {slot + 1}")

    def read_traits(self, frame: np.ndarray) -> dict[str, int]:
        return dict(self._reading(frame).traits)
