"""Test nhan playtest va bo cham (moc M0).

Moi con so ky vong o day deu tinh tay tu kich ban nho, de bo cham duoc kiem
chung TRUOC khi dung no do baseline tren record that.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.eval.playtest_draft import Sample, group_screens, resolve_card_title, segment_screen
from src.eval.playtest_labels import LabelError, from_dict, load, save, validate
from src.eval.playtest_review import augment_options, resolve_slot, save_payload
from src.eval.playtest_metrics import ReadEvent, evaluate, load_run, save_run, slot_outcome
from src.knowledge.name_index import NameIndex

KNOWN = {"A", "B", "C", "D", "E", "P1", "P2"}


def label_dict(status: str = "verified") -> dict:
    return {
        "schema": 1,
        "video": "game.mp4",
        "size": [1920, 1080],
        "screens": [
            {
                "stage": "2-1",
                "status": status,
                "open_s": 100.0,
                "close_s": 130.0,
                "hud": {"gold": 30, "level": 5, "xp": None},
                "traits": None,
                "offers": [
                    {"at_s": 101.0, "cards": [["A"], ["B"], ["C"]]},
                    {"at_s": 110.0, "cards": [["A"], ["D"], ["C"]], "rerolled_slot": 1},
                ],
                "picked": "D",
            }
        ],
    }


def ev(t: float, a: str, b: str, c: str, gold: int | None = 30) -> ReadEvent:
    slot = lambda x: tuple(x.split("|")) if x else ()  # noqa: E731
    return ReadEvent(t=t, cards=(slot(a), slot(b), slot(c)), hud={"gold": gold, "level": 5})


# --- nhan -------------------------------------------------------------------


def test_valid_labels_have_no_errors():
    assert validate(from_dict(label_dict()), KNOWN) == []


def test_roundtrip(tmp_path):
    labels = from_dict(label_dict())
    save(labels, tmp_path / "x.json")
    assert load(tmp_path / "x.json", KNOWN).to_dict() == labels.to_dict()


def test_load_reports_all_errors(tmp_path):
    data = label_dict()
    s = data["screens"][0]
    s["stage"] = "hai-mot"
    s["offers"][1]["cards"][1] = ["ZZZ"]
    s["hud"]["mana"] = 3
    (tmp_path / "bad.json").write_text(__import__("json").dumps(data), encoding="utf-8")
    with pytest.raises(LabelError) as exc:
        load(tmp_path / "bad.json", KNOWN)
    text = str(exc.value)
    assert "stage" in text and "ZZZ" in text and "hud.mana" in text


def test_verified_rerolled_slot_must_match_changed_slot():
    data = label_dict()
    data["screens"][0]["offers"][1]["rerolled_slot"] = 0
    errors = validate(from_dict(data), KNOWN)
    assert any("ô thực sự đổi là [1]" in e for e in errors)


def test_draft_allows_empty_slots_and_missing_reroll_slot():
    data = label_dict("draft")
    data["screens"][0]["offers"][1]["cards"][1] = []
    data["screens"][0]["offers"][1]["rerolled_slot"] = None
    data["screens"][0]["picked"] = None
    assert validate(from_dict(data), KNOWN) == []


def test_offer_outside_screen_and_not_increasing():
    data = label_dict()
    data["screens"][0]["offers"][1]["at_s"] = 99.0
    errors = validate(from_dict(data), KNOWN)
    assert any("nằm ngoài" in e for e in errors)
    assert any("tăng dần" in e for e in errors)


def test_picked_must_be_in_last_offer():
    data = label_dict()
    data["screens"][0]["picked"] = "B"   # B da bi reroll mat
    assert any("picked" in e for e in validate(from_dict(data), KNOWN))


# --- cham -------------------------------------------------------------------


@pytest.mark.parametrize(
    "pred,truth,expected",
    [
        (["A"], ["A"], "correct"),
        (["B"], ["A"], "wrong_silent"),
        ([], ["A"], "missing"),
        (["P1"], ["P1", "P2"], "correct"),          # nhan la cap map mo
        (["P1", "P2"], ["P1"], "correct"),          # tra ca cap, su that nam trong
        (["A", "B"], ["C"], "wrong_silent"),
    ],
)
def test_slot_outcome(pred, truth, expected):
    assert slot_outcome(pred, truth) == expected


def test_read_once_at_open_misses_reroll():
    """Hanh vi run_replay.py d537eb0: doc 1 lan luc mo man."""
    report = evaluate(from_dict(label_dict()), [ev(102.0, "A", "B", "C")])
    # offer 1: 3 dung. offer 2: the dang hien van la B -> o 2 sai im lang.
    assert (report.slots, report.correct, report.wrong_silent) == (6, 5, 1)
    assert report.card_acc == pytest.approx(5 / 6)
    assert (report.rerolls, report.rerolls_caught) == (1, 0)
    assert report.offers_never_correct == 1
    assert report.latencies_s == [pytest.approx(1.0)]
    assert any("bỏ sót reroll ô 2" in f for f in report.failures)


def test_rereads_after_reroll_catch_it():
    run = [ev(102.0, "A", "B", "C"), ev(111.5, "A", "D", "C")]
    report = evaluate(from_dict(label_dict()), run)
    assert report.card_acc == 1.0
    assert report.reroll_recall == 1.0
    assert sorted(report.latencies_s) == [pytest.approx(1.0), pytest.approx(1.5)]


def test_reading_next_offer_early_is_not_wrong():
    """Nhãn ghi reroll lúc 110s; hệ thống đọc ra thẻ mới từ 105s -> vẫn là đọc đúng."""
    report = evaluate(from_dict(label_dict()), [ev(105.0, "A", "D", "C")])
    assert report.wrong_silent == 0 and report.early == 1
    assert report.correct == 6


def test_missing_read_and_hud():
    report = evaluate(from_dict(label_dict()), [ev(102.0, "A", "", "C", gold=0)])
    assert report.missing == 2          # o 2 trong ca hai offer
    assert report.hud_acc("gold") == 0.0
    assert report.hud_acc("level") == 1.0
    assert report.hud_acc("xp") is None  # nhan null -> khong cham


def test_no_reads_at_all():
    report = evaluate(from_dict(label_dict()), [])
    assert (report.missing, report.correct) == (6, 0)
    assert report.hud_acc("gold") == 0.0


def test_reads_outside_screen_are_ignored():
    report = evaluate(from_dict(label_dict()), [ev(50.0, "A", "D", "C"), ev(131.0, "A", "D", "C")])
    assert report.correct == 0


def test_read_slightly_before_open_counts_for_first_offer():
    report = evaluate(from_dict(label_dict()), [ev(99.5, "A", "B", "C")])
    assert report.correct == 5 and report.latencies_s == [0.0]


def test_draft_screens_are_skipped():
    report = evaluate(from_dict(label_dict("draft")), [ev(102.0, "A", "B", "C")])
    assert (report.screens_scored, report.screens_skipped_draft, report.slots) == (0, 1, 0)


def test_run_roundtrip(tmp_path):
    run = [ev(111.5, "A", "D|E", "C"), ev(102.0, "A", "B", "")]
    save_run(run, tmp_path / "run.jsonl")
    loaded = load_run(tmp_path / "run.jsonl")
    assert [e.t for e in loaded] == [102.0, 111.5]
    assert loaded[1].cards == (("A",), ("D", "E"), ("C",))


def test_report_dict_is_json_ready():
    import json

    report = evaluate(from_dict(label_dict()), [ev(102.0, "A", "B", "C")])
    d = json.loads(json.dumps(report.to_dict()))
    assert d["reroll_recall"] == 0.0 and d["read_latency_s"]["n"] == 1


# --- nhan nhap --------------------------------------------------------------

def thumbs(*levels: float) -> tuple[np.ndarray, ...]:
    return tuple(np.full((12, 48), v, np.float32) for v in levels)


def test_group_screens_merges_close_hits():
    times = [0, 1, 2, 3, 10, 11, 20]
    present = [False, True, True, False, True, True, False]
    assert group_screens(times, present, gap_s=3.0) == [(1, 2), (10, 11)]


A, P, D = "active", "pressed", "disabled"


def test_segment_uses_button_event_for_reroll_slot():
    seq = (
        [Sample(0.0, True, thumbs(0, 0, 0), (A, A, A))]                       # dang hien ra
        + [Sample(0.25 * i, True, thumbs(100, 100, 100), (A, A, A)) for i in range(1, 5)]
        + [Sample(1.25, True, thumbs(100, 100, 100), (A, P, A))]
        + [Sample(1.25 + 0.25 * i, True, thumbs(100, 108, 100), (A, D, A)) for i in range(1, 5)]
        + [Sample(2.5, False)]
    )
    screen = segment_screen(seq, stable_n=3)
    assert screen is not None
    assert [o.at_s for o in screen.offers] == [0.25, 1.5]
    assert screen.offers[1].rerolled_slot == 1          # doi chu chi lech 8 - van bat duoc
    assert (screen.open_s, screen.close_s) == (0.0, 2.25)


def test_segment_waits_for_slow_card_flip_after_press():
    seq = [Sample(i * 0.25, True, thumbs(100, 100, 100), (A, A, A)) for i in range(4)]
    seq += [Sample(1.0, True, thumbs(100, 100, 100), (A, A, P))]
    seq += [Sample(1.25 + 0.25 * i, True, thumbs(100, 100, 100), (A, A, D)) for i in range(4)]   # the chua doi
    seq += [Sample(2.25 + 0.25 * i, True, thumbs(100, 100, 109), (A, A, D)) for i in range(4)]
    screen = segment_screen(seq, stable_n=3)
    assert [(o.at_s, o.rerolled_slot) for o in screen.offers] == [(0.0, None), (2.25, 2)]


def test_group_screens_merges_hidden_panel():
    times = [float(t) for t in range(40)]
    present = [10 <= t <= 20 or 30 <= t <= 38 for t in range(40)]
    assert group_screens(times, present, gap_s=30.0) == [(10.0, 38.0)]


def test_segment_catches_two_quick_rerolls():
    """Roll ô 2 rồi roll ô 1 ngay sau đó, mỗi lần chỉ kịp yên 2 mẫu."""
    seq = [Sample(i * 0.25, True, thumbs(100, 100, 100), (A, A, A)) for i in range(4)]
    seq += [Sample(1.0, True, thumbs(100, 100, 100), (A, P, A)),
            Sample(1.25, True, thumbs(100, 108, 100), (A, D, A)),
            Sample(1.5, True, thumbs(100, 108, 100), (A, D, A)),
            Sample(1.75, True, thumbs(100, 108, 100), (P, D, A)),
            Sample(2.0, True, thumbs(112, 108, 100), (D, D, A)),
            Sample(2.25, True, thumbs(112, 108, 100), (D, D, A))]
    screen = segment_screen(seq, stable_n=3)
    assert [(o.at_s, o.rerolled_slot) for o in screen.offers] == [(0.0, None), (1.25, 1), (2.0, 0)]


def test_segment_ignores_settled_noise():
    seq = [Sample(i * 0.25, True, thumbs(100 + (i % 2) * 0.5, 100, 100), (A, A, A)) for i in range(10)]
    assert len(segment_screen(seq, stable_n=3).offers) == 1


def test_segment_content_change_without_button_event_has_no_slot():
    seq = [Sample(i, True, thumbs(100, 100, 100), (A, A, A)) for i in range(3)]
    seq += [Sample(3 + i, True, thumbs(90, 90, 100), (A, A, A)) for i in range(3)]
    screen = segment_screen(seq, stable_n=3)
    assert screen.offers[1].rerolled_slot is None
    assert screen.offers[1].changed_slots == [0, 1]


def test_segment_never_settled_still_yields_unsettled_offer():
    seq = [Sample(i * 0.25, True, thumbs(i * 10, i * 10, i * 10), (A, A, A)) for i in range(4)]
    screen = segment_screen(seq, stable_n=3)
    assert len(screen.offers) == 1 and not screen.offers[0].settled


def test_segment_reroll_right_before_close_is_kept_unsettled():
    seq = [Sample(i * 0.25, True, thumbs(100, 100, 100), (A, A, A)) for i in range(4)]
    seq += [Sample(1.0, True, thumbs(100, 100, 100), (P, A, A)), Sample(1.25, True, thumbs(106, 100, 100), (D, A, A))]
    screen = segment_screen(seq, stable_n=3)
    assert [o.settled for o in screen.offers] == [True, False]
    assert screen.offers[1].rerolled_slot == 0


def test_segment_press_across_flicker_is_not_lost():
    seq = [Sample(i * 0.25, True, thumbs(100, 100, 100), (A, A, A)) for i in range(4)]
    seq += [Sample(1.0, False), Sample(1.25, True, thumbs(100, 107, 100), (A, D, A)), Sample(1.5, False)]
    screen = segment_screen(seq, stable_n=3)
    assert screen.offers[-1].rerolled_slot == 1
    assert screen.offers[-1].at_s == 1.25                 # khung SAU khi doi, khong phai khung cu


def test_segment_none_without_screen():
    assert segment_screen([Sample(0.0, False)]) is None


def test_resolve_card_title_tries_joined_lines():
    index = NameIndex(by_norm={"augments": {"vi": {"tinh hoa rong": ["DA_X"], "bai hoc so khai": ["DA_Y"]}}})
    assert resolve_card_title(["Tinh Hoa", "Rồng", "mô tả dài"], index) == ["DA_X"]
    assert resolve_card_title(["Bài Hc Sơ Khai", "Đi ca bn"], index) == ["DA_Y"]   # OCR rơi dấu
    assert resolve_card_title(["Bài Tập"], index) == []
    assert resolve_card_title([], index) == []


# --- cong cu xem lai --------------------------------------------------------


def review_index() -> NameIndex:
    return NameIndex(display={"augments": {
        "DA_X": {"vi": "Tinh Hoa Rồng"},
        "DA_P1": {"vi": "Thực Vật Hấp Thụ"},
        "DA_P2": {"vi": "Thực Vật Hấp Thụ"},
    }})


def test_augment_options_group_ambiguous_pair():
    options = augment_options(review_index())
    assert {"vi": "Thực Vật Hấp Thụ", "api": ["DA_P1", "DA_P2"]} in options
    assert len(options) == 2


def test_resolve_slot_accepts_name_apiname_and_list():
    options = augment_options(review_index())
    assert resolve_slot("tinh hoa rong", options) == ["DA_X"]      # gõ không dấu vẫn ra
    assert resolve_slot("Thực Vật Hấp Thụ", options) == ["DA_P1", "DA_P2"]   # cặp mơ hồ: cả hai
    assert resolve_slot("DA_P2", options) == ["DA_P2"]             # gõ thẳng apiName
    assert resolve_slot("không có gì", options) == []


def test_save_payload_refuses_to_write_when_invalid(tmp_path):
    path = tmp_path / "labels.json"
    data = label_dict()
    data["screens"][0]["offers"][1]["rerolled_slot"] = 0
    labels, errors = save_payload(data, path, KNOWN)
    assert labels is None and errors and not path.exists()


def test_save_payload_writes_when_valid(tmp_path):
    path = tmp_path / "labels.json"
    labels, errors = save_payload(label_dict(), path, KNOWN)
    assert errors == [] and labels is not None
    assert load(path, KNOWN).screens[0].verified
