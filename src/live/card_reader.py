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
import time
from typing import Any, Protocol

import numpy as np

from ..capture.regions import ScreenRegions
from ..knowledge.augment_catalog import normalize
from ..knowledge.name_index import NameIndex
from ..vision.augment_reader import AugmentReader, CardRead

SCREEN = "augment_select"
SLOTS = 3


class CardReader(Protocol):
    """Giao dien ma LiveSession phu thuoc vao."""

    name: str

    def read_slot(self, frame: np.ndarray, slot: int) -> CardRead: ...

    def read_traits(self, frame: np.ndarray) -> dict[str, int]: ...


class OcrCardReader:
    """OCR o chu cua the roi khop voi NameIndex.

    Hanh vi o M1 GIU NGUYEN nhu DynamicCardRecognizer cua run_replay.py
    (`d537eb0`): lay dong dau, khop gan dung nguong 0.45. Do la co y - M1 chi
    doi KIEN TRUC, con do chinh xac doc the do M2 sua, va bo nhan playtest
    dang la moc so sanh cho ca hai.
    """

    name = "ocr"

    def __init__(
        self,
        regions: ScreenRegions,
        name_index: NameIndex,
        *,
        ocr: Any | None = None,
        cutoff: float = 0.45,
    ) -> None:
        self.regions = regions
        self.name_index = name_index
        self.cutoff = cutoff
        self._ocr = ocr
        self.lookup: dict[str, tuple[str, str]] = {}
        for api_name, langs in name_index.display.get("augments", {}).items():
            display = langs.get("vi") or ""
            if display:
                self.lookup[normalize(display)] = (display, api_name)

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
        norm = normalize(raw_title)

        matches = difflib.get_close_matches(norm, self.lookup.keys(), n=1, cutoff=self.cutoff)
        if not matches:
            return CardRead(
                slot=slot,
                title=raw_title,
                body=body,
                api_names=(),
                confidence=0.0,
                reason=f"không khớp tên nào (OCR đọc: {raw_title!r})" if raw_title
                       else "OCR không đọc được chữ nào trên thẻ",
            )
        display, api_name = self.lookup[matches[0]]
        ratio = difflib.SequenceMatcher(None, norm, matches[0]).ratio()
        return CardRead(
            slot=slot,
            title=display,
            body=body,
            api_names=(api_name,),
            confidence=ratio,
            reason=f"OCR {raw_title!r} khớp {display} ({ratio:.2f})",
        )

    def read_traits(self, frame: np.ndarray) -> dict[str, int]:
        """Chua doc duoc toc/he tu OCR - M2 viec 0b. Tra ve rong chu KHONG doan."""
        return {}


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
