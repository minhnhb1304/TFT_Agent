"""Doc the augment va toc/he tu man hinh chon augment (SPEC 3.2, SPEC 9.1).

MODULE STYLE & HOUSE RULES:
- Comments va docstrings dung tieng Viet khong dau (ASCII-folded).
- Chuoi thong bao nguoi dung (reason, error) giu day du dau tieng Viet.
- Khong bao gio doan gia tri: the khong doc duoc tra ve api_names rong kem reason ro rang.
- Dataclass bat bien (frozen=True), ngoai le cuc bo AugmentReadError(RuntimeError).

SPEC TENSION & INVARIANT:
`src/decision/llm_reasoner.py` quy dinh LLM khong bao gio nam tren duong quyet dinh
co han gio. Quy tac do chi phoi tang SUY LUAN (reasoning). SPEC 9.3 neu ro bo nhan dang
chi tra ve `apiName` + do tin cay va KHONG BAO GIO cham diem - nho do xep hang van
hoan toan xac dinh, closed-form va khong dung LLM. Nhan dang tat yeu phai dien ra truoc
khi cham diem; co che timeout cung, cache aHash va con duong tu choi (refuse, khong doan)
la nhung thu giu cho ranh gioi do duoc trung thuc va an toan.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass
import json
import os
from pathlib import Path
import time
from typing import Any, Callable, Sequence

import numpy as np

from ..capture.regions import RegionError, ScreenRegions
from ..decision.augment_advisor import AugmentChoice
from ..knowledge.name_index import NameIndex
from ..utils.env import load_env

DEFAULT_REGIONS = "config/screen_regions.yaml"
DEFAULT_NAME_INDEX = "data/name_index.json"
DEFAULT_MODEL = "gemini-3.5-flash-lite"
# Do duoc 3 lan tren may ranh: 3,10 / 3,14 / 3,16 s. 12,0 = ~4x p50, con
# chua ~18 s trong dong ho ~30 s cua man chon augment. Nguong 6,0 cu da
# timeout that o che do --from-video. CHUA do khi game dang chay (SPEC 12.1).
DEFAULT_TIMEOUT_S = 12.0
DEFAULT_HASH_SIZE = 8

PROMPT = """Bạn là bộ trích xuất văn bản từ hình ảnh giao diện Đấu Trường Chân Lý (Teamfight Tactics) tiếng Việt.
Hình ảnh đính kèm gồm 3 thẻ Nâng Cấp (Augment) ở các ô slot 0, 1, 2 và bảng Tộc/Hệ (Traits).
Hãy trích xuất tiêu đề (title), mô tả (body) của từng thẻ, và danh sách các tộc/hệ (name) cùng số mốc kích hoạt (count).

