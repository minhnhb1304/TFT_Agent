"""Test co che bao ve chup man cua overlay (SPEC 3.6).

Chi test duoc phan QUYET DINH (chon co nao, ha cap khi nao). Phan goi Win32
that va phan ve chi kiem chung duoc tren may co man hinh + game dang chay -
do la Track B. Tach hai thu ra la de phan quyet dinh khong bi bo trong.
"""

from __future__ import annotations

from src.overlay.overlay_window import (
    MIN_BUILD_FOR_EXCLUDE,
    WDA_EXCLUDEFROMCAPTURE,
    WDA_MONITOR,
    WDA_NONE,
    apply_capture_protection,
    windows_build,
)


def test_constants_match_win32_documentation() -> None:
    """Sai mot hang so o day thi overlay am tham lot vao anh no tu chup."""
    assert (WDA_NONE, WDA_MONITOR, WDA_EXCLUDEFROMCAPTURE) == (0x00, 0x01, 0x11)
    assert MIN_BUILD_FOR_EXCLUDE == 19041


def test_non_windows_degrades_loudly_not_silently() -> None:
    result = apply_capture_protection(hwnd=0, build=0)
    assert not result.ok
    assert result.degraded
    assert result.message, "ha cap phai co thong bao, khong duoc im lang"


def test_windows_build_probe_is_safe_everywhere() -> None:
    assert windows_build() >= 0


def test_capture_protection_is_off_by_default() -> None:
    """Mac dinh TAT phai la thuoc tinh kiem chung duoc, khong phai y dinh.

    Danh gia rui ro 2026-09-04 ket luan: chup theo cua so game lam vong lap tu
    chup khong hinh thanh ve cau truc, nen khong can goi
    SetWindowDisplayAffinity - loi goi duy nhat trong stack co hinh dang giong
    ne tranh. Neu ai do doi mac dinh nay tro lai True, test do va buoc ho doc
    lai ly do thay vi doi am tham.

    Dung inspect thay vi goi create_windows() vi ham do can Qt + man hinh.
    """
    import inspect

    from src.overlay.overlay_window import create_windows

    default = inspect.signature(create_windows).parameters["capture_protection"].default
    assert default is False, (
        "capture_protection phai mac dinh False - xem docstring overlay_window "
        "va research/vanguard/ truoc khi doi"
    )
