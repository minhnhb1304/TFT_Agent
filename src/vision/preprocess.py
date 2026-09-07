"""Tien xu ly anh truoc khi OCR, va doc dau ra cua OCR cho an toan.

DO DUOC, KHONG PHAI DOAN (2026-09-07, tren VOD vQDqc9eiDpk @ 3,74 Mbps)

| Vung   | OCR tho          | Sau `binarize_for_ocr` |
|--------|------------------|------------------------|
| gold   | dung             | dung                   |
| xp     | dung             | dung                   |
| stage  | **truot**        | **3/3 dung**           |

`stage` truot vi chu mau kem tren nen lam - tuong phan thap, khong phai vi
nen video. Otsu bien no thanh den trang va van de bien mat. Vi the buoc nay
nam o day chu khong nam trong mot script: moi HUD reader ve sau deu can no,
va deu can dung MOT cach.

VI SAO KHONG DUNG CHO TEN AUGMENT

Tien xu ly khong cuu duoc tieng Viet co dau. Charset cua PP-OCRv6_rec_small
thieu 33/35 ky tu dau chong tang (ắ ễ ộ ừ...) va toan bo dau hoi/nang - do
tren anh SACH khong nen, moi co chu tu 18px den 96px deu sai. Ten augment
phai di duong Gemini Vision (SPEC 9.3). Dung goi ham nay roi ky vong doc
duoc `Cắm Rễ Phân Tán`.

DOC DAU RA OCR: KHONG BAO GIO DUNG `getattr(out, "txts")` TRUC TIEP

`requirements.txt` ghim `rapidocr>=3.9.2` khong chan tren. Ban 3.x tra ve
`RapidOCROutput` co `.txts`; ban 1.x/2.x tra ve tuple `(result, elapse)` voi
result la list `[box, text, score]`. Doc thang mot kieu thi khi thu vien doi
schema, ket qua thanh RONG mot cach IM LANG - khong loi, chi la "khong doc
duoc gi", va con so danh gia tut ma khong ai biet vi sao.

Them mot bay nua: `bool(RapidOCROutput)` la **False** khi khong co chu, nen
`if out:` bo qua ca truong hop hop le.
"""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

# He so phong to truoc khi OCR. Do tren cac o HUD 36x28..67x32: duoi 4 thi
# bo dinh vi chu thuong khong bat duoc vung nao ca.
DEFAULT_OCR_SCALE = 6

# Nguong nhan biet "thanh HUD dang hien": phai co CA chu gan trang LAN nen
# toi. Thieu mot trong hai la khung dang o vong carousel, dang xem board
# nguoi khac, hoac man loading - khi do o gold rong va khong co gi de doc.
_MIN_BRIGHT_PX = 12
_MIN_DARK_PX = 60
_BRIGHT_LEVEL = 200
_DARK_LEVEL = 90


def ocr_texts(result: Any) -> tuple[str, ...]:
    """Rut danh sach chuoi tu dau ra cua RapidOCR, chiu duoc nhieu schema.

    Nhan: `RapidOCROutput` (co `.txts`), tuple `(result, elapse)`, list cac
    `[box, text, score]`, list chuoi, hoac None. Tra ve tuple rong khi khong
    co gi - KHONG bao gio nem.
    """
    if result is None:
        return ()

    # Ban 3.x: doi tuong co .txts (hoac .txt o vai ban trung gian)
    for attr in ("txts", "txt"):
        if hasattr(result, attr):
            value = getattr(result, attr)
            if value is None:
                return ()
            if isinstance(value, str):
                return (value,)
            return tuple(str(v) for v in value if v is not None)

    # Ban 1.x/2.x: (result, elapse). Phan tu dau moi la du lieu.
    if isinstance(result, tuple) and len(result) == 2 and not isinstance(result[0], str):
        return ocr_texts(result[0])

    if isinstance(result, (list, tuple)):
        out: list[str] = []
        for row in result:
            if isinstance(row, str):
                out.append(row)
            elif isinstance(row, dict):
                for key in ("text", "txt", "rec_text"):
                    if key in row:
                        out.append(str(row[key]))
                        break
            elif isinstance(row, (list, tuple)) and len(row) >= 2:
                # dang [box, text, score]
                out.append(str(row[1]))
        return tuple(out)

    if isinstance(result, dict):
        for key in ("txts", "texts", "text"):
            if key in result:
                value = result[key]
                if isinstance(value, str):
                    return (value,)
                return tuple(str(v) for v in value)

    return ()


def ocr_join(result: Any, sep: str = "") -> str:
    """Toan bo chu doc duoc, noi lai thanh mot chuoi."""
    return sep.join(ocr_texts(result))


def has_digit(result: Any) -> bool:
    """Dau ra OCR co chua chu so nao khong."""
    return any(ch.isdigit() for ch in ocr_join(result))


def binarize_for_ocr(crop: np.ndarray, scale: int = DEFAULT_OCR_SCALE) -> np.ndarray:
    """Xam -> keo tuong phan -> Otsu -> phong to. Tra anh BGR cho OCR.

    Nem `ValueError` khi crop rong: mot mang 0x0 di tiep vao cv2 se nem mot
    loi kho hieu o tan sau, con o day thi noi ro cho nao sai.
    """
    if crop is None or crop.size == 0 or crop.shape[0] < 1 or crop.shape[1] < 1:
        raise ValueError("crop rong - kiem lai toa do ROI")
    if scale < 1:
        raise ValueError(f"scale phai >= 1, nhan duoc {scale}")

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
    gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if scale > 1:
        binary = cv2.resize(binary, None, fx=scale, fy=scale,
                            interpolation=cv2.INTER_CUBIC)
    return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)


def hud_bar_present(crop: np.ndarray) -> bool:
    """Khung nay co dang hien thanh HUD khong?

    Phan biet "OCR doc sai" voi "khong co gi de doc". Tren VOD dau tien,
    12/12 khung bi cham la truot deu la khung KHONG co thanh HUD (vong
    carousel, dang xem board nguoi khac, man loading) - gop chung vao ti le
    loi OCR la tu ha diem minh mot cach vo nghia.
    """
    if crop is None or crop.size == 0:
        return False
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
    bright = int((gray > _BRIGHT_LEVEL).sum())
    dark = int((gray < _DARK_LEVEL).sum())
    return bright >= _MIN_BRIGHT_PX and dark >= _MIN_DARK_PX
