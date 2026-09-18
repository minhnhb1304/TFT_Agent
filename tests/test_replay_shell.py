"""Test phần không phụ thuộc Qt của vỏ replay (mốc M1).

Widget Qt không được dựng trong test — theo đúng cách repo đang làm với overlay.
Cái phải khoá lại ở đây là **ranh giới**: vỏ chỉ được hiển thị, mọi việc đọc và
mọi GameState phải đến từ `src/live`. Đó chính là chỗ đã hỏng ở bản trước
(`run_replay.py` tự đọc HUD rồi tự dựng GameState thiếu XP và tộc/hệ).
"""

from __future__ import annotations

import ast
from pathlib import Path

from src.replay.scan import ScreenMarker, merge_spans

SHELL = Path(__file__).resolve().parent.parent / "src" / "replay"


def test_merge_spans_keeps_a_hidden_panel_as_one_screen():
    """Ẩn màn ~10 s để xem bàn cờ rồi mở lại vẫn là MỘT vòng chọn lõi."""
    times = [float(t) for t in range(40)]
    present = [10 <= t <= 20 or 30 <= t <= 38 for t in range(40)]
    assert merge_spans(times, present, gap_s=30.0) == [(10.0, 38.0)]


def test_merge_spans_splits_far_apart_screens():
    times = [float(t) for t in range(0, 200, 5)]
    present = [t in (10, 15, 120, 125) for t in times]
    assert merge_spans(times, present, gap_s=30.0) == [(10.0, 15.0), (120.0, 125.0)]


def test_marker_label_shows_stage_and_timestamp():
    assert ScreenMarker(626.75, 647.0, "3-2").label == "3-2 (10:26)"
    assert ScreenMarker(5.0, 9.0).label.startswith("?")


def _calls(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }


def test_window_never_reads_the_screen_itself():
    """Vỏ không được tự đọc thẻ hay HUD — nếu không hai vỏ sẽ lệch nhau."""
    forbidden = {"read_slot", "read_traits", "recognize_cards"}
    assert not (_calls(SHELL / "window.py") & forbidden)


def test_window_never_builds_game_state():
    """GameState phải đi kèm sự kiện, không được vỏ tự dựng lại."""
    tree = ast.parse((SHELL / "window.py").read_text(encoding="utf-8"))
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    names |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert "GameState" not in names


def test_scan_module_has_no_qt():
    """scan.py chạy được headless: dùng lại cho công cụ dòng lệnh và cho live."""
    tree = ast.parse((SHELL / "scan.py").read_text(encoding="utf-8"))
    imported = [
        name.name for node in ast.walk(tree)
        if isinstance(node, ast.Import) for name in node.names
    ] + [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    assert not any(m.lower().startswith(("pyqt", "pyside")) for m in imported)
