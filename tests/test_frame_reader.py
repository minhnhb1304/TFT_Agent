"""Test bo hop nhat khung hinh (src/vision/frame_reader.py).

Kiem tra:
1. Composition cua ca 3 chan (HUD, Augment, Rerolls) va GameStateTracker.
2. Mot chan hong khong lam crash toan bo quy trinh, chi ghi vao degraded.
3. Cac the chua xac dinh (unresolved) va cac truong stale/never_seen duoc ghi nhan day du.
4. Khung hinh rong nem FrameReadError.
5. Toan bo test offline 100%, khong dung mock.patch ma tiem qua ham khoi tao.
"""

from __future__ import annotations

from typing import Any
import numpy as np
import pytest

from src.capture.regions import Region, ScreenRegions
from src.decision.augment_advisor import AugmentChoice
from src.decision.reroll_policy import RerollState
from src.game_state.models import GameState
from src.game_state.state_tracker import GameStateTracker
from src.vision.augment_reader import AugmentReader, AugmentReading, CardRead
from src.vision.frame_reader import FrameReader, FrameReadError, FrameReading
from src.vision.hud_reader import FieldRead, HudReader, HudReading
from src.vision.reroll_buttons import ButtonRead, RerollButtonReader, RerollButtonReading

cv2 = pytest.importorskip("cv2")


def _make_dummy_frame() -> np.ndarray:
    return np.zeros((1080, 1920, 3), dtype=np.uint8)


def _make_dummy_regions() -> ScreenRegions:
    screens = {
        "hud": {
            "stage": Region.from_pixels(768, 5, 815, 34, 1920, 1080),
            "gold": Region.from_pixels(1022, 882, 1058, 910, 1920, 1080),
            "level": Region.from_pixels(348, 882, 415, 914, 1920, 1080),
            "xp": Region.from_pixels(455, 882, 520, 914, 1920, 1080),
            "hp": Region.from_pixels(1810, 265, 1860, 305, 1920, 1080),
            "traits": Region.from_pixels(0, 258, 238, 792, 1920, 1080),
        },
        "augment_select": {
            "reroll_0": Region.from_pixels(500, 834, 600, 886, 1920, 1080),
            "reroll_1": Region.from_pixels(910, 834, 1010, 886, 1920, 1080),
            "reroll_2": Region.from_pixels(1320, 834, 1420, 886, 1920, 1080),
            "card_text_0": Region.from_pixels(410, 515, 690, 700, 1920, 1080),
            "card_text_1": Region.from_pixels(820, 515, 1100, 700, 1920, 1080),
            "card_text_2": Region.from_pixels(1230, 515, 1510, 700, 1920, 1080),
            "cards": Region.from_pixels(410, 515, 1510, 700, 1920, 1080),
        },
    }
    return ScreenRegions(screens=screens, blockers={}, meta={})


class FakeHudReader:
    def __init__(self, reading: HudReading | None = None, raise_exc: Exception | None = None) -> None:
        self.reading = reading
        self.raise_exc = raise_exc

    def read(self, frame: np.ndarray) -> HudReading:
        if self.raise_exc:
            raise self.raise_exc
        if self.reading:
            return self.reading
        # Mac dinh: augment screen -> bar_visible=False, stage va hp co mat
        fields = (
            FieldRead("stage", "3-2", "3-2", True, "hợp lệ", 1.0),
            FieldRead("gold", None, "", False, "thanh HUD ẩn", 1.0),
            FieldRead("level", None, "", False, "thanh HUD ẩn", 1.0),
            FieldRead("xp", None, "", False, "thanh HUD ẩn", 1.0),
            FieldRead("hp", 85, "85", True, "hợp lệ", 1.0),
        )
        return HudReading(fields=fields, _bar_visible=False)