Trả về DUY NHẤT một đối tượng JSON phẳng theo cấu trúc sau (không kèm giải thích, không dùng markdown block):
{
  "cards": [
    {"slot": 0, "title": "...", "body": "..."},
    {"slot": 1, "title": "...", "body": "..."},
    {"slot": 2, "title": "...", "body": "..."}
  ],
  "traits": [
    {"name": "...", "count": 2}
  ]
}
"""


class AugmentReadError(RuntimeError):
    """Loi cau truc hoac yeu cau du lieu khong hop le tu ket qua doc augment."""


@dataclass(frozen=True)
class CardRead:
    """Ket qua doc mot the augment duy nhat."""

    slot: int
    title: str
    body: str
    api_names: tuple[str, ...]
    confidence: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot": self.slot,
            "title": self.title,
            "body": self.body,
            "api_names": list(self.api_names),
            "confidence": round(self.confidence, 4),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class AugmentReading:
    """Ket qua doc toan bo man chon augment (3 the + toc/he)."""

    cards: tuple[CardRead, ...]
    traits: dict[str, int]
    source: str
    latency_ms: float

    def resolved(self) -> bool:
        """True neu moi the deu da duoc xac dinh it nhat mot apiName."""
        return bool(self.cards) and all(len(c.api_names) > 0 for c in self.cards)

    def to_choices(self) -> list[AugmentChoice]:
        """Chuyen ket qua thanh danh sach AugmentChoice cho Advisor."""
        if not self.cards:
            raise AugmentReadError("Không có thẻ augment nào trong kết quả đọc")
        unresolved = [c for c in self.cards if not c.api_names]
        if unresolved:
            reasons = "; ".join(f"ô {c.slot + 1}: {c.reason}" for c in unresolved)
            raise AugmentReadError(f"Không thể tạo AugmentChoice vì có thẻ chưa xác định: {reasons}")
        return [
            AugmentChoice(
                api_names=list(c.api_names),
                confidence=c.confidence,
                display_name=c.title,
            )
            for c in self.cards
        ]

    def api_names_flat(self) -> list[str]:
        """Tra ve danh sach 1 apiName moi the. Nem loi neu the bi map mo hoac chua xac dinh."""
        if not self.cards:
            raise AugmentReadError("Không có thẻ augment nào trong kết quả đọc")
        flat: list[str] = []
        for c in self.cards:
            if not c.api_names:
                raise AugmentReadError(
                    f"Thẻ ở ô {c.slot + 1} chưa xác định được apiName ({c.reason})"
                )
            if len(c.api_names) > 1:
                raise AugmentReadError(
                    f"Thẻ ở ô {c.slot + 1} bị mập mờ ({', '.join(c.api_names)}), "
                    "không thể làm phẳng thành list[str] vì sẽ làm mất ứng viên"
                )
            flat.append(c.api_names[0])
        return flat

    def to_dict(self) -> dict[str, Any]:
        return {
            "cards": [c.to_dict() for c in self.cards],
            "traits": dict(self.traits),
            "source": self.source,
            "latency_ms": round(self.latency_ms, 2),
            "resolved": self.resolved(),
        }


def compute_ahash(image: np.ndarray, hash_size: int = DEFAULT_HASH_SIZE) -> int:
    """Tinh Average Hash (aHash) 64-bit tren anh BGR hoac xam."""
    import cv2  # noqa: PLC0415

    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    resized = cv2.resize(gray, (hash_size, hash_size), interpolation=cv2.INTER_AREA)
    mean_val = float(resized.mean())
    val = 0
    for pixel in resized.flat:
        val = (val << 1) | (1 if pixel >= mean_val else 0)
    return val


def build_composite(
    card_crops: Sequence[np.ndarray],
    traits_crop: np.ndarray,
) -> np.ndarray:
    """Gop 3 vung the bai va bang toc/he thanh 1 anh duy nhat kem nhan."""
    import cv2  # noqa: PLC0415

    banner_h = 24
    labeled_cards: list[np.ndarray] = []
    for idx, crop_img in enumerate(card_crops):
        if crop_img.ndim == 2:
            crop_img = cv2.cvtColor(crop_img, cv2.COLOR_GRAY2BGR)
        cw = crop_img.shape[1]
        banner = np.full((banner_h, cw, 3), 30, dtype=np.uint8)
        cv2.putText(
            banner,
            f"CARD {idx}",
            (10, banner_h - 7),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
        labeled = np.vstack([banner, crop_img])
        labeled_cards.append(labeled)

    max_card_h = max(c.shape[0] for c in labeled_cards)
    padded_cards: list[np.ndarray] = []
    for c in labeled_cards:
        if c.shape[0] < max_card_h:
            pad = np.zeros((max_card_h - c.shape[0], c.shape[1], 3), dtype=np.uint8)
            padded_cards.append(np.vstack([c, pad]))
        else:
            padded_cards.append(c)
    cards_strip = np.hstack(padded_cards)

    if traits_crop.ndim == 2:
        traits_crop = cv2.cvtColor(traits_crop, cv2.COLOR_GRAY2BGR)
    tw = traits_crop.shape[1]
    traits_banner = np.full((banner_h, tw, 3), 30, dtype=np.uint8)
    cv2.putText(
        traits_banner,
        "TRAITS",
        (10, banner_h - 7),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )
    labeled_traits = np.vstack([traits_banner, traits_crop])

    total_h = max(labeled_traits.shape[0], cards_strip.shape[0])
    total_w = labeled_traits.shape[1] + cards_strip.shape[1] + 10
    canvas = np.zeros((total_h, total_w, 3), dtype=np.uint8)
    canvas[: labeled_traits.shape[0], : labeled_traits.shape[1]] = labeled_traits
    x_offset = labeled_traits.shape[1] + 10
    canvas[: cards_strip.shape[0], x_offset : x_offset + cards_strip.shape[1]] = cards_strip
    return canvas


class AugmentReader:
    """Bo nhan dang the augment va toc/he su dung Gemini Vision kem bo dem aHash."""

    def __init__(
        self,
        regions: ScreenRegions | str | Path | None = None,
        names: NameIndex | str | Path | None = None,
        *,
        model: str = DEFAULT_MODEL,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        enable_gemini_vision: bool = True,
        call: Callable[[bytes], str] | None = None,
        hash_size: int = DEFAULT_HASH_SIZE,
        max_hash_diff: int = 0,
    ) -> None:
        if regions is None:
            self.regions = ScreenRegions.load(DEFAULT_REGIONS)
        elif isinstance(regions, ScreenRegions):
            self.regions = regions
        else:
            self.regions = ScreenRegions.load(regions)

        if names is None:
            self.names = NameIndex.load(DEFAULT_NAME_INDEX)
        elif isinstance(names, NameIndex):
            self.names = names
        else:
            self.names = NameIndex.load(names)

        self.model = model
        self.timeout_s = timeout_s
        self.enable_gemini_vision = enable_gemini_vision
        self.call = call
        self.hash_size = hash_size
        self.max_hash_diff = max_hash_diff

        self._last_hash: int | None = None
        self._last_reading: AugmentReading | None = None

        # Kiem tra cac vung bat buoc ngay luc khoi tao
        try:
            for slot in range(3):
                self.regions.region("augment_select", f"card_text_{slot}")
            self.regions.region("hud", "traits")
        except RegionError as exc:
            raise AugmentReadError(f"Thiếu ROI cho AugmentReader: {exc}") from exc

    @classmethod
    def load(
        cls,
        regions: ScreenRegions | str | Path = DEFAULT_REGIONS,
        names: NameIndex | str | Path = DEFAULT_NAME_INDEX,
        *,
        model: str = DEFAULT_MODEL,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        enable_gemini_vision: bool = True,
        call: Callable[[bytes], str] | None = None,
        hash_size: int = DEFAULT_HASH_SIZE,
        max_hash_diff: int = 0,
    ) -> "AugmentReader":
        """Nap bo doc augment tu file cau hinh ROI va index ten."""
        return cls(
            regions=regions,
            names=names,
            model=model,
            timeout_s=timeout_s,
            enable_gemini_vision=enable_gemini_vision,
            call=call,
            hash_size=hash_size,
            max_hash_diff=max_hash_diff,
        )

    def _default_call(self, image_png: bytes) -> str:
        """Goi truc tiep SDK Gemini Vision."""
        load_env()
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise AugmentReadError("Thiếu GEMINI_API_KEY hoặc GOOGLE_API_KEY")
        from google import genai  # noqa: PLC0415
        from google.genai import types  # noqa: PLC0415

        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(
            model=self.model,
            contents=[
                PROMPT,
                types.Part.from_bytes(data=image_png, mime_type="image/png"),
            ],
            config={"response_mime_type": "application/json"},
        )
        return getattr(resp, "text", "") or ""

    @staticmethod
    def _parse(raw: str) -> dict[str, Any] | None:
        """Trang bi brace scan va json.loads giong llm_reasoner._parse."""
        start, end = raw.find("{"), raw.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            parsed = json.loads(raw[start : end + 1])
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None

    def _resolve_card(self, slot: int, card_data: dict[str, Any]) -> CardRead:
        title = str(card_data.get("title", "")).strip()
        body = str(card_data.get("body", "")).strip()

        if not title:
            return CardRead(
                slot=slot,
                title="",
                body=body,
                api_names=(),
                confidence=0.0,
                reason="Không có tiêu đề thẻ từ Gemini",
            )

        # 1. Resolve truc tiep qua NameIndex
        hits = self.names.resolve(title, namespace="augments", lang="vi")
        if len(hits) == 1:
            return CardRead(
                slot=slot,
                title=title,
                body=body,
                api_names=tuple(hits),
                confidence=1.0,
                reason="Khớp duy nhất",
            )
        if len(hits) > 1:
            return CardRead(
                slot=slot,
                title=title,
                body=body,
                api_names=tuple(hits),
                confidence=1.0,
                reason=f"Cặp augment mập mờ ({len(hits)} ứng viên)",
            )

        # 2. Thu resolve_stem neu bo sot hau to tier (I, II, III, +, ++)
        stem_hits = self.names.resolve_stem(title, namespace="augments", lang="vi")
        if stem_hits:
            return CardRead(
                slot=slot,
                title=title,
                body=body,
                api_names=tuple(stem_hits),
                confidence=0.7,
                reason="Khớp theo gốc (resolve_stem), thiếu hậu tố tier",
            )

        # 3. Khong tim thay - KHONG fuzzy match
        return CardRead(
            slot=slot,
            title=title,
            body=body,
            api_names=(),
            confidence=0.0,
            reason=f"Không tìm thấy tên '{title}' trong NameIndex",
        )

    def _resolve_traits(self, traits_data: list[Any]) -> dict[str, int]:
        result: dict[str, int] = {}
        for item in traits_data:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            count = item.get("count", 0)
            if not name:
                continue
            try:
                cnt = int(count)
            except (ValueError, TypeError):
                continue
            hits = self.names.resolve(name, namespace="traits", lang="vi")
            if len(hits) == 1:
                result[hits[0]] = cnt
            elif not hits:
                stem_hits = self.names.resolve_stem(name, namespace="traits", lang="vi")
                if len(stem_hits) == 1:
                    result[stem_hits[0]] = cnt
        return result

    def _crop_cards(self, frame: np.ndarray) -> np.ndarray:
        """Cat vung bao the bai de tinh aHash caching."""
        if "cards" in self.regions.screens.get("augment_select", {}):
            return self.regions.crop(frame, "augment_select", "cards")
        c0 = self.regions.crop(frame, "augment_select", "card_text_0")
        c1 = self.regions.crop(frame, "augment_select", "card_text_1")
        c2 = self.regions.crop(frame, "augment_select", "card_text_2")
        return np.hstack([c0, c1, c2])

    def _unresolved_reading(self, reason: str, latency_ms: float) -> AugmentReading:
        cards = tuple(
            CardRead(
                slot=slot,
                title="",
                body="",
                api_names=(),
                confidence=0.0,
                reason=reason,
            )
            for slot in range(3)
        )
        return AugmentReading(
            cards=cards,
            traits={},
            source=f"gemini:{self.model}",
            latency_ms=round(latency_ms, 2),
        )

    def read(self, frame: np.ndarray) -> AugmentReading:
        """Doc the augment va toc/he tu mot khung hinh BGR."""
        if frame is None or frame.size == 0:
            raise AugmentReadError("Khung hình rỗng, không thể đọc augment")

        if not self.enable_gemini_vision:
            return self._unresolved_reading("Gemini Vision đã tắt trong cấu hình", 0.0)

        t0 = time.perf_counter()

        # 1. Kiem tra aHash caching
        cards_crop = self._crop_cards(frame)
        current_hash = compute_ahash(cards_crop, hash_size=self.hash_size)

        if self._last_reading is not None and self._last_hash is not None:
            diff = (current_hash ^ self._last_hash).bit_count()
            if diff <= self.max_hash_diff:
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                return AugmentReading(
                    cards=self._last_reading.cards,
                    traits=self._last_reading.traits,
                    source="cache",
                    latency_ms=round(elapsed_ms, 2),
                )

        # 2. Cat cac vung va tao composite image
        import cv2  # noqa: PLC0415

        c0 = self.regions.crop(frame, "augment_select", "card_text_0")
        c1 = self.regions.crop(frame, "augment_select", "card_text_1")
        c2 = self.regions.crop(frame, "augment_select", "card_text_2")
        traits_crop = self.regions.crop(frame, "hud", "traits")

        composite = build_composite([c0, c1, c2], traits_crop)
        success, buf = cv2.imencode(".png", composite)
        if not success:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return self._unresolved_reading(
                reason="Không thể mã hóa ảnh PNG composite",
                latency_ms=elapsed_ms,
            )
        image_png = buf.tobytes()

        # 3. Goi Gemini hoac plain callable tiem vao
        caller = self.call or self._default_call
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                raw = pool.submit(caller, image_png).result(timeout=self.timeout_s)
        except FutureTimeout:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return self._unresolved_reading(
                reason=f"Gemini timeout sau {self.timeout_s:.1f}s",
                latency_ms=elapsed_ms,
            )
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return self._unresolved_reading(
                reason=f"Lỗi gọi Gemini: {exc}",
                latency_ms=elapsed_ms,
            )

        # 4. Parse JSON
        parsed = self._parse(raw)
        if parsed is None or not isinstance(parsed, dict):
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return self._unresolved_reading(
                reason="JSON trả về từ Gemini bị hỏng hoặc sai định dạng",
                latency_ms=elapsed_ms,
            )

        # 5. Giai ma the
        cards_list = parsed.get("cards", [])
        if not isinstance(cards_list, list):
            cards_list = []

        cards_by_slot: dict[int, dict[str, Any]] = {}
        for item in cards_list:
            if isinstance(item, dict) and "slot" in item:
                try:
                    s = int(item["slot"])
                    cards_by_slot[s] = item
                except (ValueError, TypeError):
                    pass

        card_reads: list[CardRead] = []
        for slot in range(3):
            c_data = cards_by_slot.get(slot)
            if (
                c_data is None
                and slot < len(cards_list)
                and isinstance(cards_list[slot], dict)
                and "slot" not in cards_list[slot]
            ):
                c_data = cards_list[slot]
            if c_data is not None:
                card_reads.append(self._resolve_card(slot, c_data))
            else:
                card_reads.append(
                    CardRead(
                        slot=slot,
                        title="",
                        body="",
                        api_names=(),
                        confidence=0.0,
                        reason=f"Thiếu dữ liệu ô {slot} trong phản hồi của Gemini",
                    )
                )

        # 6. Giai ma toc/he
        traits_list = parsed.get("traits", [])
        if not isinstance(traits_list, list):
            traits_list = []
        resolved_traits = self._resolve_traits(traits_list)

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        reading = AugmentReading(
            cards=tuple(card_reads),
            traits=resolved_traits,
            source=f"gemini:{self.model}",
            latency_ms=round(elapsed_ms, 2),
        )

        # Luu cache cho lan goi ke tiep
        self._last_hash = current_hash
        self._last_reading = reading
        return reading
