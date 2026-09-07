"""Hai cua so overlay + co che Win32 bat buoc (SPEC 3.6).

HAI CUA SO, KHONG PHAI MOT:
    - `passthrough`: click xuyen qua, hien khuyen nghi. Nguoi choi van thao tac
      voi game binh thuong khi con tro di ngang qua no.
    - `interactive`: nhan chuot, danh cho panel cai dat.
Gop lam mot thi hoac chan mat thao tac cua nguoi choi, hoac khong bam duoc gi.

WDA_EXCLUDEFROMCAPTURE: MAC DINH TAT (doi o ban danh gia rui ro 2026-09-04):
Truoc day co nay BAT BUOC, de overlay khong lot vao chinh anh ma no chup (vision
doc lai chu cua chinh minh -> khuyen nghi tu boi duong chinh no). Van de la that,
nhung cach chua thi sai:

    - Vong lap tu chup duoc GIAI QUYET TAN GOC bang cach chup THEO CUA SO GAME
      thay vi chup ca desktop. Chup theo cua so khong lay overlay cua tien trinh
      khac, nen vong lap khong hinh thanh - khong can goi API nao ca.
    - Ban than loi goi nay la thu duy nhat trong stack co HINH DANG giong ne
      tranh: `GetWindowDisplayAffinity` doc duoc "from any process" khong can
      quyen gi, vgk.sys co hook o `NtUserGetWindowDisplayAffinity`, va mot
      anti-cheat cung nganh (TAC cua Activision) da thu thap va gui gia tri nay
      ve server. Khong co bang chung Vanguard lam dieu do - nhung cung khong co
      ly do phai chiu rui ro khi da co cach khac.
    - Rieng ve mat trinh bay: Riot xac nhan (05-2024) ho CHUP vung man hinh ma
      client chiem, de tim ESP hack. Mot panel tu van HIEN RA se bi danh gia
      theo NOI DUNG (vo hai). Mot cua so co tinh an khoi anh chup bi danh gia
      theo HANH VI. Hien ra la lua chon dung voi chuan trung thuc cua SPEC 11.5.

Ham `apply_capture_protection()` duoc GIU LAI nguyen ven va van test day du: no
la duong lui cho may khong chup theo cua so duoc. Chi co MAC DINH la doi.

Yeu cau khi bat: Windows 10 build 19041 (2004) tro len. Duoi muc do, ha xuong
WDA_MONITOR (che bang o den trong anh chup) - van dung, chi xau hon, va PHAI bao
cho nguoi dung biet thay vi im lang bo qua.

TRACK B: file nay chi kiem tra duoc tren may co man hinh va co game dang chay.
Phan logic trinh bay da duoc tach sang widgets/augment_panel.py de test duoc.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any

# Hang so Win32 - xem tai lieu SetWindowDisplayAffinity.
WDA_NONE = 0x00
WDA_MONITOR = 0x01
WDA_EXCLUDEFROMCAPTURE = 0x11

# Build Windows dau tien ho tro WDA_EXCLUDEFROMCAPTURE.
MIN_BUILD_FOR_EXCLUDE = 19041


class OverlayUnavailableError(RuntimeError):
    """Khong dung duoc overlay tren moi truong hien tai."""


@dataclass
class CaptureProtection:
    """Ket qua dat co bao ve chong lot vao anh chup."""

    applied: int
    degraded: bool
    message: str

    @property
    def ok(self) -> bool:
        return self.applied != WDA_NONE


def windows_build() -> int:
    """So build Windows hien tai. Tra 0 khi khong phai Windows."""
    if sys.platform != "win32":
        return 0
    return int(getattr(sys.getwindowsversion(), "build", 0))


def apply_capture_protection(hwnd: int, build: int | None = None) -> CaptureProtection:
    """Dat SetWindowDisplayAffinity cho mot cua so.

    Ba dieu kien cua API (SPEC 3.6) - thieu bat ky cai nao deu that bai:
        - hwnd phai la top-level VA thuoc chinh process nay;
        - phai co DWM compositing;
        - build >= 19041 moi co WDA_EXCLUDEFROMCAPTURE.

    Returns:
        CaptureProtection - luon tra ve, khong nem ngoai le, de goi y ha cap
        duoc xu ly nhu mot trang thai binh thuong chu khong phai loi.
    """
    build = windows_build() if build is None else build
    if build == 0:
        return CaptureProtection(WDA_NONE, True, "Khong phai Windows - khong co bao ve chup man")

    import ctypes  # noqa: PLC0415 - chi can tren Windows

    user32 = ctypes.windll.user32
    wanted = WDA_EXCLUDEFROMCAPTURE if build >= MIN_BUILD_FOR_EXCLUDE else WDA_MONITOR

    ok = bool(user32.SetWindowDisplayAffinity(ctypes.c_void_p(hwnd), wanted))
    if not ok:
        return CaptureProtection(
            WDA_NONE,
            True,
            "SetWindowDisplayAffinity that bai - overlay CO THE lot vao anh chup. "
            "Kiem tra: cua so top-level, dung process, DWM dang bat.",
        )

    if wanted == WDA_MONITOR:
        return CaptureProtection(
            WDA_MONITOR,
            True,
            f"Windows build {build} < {MIN_BUILD_FOR_EXCLUDE}: ha xuong WDA_MONITOR - "
            "vung overlay se thanh o den trong anh chup, phai tranh ROI khi calibrate.",
        )
    return CaptureProtection(WDA_EXCLUDEFROMCAPTURE, False, "Bao ve chup man: day du")


def _qt():
    try:
        from PyQt6 import QtCore, QtWidgets  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover
        raise OverlayUnavailableError(f"can PyQt6 de chay overlay: {exc}") from exc
    return QtCore, QtWidgets


def create_windows(
    parent_app: Any = None, capture_protection: bool = False
) -> dict[str, Any]:
    """Tao ca hai cua so overlay.

    Args:
        parent_app: QApplication dang chay, neu co.
        capture_protection: bat SetWindowDisplayAffinity. MAC DINH TAT - xem
            docstring dau module. Chi bat khi khong chup theo cua so game duoc;
            khi do overlay phai duoc che khoi anh chup bang cach khac.

    Returns:
        {"passthrough": w1, "interactive": w2, "protection": {...}}
        `protection` rong khi capture_protection=False - khong co loi goi nao
        duoc thuc hien, khong phai "goi roi that bai".
    """
    QtCore, QtWidgets = _qt()

    base_flags = (
        QtCore.Qt.WindowType.FramelessWindowHint
        | QtCore.Qt.WindowType.WindowStaysOnTopHint
        | QtCore.Qt.WindowType.Tool
    )

    passthrough = QtWidgets.QWidget()
    # WindowTransparentForInput: PyQt6 expose san, KHONG can goi win32 thu cong.
    passthrough.setWindowFlags(base_flags | QtCore.Qt.WindowType.WindowTransparentForInput)
    passthrough.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
    passthrough.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating)

    interactive = QtWidgets.QWidget()
    interactive.setWindowFlags(base_flags)
    interactive.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)

    protection: dict[str, CaptureProtection] = {}
    if capture_protection:
        for name, window in (("passthrough", passthrough), ("interactive", interactive)):
            # winId() buoc Qt tao hwnd that - phai goi truoc khi dat affinity.
            protection[name] = apply_capture_protection(int(window.winId()))

    return {"passthrough": passthrough, "interactive": interactive, "protection": protection}
