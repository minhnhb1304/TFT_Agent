"""Thi hanh SPEC 1.3 + 11.4 bang test, khong bang loi hua.

Kien truc cua du an nay PHAI thuan read-only. Module nay quet AST cua toan bo
source, khong phai grep text - nghia la mot comment nhac den "SendInput" thi
khong sao, nhung mot lenh import/goi that su thi build do ngay.

Vi sao dung AST thay vi grep:
    grep se bao dong gia (false positive) o docstring va comment, roi nguoi ta
    se tat test di. AST chi bat lenh THUC SU chay, nen test nay dang tin cay
    va khong ai co dong co vo hieu hoa no.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# Thu muc duoc quet. KHONG quet tests/ - chinh file nay chua cac ten bi cam.
SCANNED_DIRS = ("src", "scripts", "tools")

# File .py nam ngay goc repo cung phai quet (KHONG de quy - chi tang tren cung).
# Ly do: mot entry point tuong lai kieu main.py / run.py se nam o day, va neu
# khong quet thi no la lo hong ngay giua hang rao an toan.
SCAN_REPO_ROOT = True

# --- Module bi cam import hoan toan ---------------------------------------
# Deu la thu vien tao input tong hop (synthetic input) -> vi pham SPEC 1.3.
#
# `keyboard` bi cam HOAN TOAN chu khong chi cam ham gui input: no cai
# SetWindowsHookEx(WH_KEYBOARD_LL) ngay khi dang ky hotkey, tuc la chinh cai
# hanh vi ma SPEC 1.3 goi ten la "loai anti-cheat heuristic de y toi".
# src/utils/hotkeys.py chung minh khong can no: RegisterHotKey lam duoc viec
# do ma khong hook, khong can admin. Cam mot nua thi khong mua duoc gi.
FORBIDDEN_MODULES = frozenset({
    "pyautogui",
    "pydirectinput",
    "pynput",
    "pywinauto",
    "autoit",
    "directinput",
    "keyboard",
})

# --- Ten ham / thuoc tinh bi cam su dung ----------------------------------
# Bat ke goi qua ctypes, win32api hay bat ky duong nao khac.
FORBIDDEN_SYMBOLS = frozenset({
    # Input injection
    "SendInput", "keybd_event", "mouse_event", "SendMessage", "PostMessage",
    # Doc/ghi bo nho tien trinh khac
    "ReadProcessMemory", "WriteProcessMemory", "VirtualAllocEx",
    "VirtualProtectEx", "NtReadVirtualMemory", "NtWriteVirtualMemory",
    # Injection
    "OpenProcess", "CreateRemoteThread", "LoadLibraryA", "LoadLibraryW",
    "QueueUserAPC", "SetThreadContext",
    # Render hooking
    "D3D11CreateDevice", "IDXGISwapChain", "detours",
    # Hook toan he thong. SPEC 1.3 goi ten WH_KEYBOARD_LL la hanh vi rui ro
    # nhat trong ca tai lieu - nhung truoc day test lai KHONG bat no. Mot hook
    # cap thap nhin thay moi phim cua moi ung dung tren may; do la thu duy nhat
    # trong stack nay co hinh dang giong keylogger.
    "SetWindowsHookEx", "SetWindowsHookExA", "SetWindowsHookExW",
    "SetWinEventHook", "WH_KEYBOARD_LL", "WH_MOUSE_LL",
})

# Ham gui input cua thu vien `keyboard`. Giu lai lam lop phong thu thu hai:
# `keyboard` da bi cam o FORBIDDEN_MODULES, nen muon goi duoc cac ham nay thi
# phai qua mot lenh import da bi chan truoc do.
FORBIDDEN_KEYBOARD_CALLS = frozenset({"send", "write", "press", "release", "press_and_release"})


def _iter_source_files() -> list[Path]:
    """Tra ve moi file .py trong cac thu muc duoc quet + goc repo."""
    root = Path(__file__).resolve().parent.parent
    files: list[Path] = []
    for d in SCANNED_DIRS:
        target = root / d
        if target.exists():
            files.extend(sorted(target.rglob("*.py")))
    if SCAN_REPO_ROOT:
        # glob khong de quy: chi file .py nam truc tiep o goc, khong keo theo
        # .venv/ hay tests/ (tests/ co chua ten bi cam mot cach hop phap).
        files.extend(sorted(root.glob("*.py")))
    return files


def _violations_in(path: Path) -> list[str]:
    """Quet AST mot file, tra ve danh sach vi pham dang doc duoc."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:  # file hong thi bao loi ro rang, khong nuot
        return [f"{path}: khong parse duoc AST ({exc})"]

    found: list[str] = []

    for node in ast.walk(tree):
        # import pyautogui / import pynput.mouse
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in FORBIDDEN_MODULES:
                    found.append(f"{path}:{node.lineno} import module bi cam '{alias.name}'")

        # from pyautogui import click
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                if top in FORBIDDEN_MODULES:
                    found.append(f"{path}:{node.lineno} import tu module bi cam '{node.module}'")

        # windll.user32.SendInput(...) / win32api.keybd_event(...)
        elif isinstance(node, ast.Attribute):
            if node.attr in FORBIDDEN_SYMBOLS:
                found.append(f"{path}:{node.lineno} dung symbol bi cam '{node.attr}'")
            # keyboard.send(...)
            if (
                node.attr in FORBIDDEN_KEYBOARD_CALLS
                and isinstance(node.value, ast.Name)
                and node.value.id == "keyboard"
            ):
                found.append(f"{path}:{node.lineno} goi keyboard.{node.attr}() - gui input bi cam")

        # SendInput(...) goi truc tiep sau khi da import ten
        elif isinstance(node, ast.Name):
            if node.id in FORBIDDEN_SYMBOLS:
                found.append(f"{path}:{node.lineno} dung symbol bi cam '{node.id}'")

    return found