class FakeAugmentReader:
    def __init__(self, reading: AugmentReading | None = None, raise_exc: Exception | None = None) -> None:
        self.reading = reading
        self.raise_exc = raise_exc

    def read(self, frame: np.ndarray) -> AugmentReading:
        if self.raise_exc:
            raise self.raise_exc
        if self.reading:
            return self.reading
        cards = (
            CardRead(0, "Găng Đạo Tặc I", "Nhận 1 Găng", ("DA_BandOfThieves1",), 1.0, "Khớp chính xác"),
            CardRead(1, "Buffet Trang Bị", "Nhận trang bị", ("DA_ComponentBuffet",), 1.0, "Khớp chính xác"),
            CardRead(2, "Quái Thú Hư Không", "Tăng máu", ("DA_18_RiftbeastTraitAugment",), 1.0, "Khớp chính xác"),
        )
        return AugmentReading(cards=cards, traits={"TFT13_Bruiser": 2}, source="fake", latency_ms=10.0)


class FakeRerollReader:
    def __init__(self, reading: RerollButtonReading | None = None, raise_exc: Exception | None = None) -> None:
        self.reading = reading
        self.raise_exc = raise_exc

    def read(self, frame: np.ndarray) -> RerollButtonReading:
        if self.raise_exc:
            raise self.raise_exc
        if self.reading:
            return self.reading
        reads = (
            ButtonRead(0, "active", 0.95, 30.0, 42.0, "sang"),
            ButtonRead(1, "active", 0.95, 30.0, 42.0, "sang"),
            ButtonRead(2, "disabled", 0.95, -5.0, 32.0, "da dung"),
        )
        return RerollButtonReading(reads=reads)


def test_frame_reader_full_composition() -> None:
    """Kiem tra FrameReader doc day du va hop nhat ca 3 chan vao FrameReading."""
    frame = _make_dummy_frame()
    reader = FrameReader(
        hud_reader=FakeHudReader(),
        augment_reader=FakeAugmentReader(),
        reroll_reader=FakeRerollReader(),
        tracker=GameStateTracker(),
    )

    reading = reader.read(frame)
    assert isinstance(reading, FrameReading)

    # State doc tu HUD + Traits tu Augment
    assert reading.state.stage == "3-2"
    assert reading.state.hp == 85
    assert reading.state.active_traits == {"TFT13_Bruiser": 2}

    # Choices doc tu Augment
    assert len(reading.choices) == 3
    assert reading.choices[0].api_names == ["DA_BandOfThieves1"]
    assert reading.choices[1].api_names == ["DA_ComponentBuffet"]
    assert reading.choices[2].api_names == ["DA_18_RiftbeastTraitAugment"]

    # Rerolls doc tu Reroll buttons
    assert reading.rerolls is not None
    assert reading.rerolls.available == (True, True, False)

    # Degraded chua cac truong never_seen tu HUD bar bi an
    assert any("gold: never_seen" in d for d in reading.degraded)
    assert any("level: never_seen" in d for d in reading.degraded)
    assert any("xp: never_seen" in d for d in reading.degraded)

    # Latencies
    assert "hud" in reading.latency_ms
    assert "augment" in reading.latency_ms
    assert "rerolls" in reading.latency_ms


def test_frame_reader_one_failing_leg_degrades_only_itself() -> None:
    """Khi mot chan bi loi ngoai le, FrameReader khong crash ma ghi vao degraded."""
    frame = _make_dummy_frame()

    # 1. HUD reader fail
    reader_bad_hud = FrameReader(
        hud_reader=FakeHudReader(raise_exc=RuntimeError("Lỗi kết nối OCR")),
        augment_reader=FakeAugmentReader(),
        reroll_reader=FakeRerollReader(),
        tracker=GameStateTracker(),
    )
    reading_1 = reader_bad_hud.read(frame)
    assert any("hud: Lỗi kết nối OCR" in d for d in reading_1.degraded)
    assert len(reading_1.choices) == 3
    assert reading_1.rerolls is not None

    # 2. Augment reader fail
    reader_bad_aug = FrameReader(
        hud_reader=FakeHudReader(),
        augment_reader=FakeAugmentReader(raise_exc=RuntimeError("Timeout Gemini")),
        reroll_reader=FakeRerollReader(),
        tracker=GameStateTracker(),
    )
    reading_2 = reader_bad_aug.read(frame)
    assert any("augment: Timeout Gemini" in d for d in reading_2.degraded)
    assert reading_2.choices == []
    assert reading_2.state.stage == "3-2"
    assert reading_2.rerolls is not None

    # 3. Reroll reader fail
    reader_bad_reroll = FrameReader(
        hud_reader=FakeHudReader(),
        augment_reader=FakeAugmentReader(),
        reroll_reader=FakeRerollReader(raise_exc=RuntimeError("Mẫu nút bị hỏng")),
        tracker=GameStateTracker(),
    )
    reading_3 = reader_bad_reroll.read(frame)
    assert any("rerolls: Mẫu nút bị hỏng" in d for d in reading_3.degraded)
    assert reading_3.rerolls is None
    assert len(reading_3.choices) == 3
    assert reading_3.state.stage == "3-2"


