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


def test_overlay_badges_sit_on_the_reader_regions_at_16_10():
    """Huy hiệu neo vào đúng vùng bộ đọc cắt — 16:10 dùng chung điểm neo `center`."""
    from src.capture.regions import Region, ScreenRegions
    from src.replay import overlay

    boxes = {f"card_text_{i}": Region(0.213542 + 0.213541 * i, 0.476852, 0.145833, 0.171296, "center")
             for i in range(3)}
    boxes |= {f"reroll_{i}": Region(0.260417 + 0.213541 * i, 0.772222, 0.052083, 0.048148, "center")
              for i in range(3)}
    regions = ScreenRegions({"augment_select": boxes}, {}, {})

    lay = overlay.layout(regions, 1728, 1080)
    assert lay.cards[0] == (314, 515, 594, 700)          # đo trên khung dat_01, 2-1
    assert lay.rerolls[2][0] == 1224
    left, _, right, _ = lay.verdict
    assert abs((left + right) / 2 - 864) <= 1


def test_overlay_frost_only_touches_its_rect():
    import numpy as np

    from src.replay import overlay

    rgb = np.full((100, 200, 3), 200, dtype=np.uint8)
    overlay.frost(rgb, (50, 20, 150, 60))
    assert rgb[40, 100].max() < 200
    assert (rgb[0:20] == 200).all() and (rgb[:, 0:50] == 200).all()


def test_overlay_badge_text_flags_unread_and_uncertain_cards():
    from src.replay.overlay import badge_text
    from src.replay.viewmodel import SlotVM

    assert badge_text(SlotVM(0, "x", unread=True)) == "chưa đọc được"
    assert badge_text(SlotVM(0, "x", score=6.1, rank=2)) == "#2  6.10"
    assert badge_text(SlotVM(0, "x", score=6.1, rank=2, low_confidence=True)).endswith("~")


def _advice_event(cards, entries, reroll=None):
    from types import SimpleNamespace as NS

    return NS(
        cards=[NS(slot=i, title=t, api_names=tuple(a), confidence=c, reason="") for i, (t, a, c) in enumerate(cards)],
        bundle=NS(ranking=NS(entries=[NS(api_name=a, name=n, total=v, components={}, reasons=[])
                                      for a, n, v in entries]),
                  reroll=reroll, economy=[], stale_data=[]),
        state=None, rerolls=None,
    )


def test_view_names_cards_as_the_client_does():
    """Tên trên thẻ (tiếng client), không phải tên CDragon en_us của ranking."""
    from src.replay.viewmodel import build_view

    event = _advice_event([("Phình Đại", ["DA_Embiggen"], 1.0)], [("DA_Embiggen", "Embiggen", 0.4)])
    _, verdict, slots = build_view(event)
    assert slots[0].name == "Phình Đại" and verdict.name == "Phình Đại"


def test_view_ranks_within_the_three_slots_when_a_card_is_ambiguous():
    """dat_01 3-2: ô 3 đọc ra Nidalee/Sivir → ranking 4 dòng, ô cuối từng hiện #4."""
    from src.replay.viewmodel import build_view

    event = _advice_event(
        [("X", ["A1", "A2"], 0.6), ("Y", ["B"], 1.0), ("Z", ["C1", "C2"], 0.6)],
        [("B", "B", 0.57), ("A1", "A", 0.51), ("A2", "A", 0.51), ("C1", "C", 0.45), ("C2", "C", 0.45)],
    )
    _, _, slots = build_view(event)
    assert [s.rank for s in slots] == [2, 1, 3]


def test_reroll_verdict_labels_its_number_as_expected_gain():
    """Khi ĐỔI, `delta` là lợi kỳ vọng của chính sách — không phải 'hơn lựa chọn kế'."""
    from types import SimpleNamespace as NS

    from src.replay.viewmodel import build_view

    event = _advice_event(
        [("X", ["A"], 1.0), ("Y", ["B"], 1.0)], [("A", "A", 0.5), ("B", "B", 0.4)],
        reroll=NS(action="REROLL", target_slot=1, expected_gain=0.012, reason=""),
    )
    _, verdict, _ = build_view(event)
    assert verdict.delta_text == "lợi kỳ vọng +0.01"
