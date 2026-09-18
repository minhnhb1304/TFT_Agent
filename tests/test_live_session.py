"""Test lõi dùng chung cho replay và live (mốc M1).

Mọi tình huống ở đây đều lấy từ buổi test 2026-09-16 và đo được trong
docs/playtest-fixes/eval-dataset.md — đặc biệt là ba lỗi đã làm hỏng buổi đó:
đọc một lần rồi thôi, đọc HUD đúng lúc HUD bị che, và coi việc ẩn màn chọn lõi
là đóng màn.

Không cần OCR, không cần Gemini, không cần Qt: mọi bộ đọc đều được tiêm vào.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pytest

from src.capture.frame_source import Frame
from src.capture.regions import Region, ScreenRegions
from src.live.events import AdviceReady, Cleared, Idle, Status
from src.live.session import LiveSession
from src.vision.augment_reader import CardRead
from src.vision.hud_reader import FieldRead, HudReading
from src.vision.reroll_buttons import ButtonRead, RerollButtonReading

cv2 = pytest.importorskip("cv2")

W, H = 1920, 1080


def regions() -> ScreenRegions:
    return ScreenRegions(
        screens={
            "hud": {"traits": Region.from_pixels(0, 258, 238, 792, W, H)},
            "augment_select": {
                "card_text_0": Region.from_pixels(410, 515, 690, 700, W, H),
                "card_text_1": Region.from_pixels(820, 515, 1100, 700, W, H),
                "card_text_2": Region.from_pixels(1230, 515, 1510, 700, W, H),
            },
        },
        blockers={},
        meta={"set": "TFTSet18"},
    )


def frame(t: float, cards: tuple[int, int, int] = (60, 60, 60)) -> Frame:
    """Khung hình với ba ô có độ sáng cho trước — đổi số = đổi nội dung thẻ."""
    image = np.zeros((H, W, 3), np.uint8)
    for slot, value in enumerate(cards):
        x0 = (410, 820, 1230)[slot]
        image[515:700, x0:x0 + 280] = value
    return Frame(image=image, t=t, ref=f"test@{t}")


def buttons(states: tuple[str, str, str]) -> RerollButtonReading:
    return RerollButtonReading(tuple(
        ButtonRead(i, s, 0.9, 30.0, 0.0, "test") for i, s in enumerate(states)
    ))


class FakeButtonReader:
    def __init__(self) -> None:
        self.states: tuple[str, str, str] = ("active", "active", "active")
        self.present = True

    def read(self, image) -> RerollButtonReading:
        if not self.present:
            return RerollButtonReading(tuple(
                ButtonRead(i, "unknown", 0.1, 0.0, 0.0, "không có màn") for i in range(3)
            ))
        return buttons(self.states)


class FakeHudReader:
    def __init__(self, gold: int = 32, level: int = 6, stage: str = "3-2") -> None:
        self.values = {"gold": gold, "level": level, "stage": stage, "hp": 88, "xp": 4, "xp_needed": 10}
        self.calls = 0

    def read(self, image) -> HudReading:
        self.calls += 1
        return HudReading(fields=tuple(
            FieldRead(k, v, str(v), True, "test", 1.0) for k, v in self.values.items()
        ))


@dataclass
class FakeCardReader:
    """Trả tên lõi theo ĐỘ SÁNG của ô — mô phỏng 'thẻ đổi thì đọc ra tên khác'."""

    name: str = "fake"
    calls: list[tuple[int, int]] = field(default_factory=list)

    def read_slot(self, image, slot: int) -> CardRead:
        x0 = (410, 820, 1230)[slot]
        value = int(image[600, x0 + 10, 0])
        self.calls.append((slot, value))
        return CardRead(slot, f"card{value}", "", (f"DA_{value}",), 1.0, "ok")

    def read_traits(self, image) -> dict[str, int]:
        return {"Vanguard": 2}


class FakeAdvisor:
    def __init__(self) -> None:
        self.states = []

    def advise(self, state, choices=None, frame_ref=None, rerolls=None):
        self.states.append(state)
        return {"choices": [c.api_names[0] for c in choices or []], "rerolls": rerolls}


def session(**kwargs) -> tuple[LiveSession, FakeButtonReader, FakeCardReader, FakeHudReader]:
    reroll, cards, hud = FakeButtonReader(), FakeCardReader(), FakeHudReader()
    s = LiveSession(
        card_reader=cards, hud_reader=hud, reroll_reader=reroll,
        advisor=FakeAdvisor(), regions=regions(), **kwargs,
    )
    return s, reroll, cards, hud


def feed(s: LiveSession, t0: float, n: int, cards=(60, 60, 60), step: float = 0.2):
    """Đẩy n khung giống nhau, trả về sự kiện cuối cùng khác Idle (nếu có)."""
    out = None
    for i in range(n):
        ev = s.step(frame(t0 + i * step, cards))
        if not isinstance(ev, Idle):
            out = ev
    return out


# --- ngoài màn chọn lõi -----------------------------------------------------


def test_no_card_read_outside_augment_screen():
    s, reroll, cards, hud = session()
    reroll.present = False
    for i in range(10):
        assert isinstance(s.step(frame(i * 0.2)), Idle)
    assert cards.calls == []


def test_hud_primed_outside_screen_and_used_inside():
    """Màn chọn lõi che vàng/cấp — giá trị phải đến từ lúc TRƯỚC khi mở màn."""
    s, reroll, cards, hud = session(hud_every_s=1.0)
    reroll.present = False
    for i in range(10):
        s.step(frame(i * 1.0))
    reroll.present = True
    ev = feed(s, 20.0, 4)
    assert isinstance(ev, AdviceReady)
    assert (ev.state.gold, ev.state.level, ev.state.xp_needed) == (32, 6, 10)


def test_hud_read_is_rate_limited():
    s, reroll, cards, hud = session(hud_every_s=3.0)
    reroll.present = False
    for i in range(31):
        s.step(frame(i * 0.2))       # 0 → 6.0 giây
    assert hud.calls == 3            # t=0, 3, 6 — không phải 31 lần


# --- trong màn chọn lõi -----------------------------------------------------


def test_reads_once_when_cards_settle():
    s, reroll, cards, hud = session()
    ev = feed(s, 0.0, 6)
    assert isinstance(ev, AdviceReady)
    assert sorted(c[0] for c in cards.calls) == [0, 1, 2]     # mỗi ô đúng một lần
    assert ev.rerolls.available == (True, True, True)


def test_unsettled_cards_are_not_read():
    """Thẻ đang lật (khung nào cũng khác) thì chưa đọc."""
    s, reroll, cards, hud = session()
    for i in range(6):
        s.step(frame(i * 0.2, (60 + i * 30, 60, 60)))
    assert all(slot != 0 for slot, _ in cards.calls)


def test_reroll_triggers_reread_of_that_slot_only():
    s, reroll, cards, hud = session()
    feed(s, 0.0, 5)
    cards.calls.clear()

    reroll.states = ("active", "pressed", "active")           # bấm đổi ô 2
    s.step(frame(1.0, (60, 60, 60)))
    reroll.states = ("active", "disabled", "active")
    ev = feed(s, 1.2, 4, cards=(60, 150, 60))                 # ô 2 đổi nội dung

    assert isinstance(ev, AdviceReady)
    assert {slot for slot, _ in cards.calls} == {1}           # chỉ đọc lại ô vừa đổi
    assert [tuple(c.api_names)[0] for c in ev.cards] == ["DA_60", "DA_150", "DA_60"]
    assert ev.rerolls.available == (True, False, True)


def test_two_quick_rerolls_are_both_caught():
    """Roll hai ô liền tay, mỗi lần chỉ kịp yên 2 khung (record 2026-09-16, game 2)."""
    s, reroll, cards, hud = session()
    feed(s, 0.0, 5)

    reroll.states = ("active", "pressed", "active")
    s.step(frame(1.0))
    reroll.states = ("active", "disabled", "active")
    first = feed(s, 1.2, 2, cards=(60, 150, 60))

    reroll.states = ("pressed", "disabled", "active")
    s.step(frame(1.8, (60, 150, 60)))
    reroll.states = ("disabled", "disabled", "active")
    second = feed(s, 2.0, 2, cards=(200, 150, 60))

    assert isinstance(first, AdviceReady) and isinstance(second, AdviceReady)
    assert [tuple(c.api_names)[0] for c in second.cards] == ["DA_200", "DA_150", "DA_60"]


def test_card_change_without_button_event_still_rereads():
    """Mất nhịp khung hình nên không thấy lúc bấm — nội dung đổi vẫn phải đọc lại."""
    s, reroll, cards, hud = session()
    feed(s, 0.0, 5)
    cards.calls.clear()
    ev = feed(s, 1.0, 5, cards=(60, 60, 210))
    assert isinstance(ev, AdviceReady)
    assert {slot for slot, _ in cards.calls} == {2}


def test_same_screen_emits_once():
    s, reroll, cards, hud = session()
    feed(s, 0.0, 5)
    assert all(isinstance(s.step(frame(2.0 + i * 0.2)), Idle) for i in range(5))


def test_force_refresh_rereads_everything():
    s, reroll, cards, hud = session()
    feed(s, 0.0, 5)
    cards.calls.clear()
    s.force_refresh()
    ev = feed(s, 2.0, 4)
    assert isinstance(ev, AdviceReady)
    assert sorted(slot for slot, _ in cards.calls) == [0, 1, 2]


def test_unread_slot_is_reported_not_hidden():
    class BlindReader(FakeCardReader):
        def read_slot(self, image, slot):
            if slot == 1:
                return CardRead(1, "", "", (), 0.0, "OCR không đọc được")
            return super().read_slot(image, slot)

    s, reroll, cards, hud = session()
    s.card_reader = BlindReader()
    ev = feed(s, 0.0, 5)
    assert isinstance(ev, AdviceReady)
    assert ev.unread_slots == (1,)


def test_no_readable_card_gives_status_not_silence():
    class DeadReader(FakeCardReader):
        def read_slot(self, image, slot):
            return CardRead(slot, "", "", (), 0.0, "OCR trắng")

    s, reroll, cards, hud = session()
    s.card_reader = DeadReader()
    ev = feed(s, 0.0, 5)
    assert isinstance(ev, Status) and len(ev.degraded) == 3


# --- rời màn / ẩn màn -------------------------------------------------------


def test_hiding_the_panel_is_not_leaving_the_screen():
    """Người chơi ẩn màn ~10 s để xem bàn cờ rồi mở lại: không mất lượt reroll."""
    s, reroll, cards, hud = session(grace_s=30.0)
    feed(s, 0.0, 5)
    reroll.states = ("active", "disabled", "active")
    s.step(frame(1.2))

    reroll.present = False
    for i in range(50):                                   # 10 giây không thấy màn
        assert not isinstance(s.step(frame(2.0 + i * 0.2)), Cleared)

    reroll.present = True
    cards.calls.clear()
    ev = feed(s, 13.0, 4, cards=(60, 150, 60))
    assert isinstance(ev, AdviceReady)
    assert ev.rerolls.available == (True, False, True)     # vẫn nhớ ô 2 đã dùng


def test_leaving_the_screen_clears_after_grace():
    s, reroll, cards, hud = session(grace_s=2.0)
    feed(s, 0.0, 5)
    reroll.present = False
    events = [s.step(frame(2.0 + i * 0.5)) for i in range(12)]
    assert sum(isinstance(e, Cleared) for e in events) == 1


def test_seek_backwards_starts_a_new_game():
    s, reroll, cards, hud = session()
    feed(s, 100.0, 5)
    hud.values["gold"] = 99
    s.seek(10.0)
    reroll.present = False
    s.step(frame(10.0))
    reroll.present = True
    ev = feed(s, 11.0, 4)
    assert isinstance(ev, AdviceReady) and ev.state.gold == 99


def test_reader_failure_becomes_status_not_crash():
    class Boom:
        def read(self, image):
            raise RuntimeError("template hỏng")

    s, reroll, cards, hud = session()
    s.reroll_reader = Boom()
    ev = s.step(frame(0.0))
    assert isinstance(ev, Status) and "template hỏng" in ev.message


def test_live_core_never_imports_qt():
    """Lõi phải chạy headless: một import Qt ở đây là hai vỏ bắt đầu lệch nhau."""
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent / "src" / "live"
    for path in root.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            assert not any(n.lower().startswith(("pyqt", "pyside")) for n in names), path.name