def test_frame_reader_unresolved_augment_card_records_in_degraded() -> None:
    """The augment khong nhan dien duoc apiName phai duoc ghi vao degraded."""
    frame = _make_dummy_frame()
    cards = (
        CardRead(0, "Lõi Hợp Lệ", "", ("DA_ValidAugment",), 1.0, "Khớp"),
        CardRead(1, "Lõi Lạ Không Biết", "", (), 0.0, "Không khớp danh mục"),
        CardRead(2, "Lõi Khác", "", ("DA_Another",), 1.0, "Khớp"),
    )
    reading_aug = AugmentReading(cards=cards, traits={}, source="fake", latency_ms=1.0)
    reader = FrameReader(
        hud_reader=FakeHudReader(),
        augment_reader=FakeAugmentReader(reading=reading_aug),
        reroll_reader=FakeRerollReader(),
    )

    reading = reader.read(frame)
    # The o slot 1 bi unresolved nen chi co 2 choices hop le
    assert len(reading.choices) == 2
    assert reading.choices[0].api_names == ["DA_ValidAugment"]
    assert reading.choices[1].api_names == ["DA_Another"]
    assert any("ô 2: Không khớp danh mục" in d for d in reading.degraded)


def test_frame_reader_stale_tracker_values() -> None:
    """Khi tracker da duoc prime truoc do, cac truong vang mat duoc carry-forward va danh dau stale."""
    frame = _make_dummy_frame()
    tracker = GameStateTracker()

    # Prime tracker voi khung co thanh HUD hop le
    prime_fields = (
        FieldRead("stage", "3-1", "3-1", True, "hợp lệ", 1.0),
        FieldRead("gold", 45, "45", True, "hợp lệ", 1.0),
        FieldRead("level", 6, "6", True, "hợp lệ", 1.0),
        FieldRead("xp", 12, "12", True, "hợp lệ", 1.0),
        FieldRead("hp", 90, "90", True, "hợp lệ", 1.0),
    )
    tracker.update(HudReading(fields=prime_fields, _bar_visible=True))

    reader = FrameReader(
        hud_reader=FakeHudReader(),  # FakeHudReader tra ve bar_visible=False
        augment_reader=FakeAugmentReader(),
        reroll_reader=FakeRerollReader(),
    )

    reading = reader.read(frame, tracker=tracker)
    # Vang, cap, xp duoc carry forward
    assert reading.state.gold == 45
    assert reading.state.level == 6
    assert reading.state.xp == 12
    # Cac truong bi an duoc danh dau stale
    assert any("gold: stale" in d for d in reading.degraded)
    assert any("level: stale" in d for d in reading.degraded)
    assert any("xp: stale" in d for d in reading.degraded)
    # Khong con never_seen cho cac truong da thay
    assert not any("gold: never_seen" in d for d in reading.degraded)


def test_frame_reader_empty_frame_raises() -> None:
    """Khung hinh rong phai nem FrameReadError ngay lap tuc."""
    reader = FrameReader(
        hud_reader=FakeHudReader(),
        augment_reader=FakeAugmentReader(),
        reroll_reader=FakeRerollReader(),
    )
    with pytest.raises(FrameReadError, match="rỗng"):
        reader.read(np.zeros((0, 0, 3), dtype=np.uint8))


def test_frame_reading_to_dict() -> None:
    """Kiem tra cau truc xuat ra JSON cua FrameReading."""
    state = GameState(gold=10, level=5, hp=80, stage="2-1", active_traits={"TFT13_Bruiser": 2})
    choices = [AugmentChoice(api_names=["DA_Test"], confidence=0.9, display_name="Lõi Test")]
    rerolls = RerollState((True, False, True))
    reading = FrameReading(
        state=state,
        choices=choices,
        rerolls=rerolls,
        degraded=["gold: never_seen"],
        latency_ms={"hud": 12.345, "augment": 456.789},
    )

    d = reading.to_dict()
    assert d["state"]["gold"] == 10
    assert d["choices"][0]["api_names"] == ["DA_Test"]
    assert d["rerolls"]["available"] == [True, False, True]
    assert d["degraded"] == ["gold: never_seen"]
    assert d["latency_ms"]["hud"] == 12.35
    assert d["latency_ms"]["augment"] == 456.79


