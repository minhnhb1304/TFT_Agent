"""Test hotkey toan cuc (SPEC 1.3 / 3.6, feedback #10).

File nay bao ve mot rang buoc AN TOAN, khong chi mot tinh nang: hotkey phai
di qua RegisterHotKey cua he dieu hanh chu KHONG qua hook WH_KEYBOARD_LL ma
thu vien `keyboard` cai. Do la ly do test_module_does_not_use_keyboard_library
ton tai ben canh cac test giai ma phim thong thuong.

Chay khong can man hinh: chi tang thuan (parse_binding / plan_bindings) duoc
test o day. Phan cham Win32 + Qt chi kiem chung duoc tren may co desktop.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from src.utils.hotkeys import (
    MOD_ALT,
    MOD_CONTROL,
    MOD_NOREPEAT,
    MOD_SHIFT,
    MOD_WIN,
    HotkeyError,
    parse_binding,
    plan_bindings,
)
from src.utils.settings import Settings

MODULE = Path("src/utils/hotkeys.py")


# --- Giai ma binding -------------------------------------------------------


def test_function_keys_map_to_the_right_vk() -> None:
    """F1..F24 -> 0x70..0x87. Sai offset o day thi bam F1 ra hanh dong khac."""
    assert parse_binding("F1").vk == 0x70
    assert parse_binding("F4").vk == 0x73
    assert parse_binding("F12").vk == 0x7B
    assert parse_binding("F24").vk == 0x87


def test_letter_and_digit_keys() -> None:
    assert parse_binding("Ctrl+Q").vk == ord("Q")
    assert parse_binding("alt+7").vk == ord("7")


def test_modifiers_combine() -> None:
    b = parse_binding("Ctrl+Shift+Alt+Win+F5")
    assert b.modifiers & MOD_CONTROL
    assert b.modifiers & MOD_SHIFT
    assert b.modifiers & MOD_ALT
    assert b.modifiers & MOD_WIN
    assert b.vk == 0x74


def test_norepeat_is_always_set() -> None:
    """Thieu MOD_NOREPEAT thi giu F1 mot giay se toggle overlay hang chuc lan."""
    for text in ("F1", "Ctrl+Q", "alt+space"):
        assert parse_binding(text).modifiers & MOD_NOREPEAT, text


def test_parsing_is_case_insensitive_and_accepts_dash() -> None:
    """`text` giu nguyen van, nen so sanh phan da giai ma chu khong ca Binding."""
    lower, upper = parse_binding("ctrl+q"), parse_binding("CTRL+Q")
    assert (lower.modifiers, lower.vk) == (upper.modifiers, upper.vk)
    assert parse_binding("Ctrl-Q").vk == parse_binding("Ctrl+Q").vk


def test_binding_keeps_original_text_for_the_ui() -> None:
    assert parse_binding("Ctrl+Q").text == "Ctrl+Q"


def test_has_modifier_ignores_norepeat() -> None:
    """MOD_NOREPEAT khong phai modifier nguoi dung bam - khong duoc tinh vao."""
    assert not parse_binding("F1").has_modifier
    assert parse_binding("Ctrl+Q").has_modifier


@pytest.mark.parametrize(
    "bad",
    ["", "   ", "F0", "F25", "F99", "Hyper+X", "Ctrl+", "Ctrl+NotAKey"],
)
def test_bad_bindings_fail_loudly(bad: str) -> None:
    """Sai chinh ta trong settings.yaml phai lo ra luc NAP, khong phai luc bam.

    Kieu hong te nhat cua hotkey la im lang: nguoi dung bam phim, khong co gi
    xay ra, va khong co thong bao nao giai thich tai sao.
    """
    with pytest.raises(HotkeyError):
        parse_binding(bad)


# --- Doc ca section config -------------------------------------------------


def test_plan_bindings_collects_errors_instead_of_raising() -> None:
    """Mot binding hong khong duoc lam chet ca overlay - nhung phai bao cao."""
    ok, errors = plan_bindings({"a": "F2", "b": "F99", "c": "Hyper+X"})
    assert set(ok) == {"a"}
    assert set(errors) == {"b", "c"}
    assert "F99" in errors["b"]


def test_empty_binding_means_disabled_not_broken() -> None:
    ok, errors = plan_bindings({"quit": "", "toggle": None, "refresh": "F3"})
    assert set(ok) == {"refresh"}
    assert errors == {}


def test_shipped_settings_parse_cleanly() -> None:
    """Mac dinh trong config/settings.yaml phai giai ma duoc het.

    Day la test hop dong giua file config va module nay: doi ten phim trong
    yaml ma go sai thi build do ngay chu khong doi den luc chay.
    """
    ok, errors = plan_bindings(Settings.load("config/settings.yaml").data["hotkeys"])
    assert errors == {}
    assert set(ok) == {
        "toggle_visibility",
        "toggle_click_through",
        "force_refresh",
        "toggle_detail",
        "quit",
    }


# --- Rang buoc an toan (SPEC 1.3) -----------------------------------------


def test_module_does_not_use_keyboard_library() -> None:
    """Feedback #10: cam tuyet doi thu vien `keyboard`.

    No cai SetWindowsHookEx(WH_KEYBOARD_LL) - hook cap thap nhin thay moi phim
    cua moi ung dung, va thuong doi quyen admin. RegisterHotKey khong can ca
    hai. Quet AST chu khong grep, de nhac ten trong comment van hop le.
    """
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert "keyboard" not in imported
    assert "pynput" not in imported


def test_module_does_not_install_a_low_level_hook() -> None:
    """Khong duoc goi SetWindowsHookEx duoi bat ky dang nao."""
    source = MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    called = {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    } | {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    for banned in ("SetWindowsHookEx", "SetWindowsHookExA", "SetWindowsHookExW"):
        assert banned not in called


def test_module_never_sends_input_or_messages() -> None:
    """Chi DOC message OS gui den. Khong gui message cho ai (SPEC 1.3).

    PostMessage/SendMessage cung nam trong banlist cua
    tests/test_readonly_invariant.py; test nay noi ro ly do tai module nay.
    """
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    names = {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    } | {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    for banned in ("SendInput", "SendMessage", "PostMessage", "keybd_event"):
        assert banned not in names


def test_registerhotkey_is_the_mechanism() -> None:
    """Khang dinh duong: co dung RegisterHotKey, va co go ra bang Unregister."""
    source = MODULE.read_text(encoding="utf-8")
    assert "RegisterHotKey" in source
    assert "UnregisterHotKey" in source
