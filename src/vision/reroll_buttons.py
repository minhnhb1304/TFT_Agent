"""Doc trang thai ba nut doi the tren man chon augment (SPEC 3.1, Nhiem vu 3).

    reader = RerollButtonReader.load()
    reading = reader.read(frame)                 # frame BGR 1920x1080
    rerolls = reading.to_reroll_state(fallback=last_known)
    bundle  = advisor.advise(state, choices, rerolls=rerolls)

MAN HINH KHONG CO BO DEM SO - CHI CO BA CAI NUT

`RerollState` doi mot vector `(r0, r1, r2)`. Khong o dau tren man hinh hien
"con 2 luot"; thu duy nhat doc duoc la BA cai nut o duoi ba the bai, moi cai
mang trang thai rieng. Module nay la duong DUY NHAT bien pixel thanh vector
do. Truoc no, `Advisor.advise(rerolls=...)` chi nhan duoc so do NGUOI go vao.

BA TRANG THAI, KHONG PHAI HAI (do tren 765 mau, 3 VOD)
------------------------------------------------------

| trang thai | nen nut      | vien   | `warm`       | `fill_value` | n   |
|------------|--------------|--------|--------------|--------------|-----|
| SANG       | nau vang     | vang   | +24,3..+49,6 | 39,5..45,8   | 350 |
| VUA BAM    | gan den      | vang   |  -6,3..-2,6  |  7,6..8,2    |  11 |
| DA DUNG    | xanh than    | xam    |  -8,4..-2,1  | 29,8..37,9   | 148 |

`warm = mean(R) - mean(B)` tren long nut; `fill_value` la do sang trung binh
cua 40% diem TOI NHAT trong long nut (bo net glyph va con tro chuot ra).

Trang thai giua bang la mot cai bay. Nen no gan den nen `warm` am - doc bang
mau khong thoi se goi no la DA DUNG. Do lai chuoi thoi gian tren ba VOD cho
thay KHONG PHAI: khung ke tiep no la mot nut SANG binh thuong tro lai (VOD
s7h @ 066-070 o 2, @ 081-085 o 0). Day la khung nhay khi chuot dang bam,
khong phai trang thai on dinh. Goi no la DA DUNG thi ta tu tay xoa mot luot
roll ma nguoi choi van con - va chinh sach tuan tu se dung som mot cach vo co.
Vi the no co ten rieng va KHONG di vao vector bool.

NHAN BIET "CO NUT O DAY" PHAI DUNG HINH DANG, KHONG DUNG MAU
------------------------------------------------------------

Khung trich ra quanh moc su kien co ca khung KHONG phai man chon augment (co
xanh, tuong da, lua trai). `warm` cua dia hinh chay khap khoang - do duoc mot
mang co +54, cao hon ca nut sang. Chi hinh mui ten vong tron la khong lap lai.

Do khop lay `max` tren BON nua cua mau (trai/phai/tren/duoi) chu khong tren
ca mau: con tro chuot nam de len glyph o mot so khung, va che mot nua thi nua
kia van khop. Do tren 765 mau: nut that thap nhat 0,723 (mot nut bi con tro
che gan het), dia hinh cao nhat 0,636 - nguong 0,68 nam giua khe do.

CAI KHONG TUYEN BO DUOC

Cac nguong duoi day do tren 3 VOD Set 18 o 1920x1080, giao dien tieng Viet.
Doi do phan giai thi ROI van dung (toa do luu dang ti le) nhung nguong khop
mau CHUA duoc do lai. Doi Set / doi giao dien thi phai chay lai
`scripts/build_reroll_template.py` va do lai `docs/vision/reroll-buttons.md`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol, Sequence

import numpy as np

from ..capture.regions import Region, ScreenRegions, crop

ButtonState = Literal["active", "disabled", "pressed", "unknown"]

SCREEN = "augment_select"
SLOT_NAMES = ("reroll_0", "reroll_1", "reroll_2")

DEFAULT_TEMPLATE = "data/templates/reroll_glyph.png"
DEFAULT_REGIONS = "config/screen_regions.yaml"

# Kich thuoc chuan cua mot o nut sau khi resize: (rong, cao). Moi phep do o
# duoi deu thuc hien o kich thuoc nay nen chung khong doi theo do phan giai.
BUTTON_SIZE = (100, 52)

# Vung glyph trong long nut o kich thuoc chuan: (top, left, height, width).
# Bo 10px tren/duoi va 16px hai ben de khong an vao vien - vien la thu DOI
# MAU giua hai trang thai, glyph thi khong.
GLYPH_BOX = (10, 16, 32, 68)

# Vien nut day khoang 3px o kich thuoc chuan; cat 6px cho chac.
_BORDER = 6
# Phan tram diem toi nhat dung de uoc luong mau NEN (khong lay net glyph).
_FILL_PERCENTILE = 40


class ButtonReadError(RuntimeError):
    """Khong doc duoc trang thai nut, va khong co gia tri du phong de lui ve."""


class RerollStateLike(Protocol):
    """Chi de chu thich kieu - `RerollState` that nam o tang quyet dinh."""

    available: Sequence[bool]
    burned: Sequence[str]


@dataclass(frozen=True)
class ButtonThresholds:
    """Nguong phan loai. Moi so keo theo mot khe da do - xem docstring module."""

    # Khe do duoc: nut that thap nhat 0,723 / dia hinh cao nhat 0,636.
    min_glyph_match: float = 0.68
    # Khe do duoc: DA DUNG cao nhat -2,1 / SANG thap nhat +24,3.
    active_warm: float = 12.0
    # Khe do duoc: VUA BAM cao nhat 8,2 / DA DUNG thap nhat 29,8.
    pressed_fill_value: float = 20.0


@dataclass(frozen=True)
class ButtonRead:
    """Mot o, kem MOI so da dung de ket luan - de con truy nguoc khi doc sai."""

    slot: int
    state: ButtonState
    glyph_match: float
    warm: float
    fill_value: float
    reason: str

    @property
    def settled(self) -> bool:
        """Trang thai on dinh, quy duoc ve mot bit trong `RerollState`."""
        return self.state in ("active", "disabled")

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot": self.slot,
            "state": self.state,
            "glyph_match": round(self.glyph_match, 4),
            "warm": round(self.warm, 2),
            "fill_value": round(self.fill_value, 2),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class RerollButtonReading:
    """Ket qua doc ca ba o cua MOT khung hinh."""

    reads: tuple[ButtonRead, ...]

    @property
    def screen_present(self) -> bool:
        """Khung nay co dang o man chon augment khong.

        Doi CA BA o cung thay glyph. Man chon augment luon hien du ba nut;
        thay mot hai cai thi nhieu kha nang la trung hop dia hinh chu khong
        phai man chon bi cat mat mot goc.
        """
        return bool(self.reads) and all(r.state != "unknown" for r in self.reads)

    @property
    def settled(self) -> bool:
        """Ca ba o deu nga ngu - quy thang duoc ve `RerollState`."""
        return bool(self.reads) and all(r.settled for r in self.reads)

    @property
    def available(self) -> tuple[bool | None, ...]:
        """`True`/`False` cho o da chac, `None` cho o chua chac."""
        return tuple(
            True if r.state == "active" else False if r.state == "disabled" else None
            for r in self.reads
        )

    def to_reroll_state(self, fallback: RerollStateLike | None = None) -> Any:
        """Quy ve `RerollState` cho `Advisor.advise(rerolls=...)`.

        O chua chac (`unknown` / `pressed`) lay gia tri tu `fallback` - tuc la
        lan doc ON DINH gan nhat. Khong co `fallback` thi NEM: doan bua mot
        bit o day se lam chinh sach tuan tu dung som hoac roll qua luot, va
        loi do khong tu bao la loi o bat ky cho nao ve sau.
        """
        from ..decision.reroll_policy import RerollState

        prev = tuple(fallback.available) if fallback is not None else ()
        out: list[bool] = []
        for r in self.reads:
            if r.state == "active":
                out.append(True)
            elif r.state == "disabled":
                out.append(False)
            elif r.slot < len(prev):
                out.append(bool(prev[r.slot]))
            else:
                raise ButtonReadError(
                    f"o {r.slot + 1} doc ra '{r.state}' ({r.reason}) va khong co "
                    "gia tri du phong - truyen fallback=<lan doc on dinh gan nhat>"
                )
        burned = tuple(fallback.burned) if fallback is not None else ()
        return RerollState(tuple(out), burned)

    def to_dict(self) -> dict[str, Any]:
        return {
            "screen_present": self.screen_present,
            "settled": self.settled,
            "available": list(self.available),
            "slots": [r.to_dict() for r in self.reads],
        }


def normalize_gray(gray: np.ndarray) -> np.ndarray:
    """Keo tuong phan ve 0..255.

    Nut SANG va nut DA DUNG khac nhau ca do sang lan do bao hoa, nhung glyph
    o giua thi cung mot hinh. Chuan hoa truoc khi khop lam phep do chi con
    phu thuoc HINH DANG - nho the MOT mau dung duoc cho ca hai trang thai.
    """
    import cv2

    return cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)


class RerollButtonReader:
    """Bien mot khung hinh thanh trang thai ba nut doi the."""

    def __init__(
        self,
        regions: ScreenRegions,
        template: np.ndarray,
        thresholds: ButtonThresholds | None = None,
    ) -> None:
        if template is None or template.size == 0:
            raise ButtonReadError("mau glyph rong")
        if template.ndim != 2:
            raise ButtonReadError(
                f"mau glyph phai la anh xam 2 chieu, nhan {template.ndim} chieu"
            )
        for slot in range(len(SLOT_NAMES)):
            regions.region(SCREEN, SLOT_NAMES[slot])  # no ngay neu thieu ROI
        self.regions = regions
        self.thresholds = thresholds or ButtonThresholds()
        self.template = template
        h, w = template.shape
        # Bon nua: trai / phai / tren / duoi. Con tro chuot che mot phan glyph
        # o mot so khung; khop tren ca mau thi tut ve 0,37, con khop tren nua
        # khong bi che thi van 0,72.
        self._halves = tuple(
            np.ascontiguousarray(part)
            for part in (
                template[:, : w // 2], template[:, w // 2:],
                template[: h // 2, :], template[h // 2:, :],
            )
        )

    @classmethod
    def load(
        cls,
        regions: str | Path | ScreenRegions = DEFAULT_REGIONS,
        template: str | Path = DEFAULT_TEMPLATE,
        thresholds: ButtonThresholds | None = None,
    ) -> "RerollButtonReader":
        import cv2

        loaded = regions if isinstance(regions, ScreenRegions) else ScreenRegions.load(regions)
        p = Path(template)
        if not p.is_file():
            raise ButtonReadError(
                f"chua co mau glyph {p}. Chay `python scripts/build_reroll_template.py "
                "--frame <khung man chon augment>` de sinh ra."
            )
        img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise ButtonReadError(f"{p} khong doc duoc nhu mot anh")
        return cls(loaded, img, thresholds)

    def region(self, slot: int) -> Region:
        return self.regions.region(SCREEN, SLOT_NAMES[slot])

    def read(self, frame: np.ndarray) -> RerollButtonReading:
        """Doc ca ba o tren mot khung BGR."""
        if frame is None or frame.size == 0:
            raise ButtonReadError("khung hinh rong")
        return RerollButtonReading(
            tuple(
                self.read_button(crop(frame, self.region(slot)), slot)
                for slot in range(len(SLOT_NAMES))
            )
        )

    def read_button(self, box: np.ndarray, slot: int = 0) -> ButtonRead:
        """Doc MOT o da cat san. `box` la anh BGR cua rieng cai nut."""
        import cv2

        if box is None or box.size == 0:
            raise ButtonReadError(f"o {slot + 1}: crop rong - kiem lai toa do ROI")
        if box.ndim != 3:
            raise ButtonReadError(f"o {slot + 1}: can anh BGR, nhan {box.ndim} chieu")
        if (box.shape[1], box.shape[0]) != BUTTON_SIZE:
            box = cv2.resize(box, BUTTON_SIZE, interpolation=cv2.INTER_AREA)

        gray = normalize_gray(cv2.cvtColor(box, cv2.COLOR_BGR2GRAY))
        match = max(
            float(cv2.matchTemplate(gray, half, cv2.TM_CCOEFF_NORMED).max())
            for half in self._halves
        )

        inner = box[_BORDER:-_BORDER, _BORDER:-_BORDER].astype(np.float32)
        flat = inner.reshape(-1, 3)
        mean = flat.mean(axis=0)
        warm = float(mean[2] - mean[0])

        # Mau NEN = 40% diem toi nhat. Net glyph sang va con tro chuot trang
        # deu keo trung binh len; lay phan toi nhat thi ca hai bi loai, va nen
        # nut la thu duy nhat con lai.
        lum = flat.mean(axis=1)
        floor = float(np.percentile(lum, _FILL_PERCENTILE))
        fill_value = float(flat[lum <= floor].mean())

        t = self.thresholds
        if match < t.min_glyph_match:
            return ButtonRead(slot, "unknown", match, warm, fill_value,
                              f"không thấy nút đổi thẻ ở ô {slot + 1} "
                              f"(khớp mẫu {match:.2f} < {t.min_glyph_match:.2f})")
        if fill_value < t.pressed_fill_value:
            return ButtonRead(slot, "pressed", match, warm, fill_value,
                              f"ô {slot + 1} đang trong khung nhấn — chưa ngã ngũ")
        if warm >= t.active_warm:
            return ButtonRead(slot, "active", match, warm, fill_value,
                              f"ô {slot + 1} còn lượt đổi")
        return ButtonRead(slot, "disabled", match, warm, fill_value,
                          f"ô {slot + 1} đã dùng lượt đổi")
