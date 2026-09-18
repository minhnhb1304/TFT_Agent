"""Tim DONG CUA NGUOI CHOI trong bang 8 nguoi ben phai man hinh (moc M2).

Vi sao can: bang 8 nguoi SAP XEP LAI THEO MAU sau moi vong. Mot ROI co dinh
doc trung dong nao do tuy luc - do dung la loi da do duoc tren ban record
2026-09-16: `hud_acc[hp]` chi 0,27-0,36, va hai lan doc ra mau cua nguoi khac
(88 thay vi 78; 93 thay vi 73).

Dau hieu nhan dien, do nguoi choi chi ra va da kiem tren khung that:
avatar cua nguoi choi co VONG TRON VANG, bay nguoi con lai vong do.
Vong vang la vung mau vang lien thong LON NHAT trong cot avatar.

Khong thay vong vang (bang bi panel khac che, dang chuyen canh) thi tra None -
goi ben se lui ve ROI tinh va ghi ro la da lui, chu khong doan bua.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..capture.regions import ScreenRegions

# Ty le do tren khung 1920x1080 cua ban record. Cot avatar nam sat mep phai.
AVATAR_COLUMN = (0.920, 1.000)      # x tu - den
PANEL_ROWS = (0.10, 0.92)           # y tu - den, bo ra ngoai vung chu chay chu
HP_BOX = (0.906, 0.945)             # x cua o so mau, nam ben trai avatar
HP_BOX_HEIGHT = 36                  # px quanh tam vong vang

# Vong vang: HSV. Nguong nay tach duoc vong vang khoi bay vong do va khoi nen.
GOLD_HSV_LOW = (18, 140, 150)
GOLD_HSV_HIGH = (38, 255, 255)
MIN_RING_AREA = 300                 # px - nho hon la mot vet vang lat vat, khong phai vong
# Vong avatar o 1920x1080 rong khoang 40-56 px va gan tron. Kiem hinh dang de
# khong bat nham mot vet vang khac trong panel (do thay tren khung chuyen canh).
RING_WIDTH_PX = (26, 96)            # do tren khung that: 40-56 px binh thuong, toi 82 px o dau van
RING_ASPECT = (0.65, 1.55)


@dataclass(frozen=True)
class PlayerRow:
    """Dong cua nguoi choi trong bang ben phai."""

    center_y: int
    area: int

    @property
    def confident(self) -> bool:
        return self.area >= MIN_RING_AREA


def find_player_row(image: np.ndarray, regions: ScreenRegions | None = None) -> PlayerRow | None:
    """Tra ve dong co vong vang, hoac None neu khong thay."""
    import cv2  # noqa: PLC0415

    if image is None or image.size == 0 or image.ndim != 3:
        return None
    h, w = image.shape[:2]
    y0, y1 = int(PANEL_ROWS[0] * h), int(PANEL_ROWS[1] * h)
    x0, x1 = int(AVATAR_COLUMN[0] * w), int(AVATAR_COLUMN[1] * w)
    strip = image[y0:y1, x0:x1]
    if strip.size == 0:
        return None

    mask = cv2.inRange(cv2.cvtColor(strip, cv2.COLOR_BGR2HSV), GOLD_HSV_LOW, GOLD_HSV_HIGH)
    count, _labels, stats, centroids = cv2.connectedComponentsWithStats(mask, 8)
    if count < 2:
        return None

    scale = w / 1920.0
    best: PlayerRow | None = None
    for index in range(1, count):
        area = int(stats[index, cv2.CC_STAT_AREA])
        width = int(stats[index, cv2.CC_STAT_WIDTH])
        height = int(stats[index, cv2.CC_STAT_HEIGHT])
        if area < MIN_RING_AREA or height <= 0:
            continue
        if not RING_WIDTH_PX[0] * scale <= width <= RING_WIDTH_PX[1] * scale:
            continue
        if not RING_ASPECT[0] <= width / height <= RING_ASPECT[1]:
            continue
        if best is None or area > best.area:
            best = PlayerRow(center_y=int(centroids[index][1]) + y0, area=area)
    return best


def hp_box(image: np.ndarray, row: PlayerRow) -> np.ndarray:
    """Cat o so mau cua dong do."""
    h, w = image.shape[:2]
    half = HP_BOX_HEIGHT // 2
    top = max(0, row.center_y - half)
    bottom = min(h, row.center_y + half)
    return image[top:bottom, int(HP_BOX[0] * w):int(HP_BOX[1] * w)]