def test_no_forbidden_symbol_in_source() -> None:
    """SPEC 1.3 phai la thuoc tinh KIEM CHUNG DUOC cua source code."""
    all_violations: list[str] = []
    for path in _iter_source_files():
        all_violations.extend(_violations_in(path))

    assert not all_violations, (
        "Vi pham bat bien read-only (SPEC 1.3 / 11.4):\n  "
        + "\n  ".join(all_violations)
    )


def test_scanner_actually_catches_violations(tmp_path: Path) -> None:
    """Meta-test: chung minh scanner khong phai la test rong.

    Mot test luon xanh vi no khong kiem tra gi ca thi vo dung. Test nay nap
    mot file vi pham co y va yeu cau scanner phai bat duoc.
    """
    bad = tmp_path / "bad_module.py"
    bad.write_text(
        "import pyautogui\n"
        "from ctypes import windll\n"
        "def go():\n"
        "    windll.user32.SendInput(1)\n"
        "    windll.kernel32.ReadProcessMemory(0, 0, 0, 0, 0)\n",
        encoding="utf-8",
    )
    violations = _violations_in(bad)
    joined = " ".join(violations)
    assert "pyautogui" in joined
    assert "SendInput" in joined
    assert "ReadProcessMemory" in joined


@pytest.mark.parametrize(
    "symbol",
    ["SetWindowsHookEx", "SetWindowsHookExA", "SetWindowsHookExW", "SetWinEventHook"],
)
def test_scanner_catches_global_hooks(tmp_path: Path, symbol: str) -> None:
    """Moi ten hook phai duoc chung minh la bat duoc, khong chi nam trong set.

    Mot ten nam trong FORBIDDEN_SYMBOLS ma khong ai chung minh scanner bat duoc
    thi chi la trang tri. SPEC 1.3 goi WH_KEYBOARD_LL la rui ro lon nhat trong
    tai lieu, nen no phai co bang chung rieng.
    """
    bad = tmp_path / f"hook_{symbol}.py"
    bad.write_text(
        "from ctypes import windll\n"
        "def go():\n"
        f"    windll.user32.{symbol}(13, None, None, 0)\n",
        encoding="utf-8",
    )
    joined = " ".join(_violations_in(bad))
    assert symbol in joined


def test_scanner_catches_keyboard_module_entirely(tmp_path: Path) -> None:
    """`keyboard` bi cam ca khi chi dung de NGHE, khong chi khi gui input.

    Truoc day chi cac ham gui (send/write/press) bi cam, nen
    `import keyboard; keyboard.add_hotkey(...)` van xanh - trong khi no cai
    SetWindowsHookEx(WH_KEYBOARD_LL) that su. Day la lo hong da duoc bit.
    """
    bad = tmp_path / "listen_only.py"
    bad.write_text(
        "import keyboard\n"
        "def go():\n"
        "    keyboard.add_hotkey('f1', lambda: None)\n",
        encoding="utf-8",
    )
    joined = " ".join(_violations_in(bad))
    assert "keyboard" in joined


def test_repo_root_is_scanned() -> None:
    """File .py o goc repo phai nam trong tap duoc quet.

    Neu sau nay co main.py / run.py o goc ma khong duoc quet, hang rao an toan
    co mot lo ngay giua. Test nay kiem tra CAU HINH quet, khong phu thuoc vao
    viec hien tai goc repo co file .py nao hay khong.
    """
    root = Path(__file__).resolve().parent.parent
    assert SCAN_REPO_ROOT, "goc repo phai duoc quet"
    scanned = _iter_source_files()
    for path in root.glob("*.py"):
        assert path in scanned, f"{path.name} o goc repo khong duoc quet"


def test_known_limitation_dynamic_attribute_lookup(tmp_path: Path) -> None:
    """Ghi lai GIOI HAN da biet: tra cuu dong (getattr / ordinal) khong bat duoc.

    Scanner khop theo TEN thuoc tinh trong AST, nen `getattr(user32, "SendInput")`
    di lot. Day KHONG phai bug can sua: mo hinh de doa cua file nay la so suat
    cua chinh tac gia trong tuong lai, khong phai mot doi thu co chu dich muon
    lach chinh hang rao minh dung len. Test nay ton tai de gioi han do duoc ghi
    thanh van ban thay vi bi tuong nham la khong ton tai.
    """
    sneaky = tmp_path / "sneaky.py"
    sneaky.write_text(
        "from ctypes import windll\n"
        "def go():\n"
        "    fn = getattr(windll.user32, 'Send' + 'Input')\n"
        "    return fn(1)\n",
        encoding="utf-8",
    )
    assert _violations_in(sneaky) == [], (
        "Neu test nay do, scanner da manh hon tai lieu mo ta - hay cap nhat "
        "docstring nay va SPEC 1.3 thay vi tat test."
    )


def test_comment_mentioning_forbidden_symbol_is_allowed(tmp_path: Path) -> None:
    """Nhac ten trong comment/docstring/string KHONG duoc tinh la vi pham.

    Day chinh la ly do dung AST thay vi grep - SPEC va docstring cua du an
    nay nhac den SendInput rat nhieu lan.
    """
    ok = tmp_path / "ok_module.py"
    ok.write_text(
        '"""Module nay KHONG dung SendInput hay ReadProcessMemory."""\n'
        "# pyautogui bi cam theo SPEC 1.3\n"
        "NOTE = 'khong duoc dung WriteProcessMemory'\n"
        "def go():\n"
        "    return 1\n",
        encoding="utf-8",
    )
    assert _violations_in(ok) == []
