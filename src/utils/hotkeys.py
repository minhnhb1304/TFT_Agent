"""Hotkey toan cuc qua RegisterHotKey - SPEC 1.3 / 3.6, feedback #10.

VI SAO KHONG DUNG THU VIEN `keyboard`
    Feedback #10 cam tuyet doi. Ly do ky thuat: `keyboard` cai
    `SetWindowsHookEx(WH_KEYBOARD_LL, ...)` - mot hook cap thap nhin THAY moi
    phim cua moi ung dung tren may, va thuong doi quyen admin. Do dung la
    hanh vi ma anti-cheat heuristic de y toi.

    RegisterHotKey lam viec khac han: no dang ky mot to hop voi HE DIEU HANH,
    va he dieu hanh post WM_HOTKEY vao message queue cua process nay khi to
    hop duoc bam. Khong hook, khong nhin phim nao khac, khong can admin. No
    van hoat dong khi game dang focus - vi chan o tang OS chu khong phai tang
    cua so.

VI SAO KHONG DUNG QShortcut
    PyQt6 khong co API global shortcut. `QShortcut` chi ban khi cua so cua no
    duoc focus - ma overlay dat `WA_ShowWithoutActivating` va
    `WindowTransparentForInput` (overlay_window.py) nen KHONG BAO GIO focus.
    QShortcut o day se khong bao gio ban. "Qt global shortcut" trong thuc te
    la RegisterHotKey + QAbstractNativeEventFilter, chinh la module nay.

KIEN TRUC HAI TANG (giong overlay_window.py)
    Tang A - thuan, khong Qt, khong Win32: parse_binding / plan_bindings.
             Test duoc headless, va do la phan de sai nhat.
    Tang B - GlobalHotkeyManager: cham ctypes + Qt, import muon, KHONG NEM.
             Dang ky that chi kiem chung duoc tren may co desktop (Track B).

    KHONG dung PostMessage/SendMessage o day de chuyen tiep phim: ca hai nam
    trong banlist cua tests/test_readonly_invariant.py va se lam do build.
    Ta chi DOC message do OS gui den, khong gui message cho ai.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

# Modifier cua RegisterHotKey (winuser.h).
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

# Khong lap khi giu phim. Bat buoc cho hotkey kieu toggle: thieu co nay thi
# giu F1 mot giay se bat/tat overlay hang chuc lan.
MOD_NOREPEAT = 0x4000

WM_HOTKEY = 0x0312

MODIFIER_TOKENS: dict[str, int] = {
    "ctrl": MOD_CONTROL,
    "control": MOD_CONTROL,
    "alt": MOD_ALT,
    "shift": MOD_SHIFT,
    "win": MOD_WIN,
    "super": MOD_WIN,
    "meta": MOD_WIN,
}

# Cac phim khong phai chu/so. Chu cai va chu so suy ra bang ord() ben duoi.
SPECIAL_KEYS: dict[str, int] = {
    "esc": 0x1B,
    "escape": 0x1B,
    "space": 0x20,
    "tab": 0x09,
    "enter": 0x0D,
    "return": 0x0D,
    "backspace": 0x08,
    "insert": 0x2D,
    "delete": 0x2E,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21,
    "pagedown": 0x22,
    "left": 0x25,
    "up": 0x26,
    "right": 0x27,
    "down": 0x28,
    "pause": 0x13,
    "grave": 0xC0,
}


class HotkeyError(ValueError):
    """Chuoi binding khong doc duoc. Fail sang luc nap config, khong luc bam."""


@dataclass(frozen=True)
class Binding:
    """Mot to hop phim da giai ma.

    Attributes:
        modifiers: co MOD_* da OR lai, DA gom MOD_NOREPEAT.
        vk: virtual-key code.
        text: chuoi goc trong config - de hien len UI va bao loi cho de hieu.
    """

    modifiers: int
    vk: int
    text: str

    @property
    def has_modifier(self) -> bool:
        return bool(self.modifiers & ~MOD_NOREPEAT)


def _vk_of(token: str) -> int:
    """Ten phim -> virtual-key code."""
    key = token.strip().lower()
    if not key:
        raise HotkeyError("thieu ten phim")

    if key in SPECIAL_KEYS:
        return SPECIAL_KEYS[key]

    # F1..F24 -> 0x70..0x87
    if key.startswith("f") and key[1:].isdigit():
        n = int(key[1:])
        if 1 <= n <= 24:
            return 0x6F + n
        raise HotkeyError(f"phim chuc nang ngoai khoang F1-F24: {token!r}")

    if len(key) == 1 and (key.isalpha() or key.isdigit()):
        return ord(key.upper())

    raise HotkeyError(f"khong nhan ra phim {token!r}")


def parse_binding(text: str) -> Binding:
    """Doc chuoi kieu "Ctrl+Q" / "F1" / "Ctrl+Shift+F5" thanh Binding.

    Nem HotkeyError neu khong doc duoc - co y: sai chinh ta trong settings.yaml
    phai lo ra luc khoi dong chu khong phai luc nguoi dung bam phim va khong
    thay gi xay ra.
    """
    raw = str(text).strip()
    if not raw:
        raise HotkeyError("chuoi binding rong")

    parts = [p for p in raw.replace("-", "+").split("+") if p.strip()]
    if not parts:
        raise HotkeyError(f"khong doc duoc binding {text!r}")

    modifiers = MOD_NOREPEAT
    for token in parts[:-1]:
        mod = MODIFIER_TOKENS.get(token.strip().lower())
        if mod is None:
            raise HotkeyError(f"khong nhan ra modifier {token!r} trong {text!r}")
        modifiers |= mod

    return Binding(modifiers, _vk_of(parts[-1]), raw)


def plan_bindings(config: dict[str, Any]) -> tuple[dict[str, Binding], dict[str, str]]:
    """Doc ca section `hotkeys` cua settings thanh cac Binding.

    Tra ve (binding hop le, loi theo ten hanh dong). Khong nem: mot binding
    hong khong duoc lam chet ca overlay - nhung cung khong duoc im lang, nen
    loi duoc tra ve de goi ben log ra.

    Gia tri rong ("" hoac None) nghia la TAT hanh dong do - khong phai loi.
    """
    ok: dict[str, Binding] = {}
    errors: dict[str, str] = {}
    for action, text in sorted((config or {}).items()):
        if text is None or str(text).strip() == "":
            continue
        try:
            ok[action] = parse_binding(str(text))
        except HotkeyError as exc:
            errors[action] = str(exc)
    return ok, errors


@dataclass
class HotkeyRegistration:
    """Ket qua dang ky mot hotkey voi he dieu hanh."""

    action: str
    binding: Binding
    ok: bool
    message: str = ""


def _qt() -> Any:
    """Import PyQt6 muon - module nay phai import duoc tren may khong co Qt."""
    from PyQt6 import QtCore  # noqa: PLC0415

    return QtCore


@dataclass
class GlobalHotkeyManager:
    """Dang ky hotkey voi OS va dieu phoi callback.

    Vong doi:
        mgr = GlobalHotkeyManager()
        mgr.bind("toggle_visibility", parse_binding("F1"), panel.toggle)
        results = mgr.install(app)      # can QApplication dang chay
        ...
        mgr.uninstall()

    `install` KHONG NEM. Mot to hop co the dang bi ung dung khac giu (VD F3
    cua mot overlay khac) - khi do RegisterHotKey tra 0 va ta ghi lai that
    bai do trong ket qua thay vi lam sap chuong trinh.
    """

    _bindings: dict[str, Binding] = field(default_factory=dict)
    _callbacks: dict[str, Callable[[], None]] = field(default_factory=dict)
    _ids: dict[int, str] = field(default_factory=dict)
    _filter: Any = None
    _app: Any = None

    def bind(self, action: str, binding: Binding, callback: Callable[[], None]) -> None:
        """Khai bao mot hotkey. Chua cham OS - install() moi lam viec do."""
        self._bindings[action] = binding
        self._callbacks[action] = callback

    def bind_all(
        self, bindings: dict[str, Binding], callbacks: dict[str, Callable[[], None]]
    ) -> None:
        """Khai bao nhieu hotkey; bo qua hanh dong khong co callback."""
        for action, binding in bindings.items():
            cb = callbacks.get(action)
            if cb is not None:
                self.bind(action, binding, cb)

    # -- tang cham he dieu hanh -------------------------------------------

    def install(self, app: Any = None) -> list[HotkeyRegistration]:
        """Dang ky toan bo binding voi OS va gan native event filter."""
        import ctypes  # noqa: PLC0415 - chi can tren Windows

        QtCore = _qt()
        user32 = ctypes.windll.user32

        results: list[HotkeyRegistration] = []
        for index, (action, binding) in enumerate(sorted(self._bindings.items()), start=1):
            # hwnd = 0: WM_HOTKEY di vao message queue cua THREAD, Qt van bat
            # duoc qua native event filter. Do la duong don gian nhat va khong
            # phu thuoc vao viec cua so nao dang ton tai.
            ok = bool(user32.RegisterHotKey(None, index, binding.modifiers, binding.vk))
            if ok:
                self._ids[index] = action
            results.append(
                HotkeyRegistration(
                    action,
                    binding,
                    ok,
                    "" if ok else f"{binding.text} co the dang bi ung dung khac giu",
                )
            )

        self._filter = _make_filter(QtCore, self._dispatch)
        self._app = app or QtCore.QCoreApplication.instance()
        if self._app is not None:
            self._app.installNativeEventFilter(self._filter)
        return results

    def uninstall(self) -> None:
        """Go het hotkey va event filter. An toan khi goi nhieu lan."""
        import ctypes  # noqa: PLC0415

        user32 = ctypes.windll.user32
        for hotkey_id in list(self._ids):
            user32.UnregisterHotKey(None, hotkey_id)
        self._ids.clear()

        if self._app is not None and self._filter is not None:
            self._app.removeNativeEventFilter(self._filter)
        self._filter = None
        self._app = None

    def _dispatch(self, hotkey_id: int) -> bool:
        """Chay callback cua mot hotkey id. True neu da xu ly."""
        action = self._ids.get(hotkey_id)
        if action is None:
            return False
        callback = self._callbacks.get(action)
        if callback is None:
            return False
        callback()
        return True


def _make_filter(QtCore: Any, dispatch: Callable[[int], bool]) -> Any:
    """Dung QAbstractNativeEventFilter doc WM_HOTKEY.

    Dinh nghia lop BEN TRONG ham, sau khi da import Qt - cung khuon mau voi
    overlay/widgets/augment_panel.create_panel: import module nay khong keo
    theo PyQt6, nen test chay duoc tren may khong co man hinh.
    """
    import ctypes  # noqa: PLC0415
    import ctypes.wintypes as wintypes  # noqa: PLC0415

    class MSG(ctypes.Structure):
        _fields_ = [
            ("hwnd", wintypes.HWND),
            ("message", wintypes.UINT),
            ("wParam", wintypes.WPARAM),
            ("lParam", wintypes.LPARAM),
            ("time", wintypes.DWORD),
            ("pt", wintypes.POINT),
        ]

    class _HotkeyFilter(QtCore.QAbstractNativeEventFilter):
        def nativeEventFilter(self, event_type: Any, message: Any) -> tuple[bool, int]:
            if event_type != b"windows_generic_MSG":
                return False, 0
            msg = ctypes.cast(int(message), ctypes.POINTER(MSG)).contents
            if msg.message == WM_HOTKEY:
                # wParam mang id hotkey da dang ky.
                return dispatch(int(msg.wParam)), 0
            return False, 0

    return _HotkeyFilter()
