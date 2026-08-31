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

# --- Module bi cam import hoan toan ---------------------------------------
# Deu la thu vien tao input tong hop (synthetic input) -> vi pham SPEC 1.3.
FORBIDDEN_MODULES = frozenset({
    "pyautogui",
    "pydirectinput",
    "pynput",
    "pywinauto",
    "autoit",
    "directinput",
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
})

# Ham gui input cua thu vien `keyboard`. Ban than `keyboard` chi de LANG NGHE
# hotkey thi la danh doi da ghi ro o SPEC 1.3, nhung gui input thi bi cam.
FORBIDDEN_KEYBOARD_CALLS = frozenset({"send", "write", "press", "release", "press_and_release"})


def _iter_source_files() -> list[Path]:
    """Tra ve moi file .py trong cac thu muc duoc quet."""
    root = Path(__file__).resolve().parent.parent
    files: list[Path] = []
    for d in SCANNED_DIRS:
        target = root / d
        if target.exists():
            files.extend(sorted(target.rglob("*.py")))
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