def test_frame_labels_schema_invariants() -> None:
    """Kiem tra cac bat bien ve schema va kieu du lieu cua data/eval/frame_labels.json."""
    import json
    from pathlib import Path
    from src.game_state.models import RE_STAGE

    labels_file = Path("data/eval/frame_labels.json")
    assert labels_file.is_file(), "File data/eval/frame_labels.json phai ton tai"

    raw = json.loads(labels_file.read_text(encoding="utf-8"))
    assert "_meta" in raw, "Thieu khoi _meta"
    meta = raw["_meta"]
    assert "what" in meta
    assert "how" in meta
    assert "entities" in meta
    assert "sampling" in meta
    assert "labeled_by" in meta
    assert "frames" in meta

    declared_entities = set(meta["entities"])
    frame_entries = {k: v for k, v in raw.items() if not k.startswith("_")}
    assert len(frame_entries) == meta["frames"], "So luong frame thuc te khong khop voi _meta.frames"

    for path_key, fields in frame_entries.items():
        assert path_key.startswith("data/frames/"), f"{path_key} phai bat dau bang data/frames/"
        assert path_key.endswith(".png"), f"{path_key} phai ket thuc bang .png"

        # Kiem tra cac truong phai thuoc entities khai bao
        assert set(fields.keys()) <= declared_entities, f"{path_key} co truong khong nam trong _meta.entities"

        # Kiem tra validation bounds
        if fields.get("stage") is not None:
            assert isinstance(fields["stage"], str)
            assert RE_STAGE.match(fields["stage"]), f"{path_key}: stage khong hop le {fields['stage']}"

        if fields.get("hp") is not None:
            assert isinstance(fields["hp"], int)
            assert 0 <= fields["hp"] <= 100, f"{path_key}: hp ngoai khoang 0-100: {fields['hp']}"

        if fields.get("gold") is not None:
            assert isinstance(fields["gold"], int)
            assert 0 <= fields["gold"] <= 999, f"{path_key}: gold ngoai khoang 0-999"

        if fields.get("level") is not None:
            assert isinstance(fields["level"], int)
            assert 1 <= fields["level"] <= 10, f"{path_key}: level ngoai khoang 1-10"

        if fields.get("xp") is not None:
            assert isinstance(fields["xp"], int)
            assert 0 <= fields["xp"] <= 99, f"{path_key}: xp ngoai khoang 0-99"

        if fields.get("augment") is not None:
            assert isinstance(fields["augment"], list)
            assert len(fields["augment"]) == 3, f"{path_key}: augment phai co dung 3 phan tu"
            assert all(isinstance(c, str) for c in fields["augment"])

        if fields.get("traits") is not None:
            assert isinstance(fields["traits"], dict)
            assert all(isinstance(k, str) and isinstance(v, int) for k, v in fields["traits"].items())


def test_frame_reader_wires_settings_timeout(tmp_path: Path) -> None:
    """Kiem tra FrameReader.load() nap dung timeout tu Settings neu khong truyen tham so."""
    import yaml
    from src.utils.settings import Settings

    cfg_file = tmp_path / "settings.yaml"
    custom_cfg = {
        "vision": {
            "gemini_timeout_s": 0.5,
            "gemini_model": "gemini-custom",
            "vote_window": 3,
            "enable_gemini_vision": False,
        }
    }
    cfg_file.write_text(yaml.safe_dump(custom_cfg), encoding="utf-8")

    settings = Settings.load(cfg_file)
    regions = _make_dummy_regions()
    reader = FrameReader.load(regions, settings=settings)

    assert reader.augment_reader.timeout_s == 0.5
    assert reader.augment_reader.model == "gemini-custom"
    assert reader.augment_reader.enable_gemini_vision is False
    assert reader.tracker.window == 3

