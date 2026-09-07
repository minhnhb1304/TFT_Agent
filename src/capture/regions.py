"""Vung quan tam (ROI) - doc tu `config/screen_regions.yaml` (SPEC 3.1, 5).

TOA DO LUU DANG TI LE, KHONG PHAI PIXEL

SPEC 3.2 doi doc lap do phan giai. Luu 0..1 thay vi pixel co ba cai loi:
    - Cung mot file chay duoc tren 1920x1080 lan 2560x1440.
    - Frame tu VOD va frame tu capture song dung chung mot bo so.
    - Doc len la thay ngay ti le bo cuc, khong phai nham xem 882 la gan day
      man hinh hay giua man hinh.

BANG TOA DO TRONG SPEC 3.1 DA CHET

Bang do thuoc Set 17 (engine Hextech) va SPEC danh dau ro la khong song sot
qua 2026-08-26 khi Set 18 chuyen sang Unreal. Do lai tren frame Set 18 that
(2026-09-06) cho thay bang panel toc thuc su nam o y 260..790 chu khong phai
200..700 - tuc la neu dung so cu thi ROI se an vao overlay chat cua stream o
y 200..215 va doc phai chu cua nguoi xem.

ROI KHONG DUOC GIAO VOI VUNG BI CHE

`config/settings.yaml` co `capture.assert_roi_disjoint_from_overlay: true`.
`blockers` o day la hien thuc cua loi hua do: vung overlay cua chinh ta khi
chay song, va khung chat/QR cua streamer khi doc VOD. `check_blockers()` bien
mot quy uoc bo tri thanh mot bat bien kiem chung duoc.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import yaml


class RegionError(ValueError):
    """File ROI thieu, sai dinh dang, hoac ROI nam ngoai khung hinh."""


@dataclass(frozen=True)
class Region:
    """Mot hinh chu nhat theo ti le khung hinh (0..1)."""

    x: float
    y: float
    w: float
    h: float

    def __post_init__(self) -> None:
        for name, v in (("x", self.x), ("y", self.y), ("w", self.w), ("h", self.h)):
            if not 0.0 <= v <= 1.0:
                raise RegionError(f"{name}={v} nam ngoai 0..1")
        if self.w <= 0 or self.h <= 0:
            raise RegionError("chieu rong/cao phai duong")
        if self.x + self.w > 1.0001 or self.y + self.h > 1.0001:
            raise RegionError("vung tran ra ngoai khung hinh")

    @classmethod
    def from_pixels(
        cls, left: int, top: int, right: int, bottom: int, width: int, height: int
    ) -> "Region":
        """Dung tu toa do pixel do tay tren mot frame co kich thuoc biet truoc."""
        return cls(
            x=left / width, y=top / height,
            w=(right - left) / width, h=(bottom - top) / height,
        )

    def to_pixels(self, width: int, height: int) -> tuple[int, int, int, int]:
        """(left, top, right, bottom) tren khung hinh kich thuoc da cho.

        Luon rong/cao it nhat 1 pixel va luon nam trong khung. Vung ti le rat
        nho o do phan giai thap se lam tron ve 0 pixel; khi do `crop()` tra ve
        mang RONG va cv2 nem mot loi kho hieu o tan sau. Kep o day de loi (neu
        co) hien ra dung cho no sinh ra.
        """
        left = max(0, min(int(round(self.x * width)), max(0, width - 1)))
        top = max(0, min(int(round(self.y * height)), max(0, height - 1)))
        right = min(width, max(left + 1, left + int(round(self.w * width))))
        bottom = min(height, max(top + 1, top + int(round(self.h * height))))
        return left, top, right, bottom

    def to_dict(self) -> dict[str, float]:
        return {"x": round(self.x, 6), "y": round(self.y, 6),
                "w": round(self.w, 6), "h": round(self.h, 6)}

    def intersects(self, other: "Region") -> bool:
        return not (
            self.x + self.w <= other.x or other.x + other.w <= self.x
            or self.y + self.h <= other.y or other.y + other.h <= self.y
        )


def crop(image: np.ndarray, region: Region) -> np.ndarray:
    """Cat mot vung ra khoi anh BGR. Tra ve VIEW, khong sao chep."""
    if image is None or image.size == 0:
        raise RegionError("anh rong - khong cat duoc")
    h, w = image.shape[:2]
    left, top, right, bottom = region.to_pixels(w, h)
    return image[top:bottom, left:right]


@dataclass
class ScreenRegions:
    """Toan bo ROI da hieu chuan, kem xuat xu."""

    screens: dict[str, dict[str, Region]]
    blockers: dict[str, Region]
    meta: dict[str, Any]

    @classmethod
    def load(cls, path: str | Path) -> "ScreenRegions":
        p = Path(path)
        if not p.is_file():
            raise RegionError(
                f"chua co {p}. Chay `python tools/calibrate.py` de sinh ra - "
                "bang toa do trong SPEC 3.1 la cua Set 17 va KHONG dung nua."
            )
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            raise RegionError(f"{p} khong phai YAML hop le: {exc}") from exc
        if not isinstance(data, dict):
            raise RegionError(f"{p} phai la mot anh xa, khong phai {type(data).__name__}")

        def build(where: str, name: str, box: object) -> Region:
            if not isinstance(box, dict):
                raise RegionError(f"{where}.{name} phai co x/y/w/h, nhan {box!r}")
            missing = {"x", "y", "w", "h"} - set(box)
            if missing:
                raise RegionError(f"{where}.{name} thieu khoa: {sorted(missing)}")
            try:
                return Region(x=float(box["x"]), y=float(box["y"]),
                              w=float(box["w"]), h=float(box["h"]))
            except (TypeError, ValueError) as exc:
                raise RegionError(f"{where}.{name} co gia tri khong phai so: {exc}") from exc

        return cls(
            screens={
                screen: {name: build(screen, name, box) for name, box in (boxes or {}).items()}
                for screen, boxes in (data.get("screens") or {}).items()
            },
            blockers={
                name: build("blockers", name, box)
                for name, box in (data.get("blockers") or {}).items()
            },
            meta=data.get("meta") or {},
        )

    def to_yaml(self) -> str:
        payload = {
            "meta": self.meta,
            "screens": {
                screen: {name: box.to_dict() for name, box in boxes.items()}
                for screen, boxes in self.screens.items()
            },
            "blockers": {name: box.to_dict() for name, box in self.blockers.items()},
        }
        return yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)

    def region(self, screen: str, name: str) -> Region:
        try:
            return self.screens[screen][name]
        except KeyError as exc:
            raise RegionError(f"khong co vung '{screen}.{name}'") from exc

    def crop(self, image: np.ndarray, screen: str, name: str) -> np.ndarray:
        return crop(image, self.region(screen, name))

    def check_blockers(self, screen: str, ignore: Iterable[str] = ()) -> dict[str, list[str]]:
        """Vung nao cua `screen` bi khung che dam vao.

        Tra ve {ten_vung: [ten_blocker, ...]}. RONG la dieu ta muon; khong rong
        thi phai xu ly ro rang chu khong duoc doc xuyen qua chu cua nguoi khac.
        """
        skip = set(ignore)
        hits: dict[str, list[str]] = {}
        for name, box in self.screens.get(screen, {}).items():
            if name in skip:
                continue
            clashes = [b for b, blocker in self.blockers.items() if box.intersects(blocker)]
            if clashes:
                hits[name] = clashes
        return hits
