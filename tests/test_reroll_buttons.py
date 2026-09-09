"""Test bo doc ba nut doi the (src/vision/reroll_buttons.py).

KHUNG HINH O DAY LA VE RA, KHONG PHAI FRAME THAT

`data/frames/` khong nam trong repo (.gitignore) va mot VOD 5 gio thi khong
the la phu thuoc cua bo test. Nen o day ta VE lai cai nut: nen phang, vien
day 3px, glyph dan vao dung o `GLYPH_BOX`. Cach do kiem duoc TOAN BO logic
phan loai - nguong, thu tu uu tien giua ba nhanh, doi kich thuoc, quy ve
`RerollState` - ma khong cham file nao.

Cai no KHONG kiem duoc la cac NGUONG co dung voi pixel that khong. Do la
viec cua `scripts/read_reroll_buttons.py --labels`, chay tren khung that va
doi chieu voi nhan tay; ket qua ghi o `docs/vision/reroll-buttons.md`. Hai
thu do bo tuc nhau chu khong thay nhau.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from src.capture.regions import Region, ScreenRegions
from src.decision.reroll_policy import RerollState
from src.vision.reroll_buttons import (
    BUTTON_SIZE,
    GLYPH_BOX,
    SLOT_NAMES,
    ButtonRead,
    ButtonReadError,
    ButtonThresholds,
    RerollButtonReader,
    RerollButtonReading,
    normalize_gray,
)

cv2 = pytest.importorskip("cv2")

ROOT = Path(__file__).resolve().parent.parent

# Mau do duoc tren khung that (xem docstring cua module dang test), lam tron
# ve so nguyen: (B, G, R). `warm` = R - B, `fill_value` = do sang trung binh.
ACTIVE_FILL = (25, 45, 70)      # nau vang  -> warm +45, fill ~47
DISABLED_FILL = (40, 32, 35)    # xanh than -> warm  -5, fill ~36
PRESSED_FILL = (11, 8, 6)       # gan den   -> warm  -5, fill ~ 8
GOLD_BORDER = (60, 140, 190)
GRAY_BORDER = (110, 110, 110)


def _glyph() -> np.ndarray:
    """Mot glyph gia: mui ten vong tron ho mot doan, day net 4px.

    Khong nap `data/templates/reroll_glyph.png` o day. Mau that duoc kiem
    rieng o `test_shipped_template_matches_the_glyph_box`; con logic phan
    loai thi phai dung duoc voi BAT KY glyph nao, ke ca glyph cua Set sau.
    """
    top, left, height, width = GLYPH_BOX
    canvas = np.zeros((height, width), np.uint8)
    cv2.ellipse(canvas, (width // 2, height // 2), (width // 3, height // 3),
                0, 300, 620, 255, 4)
    cv2.line(canvas, (width // 2 + 6, 4), (width // 2 + 14, 10), 255, 4)
    return canvas


GLYPH = _glyph()


def _button(fill: tuple[int, int, int], border: tuple[int, int, int],
            glyph_level: int = 200, glyph: np.ndarray | None = None) -> np.ndarray:
    """Ve mot o nut 100x52: vien 3px, nen phang, glyph dan vao GLYPH_BOX."""
    w, h = BUTTON_SIZE
    box = np.zeros((h, w, 3), np.uint8)
    box[:, :] = border
    box[3:-3, 3:-3] = fill
    top, left, gh, gw = GLYPH_BOX
    art = GLYPH if glyph is None else glyph
    mask = art > 127
    patch = box[top:top + gh, left:left + gw]
    # Net glyph la vang nhat: B thap hon R. Giu dung tuong quan do vi `warm`
    # tinh tren CA long nut, ke ca net glyph.
    patch[mask] = (glyph_level // 3, glyph_level * 4 // 5, glyph_level)
    return box


def _terrain(seed: int = 7) -> np.ndarray:
    """Mot manh dia hinh: nhieu co cau truc, khong co glyph nao."""
    rng = np.random.default_rng(seed)
    w, h = BUTTON_SIZE
    noise = rng.integers(40, 190, size=(h, w, 3), dtype=np.uint8)
    return cv2.GaussianBlur(noise, (7, 7), 0)


def _reader(thresholds: ButtonThresholds | None = None,
            regions: ScreenRegions | None = None) -> RerollButtonReader:
    return RerollButtonReader(regions or _regions(), normalize_gray(GLYPH), thresholds)


def _regions() -> ScreenRegions:
    """ROI that cua Set 18, quy ve ti le tren khung 1920x1080."""
    boxes = {
        "reroll_0": (500, 834, 600, 886),
        "reroll_1": (910, 834, 1010, 886),
        "reroll_2": (1320, 834, 1420, 886),
    }
    return ScreenRegions(
        screens={"augment_select": {
            name: Region.from_pixels(*px, 1920, 1080) for name, px in boxes.items()
        }},
        blockers={},
        meta={"reference_size": [1920, 1080]},
    )


def _frame(states: tuple[str, str, str], width: int = 1920, height: int = 1080) -> np.ndarray:
    """Mot khung day du, dan ba cai nut vao dung ba ROI."""
    art = {
        "active": _button(ACTIVE_FILL, GOLD_BORDER),
        "disabled": _button(DISABLED_FILL, GRAY_BORDER, glyph_level=120),
        "pressed": _button(PRESSED_FILL, GOLD_BORDER, glyph_level=150),
        "terrain": _terrain(),
    }
    regions = _regions()
    frame = np.full((height, width, 3), 30, np.uint8)
    for slot, state in enumerate(states):
        left, top, right, bottom = regions.region(
            "augment_select", SLOT_NAMES[slot]).to_pixels(width, height)
        frame[top:bottom, left:right] = cv2.resize(
            art[state], (right - left, bottom - top), interpolation=cv2.INTER_NEAREST)
    return frame


# --- ba trang thai on dinh -------------------------------------------------


def test_gold_button_reads_as_active() -> None:
    read = _reader().read_button(_button(ACTIVE_FILL, GOLD_BORDER))
    assert read.state == "active"
    assert read.settled
    assert read.warm > 0


def test_navy_button_reads_as_disabled() -> None:
    read = _reader().read_button(_button(DISABLED_FILL, GRAY_BORDER, glyph_level=120))
    assert read.state == "disabled"
    assert read.settled


def test_near_black_button_is_pressed_not_disabled() -> None:
    """Do o duoc phan biet bang DO TOI cua nen, khong bang mau.

    Khung nhay luc bam chuot co nen gan den, nen `warm` cua no am y het nut
    da dung. Doc bang mau khong thoi se goi no la 'da dung' va tu tay xoa
    mot luot roll ma nguoi choi van con - chinh sach tuan tu se dung som mot
    cach vo co. Do la ly do nhanh nay dung TRUOC nhanh mau.
    """
    box = _button(PRESSED_FILL, GOLD_BORDER, glyph_level=150)
    read = _reader().read_button(box)
    assert read.state == "pressed"
    assert not read.settled
    assert read.fill_value < ButtonThresholds().pressed_fill_value


def test_terrain_without_a_glyph_is_unknown() -> None:
    read = _reader().read_button(_terrain())
    assert read.state == "unknown"
    assert read.glyph_match < ButtonThresholds().min_glyph_match


def test_every_read_carries_the_numbers_it_decided_on() -> None:
    read = _reader().read_button(_button(ACTIVE_FILL, GOLD_BORDER), slot=2)
    assert read.slot == 2
    assert "3" in read.reason, "ly do phai danh so o theo cach nguoi dem: 1..3"
    d = read.to_dict()
    assert set(d) == {"slot", "state", "glyph_match", "warm", "fill_value", "reason"}


# --- nguong dieu chinh duoc ------------------------------------------------


def test_thresholds_are_injectable() -> None:
    """Ca ba nguong deu la tham so, khong phai hang so dan trong nhanh if.

    Doi do phan giai / doi giao dien thi phai do lai chung; do lai duoc chi
    khi thay duoc bang mot doi tuong truyen vao.
    """
    box = _button(ACTIVE_FILL, GOLD_BORDER)
    strict = ButtonThresholds(min_glyph_match=1.01)  # TM_CCOEFF_NORMED toi da 1.0
    assert _reader(strict).read_button(box).state == "unknown"
    loose = ButtonThresholds(active_warm=999.0)
    assert _reader(loose).read_button(box).state == "disabled"
    # Ha nguong nhan dang xuong 0 thi ca dia hinh cung duoc doc nhu mot nut.
    blind = ButtonThresholds(min_glyph_match=0.0)
    assert _reader(blind).read_button(_terrain()).state != "unknown"


def test_pressed_branch_runs_before_the_colour_branch() -> None:
    """Tat nhanh 'vua bam' thi nut gan den roi thang vao 'da dung'."""
    box = _button(PRESSED_FILL, GOLD_BORDER, glyph_level=150)
    off = ButtonThresholds(pressed_fill_value=0.0)
    assert _reader(off).read_button(box).state == "disabled"


# --- doc ca khung hinh -----------------------------------------------------


def test_reads_three_slots_from_a_full_frame() -> None:
    reading = _reader().read(_frame(("active", "disabled", "active")))
    assert [r.state for r in reading.reads] == ["active", "disabled", "active"]
    assert reading.available == (True, False, True)
    assert reading.screen_present and reading.settled


def test_frame_without_the_augment_screen_is_not_present() -> None:
    reading = _reader().read(_frame(("terrain", "terrain", "terrain")))
    assert not reading.screen_present
    assert not reading.settled
    assert reading.available == (None, None, None)


def test_roi_is_resolution_independent() -> None:
    """Toa do luu dang ti le, nen 2560x1440 phai ra cung ket qua."""
    states = ("active", "disabled", "active")
    big = _reader().read(_frame(states, width=2560, height=1440))
    assert [r.state for r in big.reads] == ["active", "disabled", "active"]


def test_odd_sized_crop_is_resized_before_measuring() -> None:
    box = cv2.resize(_button(ACTIVE_FILL, GOLD_BORDER), (61, 33),
                     interpolation=cv2.INTER_AREA)
    assert _reader().read_button(box).state == "active"


# --- quy ve RerollState ----------------------------------------------------


def _reading(*states: str) -> RerollButtonReading:
    return RerollButtonReading(tuple(
        ButtonRead(i, s, 1.0, 0.0, 0.0, "test") for i, s in enumerate(states)
    ))


def test_settled_reading_becomes_a_reroll_state() -> None:
    state = _reading("active", "disabled", "active").to_reroll_state()
    assert isinstance(state, RerollState)
    assert state.available == (True, False, True)
    assert state.n_available == 2


def test_undecided_slot_without_fallback_raises() -> None:
    """Doan bua mot bit o day khong tu bao la loi o bat ky cho nao ve sau."""
    with pytest.raises(ButtonReadError, match="du phong"):
        _reading("active", "pressed", "active").to_reroll_state()
    with pytest.raises(ButtonReadError):
        _reading("unknown", "unknown", "unknown").to_reroll_state()


def test_undecided_slot_takes_the_last_stable_value() -> None:
    prev = RerollState((True, True, False), burned=("DA_X",))
    state = _reading("active", "pressed", "unknown").to_reroll_state(fallback=prev)
    assert state.available == (True, True, False)
    assert state.burned == ("DA_X",), "burned di theo van dau, khong theo khung hinh"


def test_settled_slots_win_over_the_fallback() -> None:
    prev = RerollState((True, True, True))
    state = _reading("disabled", "disabled", "pressed").to_reroll_state(fallback=prev)
    assert state.available == (False, False, True)


def test_reading_serialises_flat() -> None:
    d = _reading("active", "pressed", "disabled").to_dict()
    assert d["available"] == [True, None, False]
    assert d["settled"] is False and d["screen_present"] is True
    assert [s["state"] for s in d["slots"]] == ["active", "pressed", "disabled"]


# --- hong thi phai no ra ---------------------------------------------------


def test_empty_frame_raises() -> None:
    with pytest.raises(ButtonReadError):
        _reader().read(np.zeros((0, 0, 3), np.uint8))


def test_grayscale_crop_raises_instead_of_guessing() -> None:
    with pytest.raises(ButtonReadError, match="BGR"):
        _reader().read_button(np.zeros(BUTTON_SIZE[::-1], np.uint8))


def test_template_must_be_a_gray_image() -> None:
    with pytest.raises(ButtonReadError, match="2 chieu"):
        RerollButtonReader(_regions(), np.zeros((10, 10, 3), np.uint8))
    with pytest.raises(ButtonReadError, match="rong"):
        RerollButtonReader(_regions(), np.zeros((0, 0), np.uint8))


def test_regions_missing_the_screen_raise_at_construction() -> None:
    """Thieu ROI phai no luc dung reader, khong phai luc doc khung dau tien."""
    empty = ScreenRegions(screens={"hud": {}}, blockers={}, meta={})
    with pytest.raises(Exception, match="augment_select"):
        RerollButtonReader(empty, normalize_gray(GLYPH))


def test_missing_template_file_says_how_to_make_one(tmp_path: Path) -> None:
    with pytest.raises(ButtonReadError, match="build_reroll_template"):
        RerollButtonReader.load(_regions(), tmp_path / "khong-co.png")


# --- tai san di kem repo ---------------------------------------------------


def test_shipped_template_matches_the_glyph_box() -> None:
    """Mau glyph la file SINH RA nhung DUOC commit - no la mot phan cua code.

    Xoa no thi bo phan loai chet luc chay chu khong luc test, nen cho nay
    kiem su ton tai VA kich thuoc: mau lech kich thuoc voi `GLYPH_BOX` la
    dau hieu ai do doi mot trong hai ma quen cai kia.
    """
    p = ROOT / "data" / "templates" / "reroll_glyph.png"
    assert p.is_file(), "chay scripts/build_reroll_template.py de sinh lai"
    img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
    _, _, height, width = GLYPH_BOX
    assert img is not None and img.shape == (height, width)
    assert (ROOT / "data" / "templates" / "reroll_glyph.json").is_file(), "thieu xuat xu"


@pytest.mark.parametrize("name", [
    "screen_regions.s7h-jHMpFmQ.yaml",
    "screen_regions.5tshRxYLwv8.yaml",
])
def test_tracked_region_files_carry_the_three_buttons(name: str) -> None:
    """Hieu chuan lai cho mot streamer ma quen ba cai nut thi Nhiem vu 3 tat.

    Loi do im lang: `Advisor.advise()` van chay, chi la `rerolls` mai mai la
    "con du ba luot". Bat o day de no thanh mot test do.
    """
    regions = ScreenRegions.load(ROOT / "config" / name)
    for slot_name in SLOT_NAMES:
        box = regions.region("augment_select", slot_name)
        assert 0.7 < box.y < 0.8, f"{name}: {slot_name} khong o hang nut doi the"


def test_hand_labels_stay_in_the_declared_alphabet() -> None:
    """File nhan tay la ban do su that - go sai mot chu la do lech im lang."""
    raw = json.loads((ROOT / "data" / "eval" / "reroll_button_labels.json")
                     .read_text(encoding="utf-8"))
    allowed = set(raw["_meta"]["states"])
    frames = {k: v for k, v in raw.items() if not k.startswith("_")}
    assert len(frames) == raw["_meta"]["frames"]
    for key, states in frames.items():
        assert len(states) == 3, key
        assert set(states) <= allowed, key
    assert sum(len(v) for v in frames.values()) == raw["_meta"]["slots"]
