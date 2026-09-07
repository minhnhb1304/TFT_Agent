"""Test cong kiem VOD (scripts/qualify_vod.py).

Cong nay quyet dinh co bo ~15 phut may + ~1 gio cong nguoi vao mot VOD hay
khong. Mot tieu chi bao DAT sai cach thi ta gan nhan tren du lieu khong dung
duoc; mot tieu chi bao HONG sai cach thi ta vut di mot VOD tot. Ca hai deu dat.

Khong test nao o day cham vao file video that: `VideoFrameSource` duoc thay
bang mot doi tuong gia, va `cropdetect` duoc tiem vao. Nho vay bo test chay
duoc tren may khong co ffmpeg.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _load():
    """Nap script nhu mot module - scripts/ khong phai package.

    Phai dang ky vao `sys.modules` TRUOC `exec_module`: `@dataclass` tra cuu
    `sys.modules[cls.__module__]` khi xu ly lop, va se nem AttributeError neu
    module chua co o do.
    """
    spec = importlib.util.spec_from_file_location(
        "qualify_vod", ROOT / "scripts" / "qualify_vod.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


qv = _load()


class FakeSource:
    """Du de `report_dict` va `hud_checks` chay ma khong can file video."""

    def __init__(self, width=1920, height=1080, fps=60.0, bit_rate=3_740_612,
                 duration=18224.5, video_id="test123", bit_rate_source="stream"):
        self._w, self._h = width, height
        self.duration = duration
        self.video_id = video_id
        self.path = Path("khong-ton-tai.mp4")
        self.meta = {"width": width, "height": height, "fps": fps,
                     "bit_rate": bit_rate, "bit_rate_source": bit_rate_source,
                     "duration": duration, "codec": "h264", "profile": "Main"}

    @property
    def size(self):
        return self._w, self._h

    def grab(self, at=None):
        return None


# --- tieu chi tu container -------------------------------------------------


def test_the_reference_vod_passes_the_container_checks() -> None:
    """vQDqc9eiDpk: 1080p60 @ 3,74 Mbps. Chi truot moi muc 60fps."""
    checks = qv.container_checks(1920, 1080, 60.0, 3_740_612, 18224.5, "stream")
    by = {c.name: c for c in checks}
    assert by["do phan giai"].ok
    assert by["bit tren pixel"].ok            # 0,0301 bpp > san 0,025
    assert by["thoi luong"].ok
    assert not by["nhip khung"].ok            # 60fps: dung duoc nhung khong nen


def test_thirty_fps_is_preferred_over_sixty() -> None:
    assert qv.container_checks(1920, 1080, 30.0, 3_740_612, 7200, "s")[1].ok
    assert not qv.container_checks(1920, 1080, 60.0, 3_740_612, 7200, "s")[1].ok


def test_higher_resolution_is_accepted_because_rois_are_normalised() -> None:
    """1440p van 16:9 - ROI luu dang ti le nen dung duoc, khong duoc loai."""
    assert qv.container_checks(2560, 1440, 30.0, 8_000_000, 7200)[0].ok


def test_below_1080p_is_rejected() -> None:
    assert not qv.container_checks(1280, 720, 30.0, 3_000_000, 7200)[0].ok


def test_non_16_9_aspect_is_rejected() -> None:
    """Man sieu rong / co vien -> toa do ti le khong con anh xa dung."""
    assert not qv.container_checks(2560, 1080, 30.0, 8_000_000, 7200)[0].ok   # 21:9
    assert not qv.container_checks(1440, 1080, 30.0, 8_000_000, 7200)[0].ok   # 4:3


def test_missing_bitrate_fails_instead_of_reading_as_zero() -> None:
    """WebM/VP9 KHONG khai bao bit_rate o muc stream.

    Neu coi 0 la mot gia tri hop le thi moi ban tai VP9 - dinh dang duoc
    khuyen dung - deu bi danh truot voi ly do sai.
    """
    checks = {c.name: c for c in qv.container_checks(1920, 1080, 30.0, 0, 7200)}
    assert not checks["bit tren pixel"].ok
    assert "khong suy ra duoc bitrate" in checks["bit tren pixel"].detail


def test_zero_fps_does_not_divide_by_zero() -> None:
    checks = {c.name: c for c in qv.container_checks(1920, 1080, 0.0, 3_000_000, 7200)}
    assert not checks["nhip khung"].ok
    assert not checks["bit tren pixel"].ok


def test_zero_height_does_not_divide_by_zero() -> None:
    checks = qv.container_checks(1920, 0, 30.0, 3_000_000, 7200)
    assert not checks[0].ok


def test_short_video_is_rejected() -> None:
    assert not qv.container_checks(1920, 1080, 30.0, 4_000_000, 600)[3].ok


def test_bitrate_source_is_surfaced_not_hidden() -> None:
    detail = qv.container_checks(1920, 1080, 30.0, 3_000_000, 7200, "size/duration")[2].detail
    assert "size/duration" in detail


# --- vien den: hoi quy cho loi 'DAT vo can cu' -----------------------------


def test_letterbox_fails_when_ffmpeg_cannot_run() -> None:
    """HOI QUY: ban cu dung `all(c == want for c in crops if c)`.

    Khi ffmpeg vang mat, moi phan tu la None -> `all([])` -> **True** -> muc
    nay bao DAT tren mot may khong the do duoc gi. Khong do duoc phai la HONG.
    """
    check = qv.letterbox_check("x.mp4", 100.0, 1920, 1080, detector=lambda p, t: None)
    assert not check.ok
    assert "ffmpeg" in check.detail


def test_letterbox_passes_on_a_full_frame_video() -> None:
    check = qv.letterbox_check("x.mp4", 100.0, 1920, 1080,
                               detector=lambda p, t: "crop=1920:1080:0:0")
    assert check.ok


def test_letterbox_detects_pillarboxing() -> None:
    check = qv.letterbox_check("x.mp4", 100.0, 1920, 1080,
                               detector=lambda p, t: "crop=1440:1080:240:0")
    assert not check.ok


def test_letterbox_fails_when_only_some_probes_worked() -> None:
    """Do duoc 2/3 moc thi chua du de ket luan - dung doan not cai con lai."""
    seen = iter(["crop=1920:1080:0:0", None, "crop=1920:1080:0:0"])
    check = qv.letterbox_check("x.mp4", 100.0, 1920, 1080,
                               detector=lambda p, t: next(seen))
    assert not check.ok
    assert "khong do duoc" in check.detail


def test_letterbox_fails_on_zero_duration() -> None:
    assert not qv.letterbox_check("x.mp4", 0.0, 1920, 1080,
                                  detector=lambda p, t: "crop=1920:1080:0:0").ok


def test_cropdetect_returns_none_when_ffmpeg_is_absent() -> None:
    """Khong duoc nem FileNotFoundError len tan main()."""
    assert qv._cropdetect("x.mp4", 1.0, ffmpeg="ffmpeg-khong-co-that-9z") is None


# --- chon khoang lay mau ---------------------------------------------------


def test_spans_come_from_games_when_a_timeline_exists() -> None:
    spans, scope = qv.sample_spans(3000.0, [(100.0, 1000.0), (1500.0, 2500.0)])
    assert spans == [(160.0, 940.0), (1560.0, 2440.0)]
    assert "2 van" in scope


def test_a_game_shorter_than_the_padding_is_kept_whole() -> None:
    """Neu tru dem lam lo > hi thi `uniform` lang le lay mau NGUOC lai."""
    spans, _ = qv.sample_spans(3000.0, [(100.0, 150.0)])
    assert spans == [(100.0, 150.0)]
    assert all(lo < hi for lo, hi in spans)


def test_falls_back_to_the_whole_video_without_a_timeline() -> None:
    spans, scope = qv.sample_spans(1000.0, [])
    assert spans == [(100.0, 900.0)]
    assert "chua co timeline" in scope


def test_zero_duration_yields_no_spans_rather_than_a_bad_range() -> None:
    spans, scope = qv.sample_spans(0.0, [])
    assert spans == []
    assert "khong co khoang" in scope


def test_degenerate_game_intervals_are_dropped() -> None:
    spans, _ = qv.sample_spans(500.0, [(100.0, 100.0)])
    assert all(lo < hi for lo, hi in spans)


# --- doc timeline ----------------------------------------------------------


def test_missing_timeline_is_not_an_error(tmp_path) -> None:
    assert qv.load_games(tmp_path / "khong-co.json") == []


def test_corrupt_timeline_is_not_an_error(tmp_path) -> None:
    """File JSON dut giua chung khong duoc phep chan ca duong chay."""
    p = tmp_path / "timeline.json"
    p.write_text('{"events": [{"type": "game", ', encoding="utf-8")
    assert qv.load_games(p) == []


def test_timeline_rows_with_bad_fields_are_skipped_not_fatal(tmp_path) -> None:
    p = tmp_path / "timeline.json"
    p.write_text(json.dumps({"events": [
        {"type": "game", "t_start": 1.0, "t_end": 2.0},
        {"type": "game", "t_start": "hong"},
        {"type": "augment_select", "t_start": 5.0, "t_end": 6.0},
        "khong-phai-dict",
    ]}), encoding="utf-8")
    assert qv.load_games(p) == [(1.0, 2.0)]


def test_timeline_that_is_a_list_not_a_dict(tmp_path) -> None:
    p = tmp_path / "timeline.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    assert qv.load_games(p) == []


# --- HUD checks ------------------------------------------------------------


def test_hud_check_is_skipped_with_a_clear_reason_when_uncalibrated(tmp_path) -> None:
    checks = qv.hud_checks(FakeSource(), tmp_path / "khong-co.yaml", 4)
    assert len(checks) == 1 and not checks[0].ok
    assert "calibrate" in checks[0].detail


def test_hud_check_reports_bad_region_file_instead_of_crashing(tmp_path) -> None:
    p = tmp_path / "screen_regions.yaml"
    p.write_text("screens:\n  hud:\n    gold: {x: 0.5}\n", encoding="utf-8")
    checks = qv.hud_checks(FakeSource(), p, 4)
    assert len(checks) == 1 and not checks[0].ok
    assert "ROI" in checks[0].detail


# --- CLI -------------------------------------------------------------------


def test_missing_video_argument_exits() -> None:
    with pytest.raises(SystemExit):
        qv.main([])


def test_zero_samples_is_rejected() -> None:
    with pytest.raises(SystemExit):
        qv.main(["--video", "x.mp4", "--samples", "0"])


def test_unreadable_video_returns_code_2_not_a_traceback(capsys) -> None:
    """Ma tra 2 = khong cham duoc; 1 = cham duoc nhung truot. Khac nhau."""
    assert qv.main(["--video", str(ROOT / "khong-ton-tai-dau.mp4")]) == 2
    assert "loi doc video" in capsys.readouterr().err


def test_report_dict_is_json_serialisable() -> None:
    checks = qv.container_checks(1920, 1080, 60.0, 3_740_612, 18224.5, "stream")
    payload = qv.report_dict(FakeSource(), checks)
    text = json.dumps(payload, ensure_ascii=False)
    assert '"video_id": "test123"' in text
    assert payload["total"] == len(checks)
    assert payload["passed"] == sum(1 for c in checks if c.ok)
    assert payload["bpp"] == pytest.approx(0.0301, abs=1e-4)


def test_report_dict_leaves_bpp_null_when_unknowable() -> None:
    payload = qv.report_dict(FakeSource(bit_rate=0), [])
    assert payload["bpp"] is None
    json.dumps(payload)                     # van tuan tu hoa duoc


def test_check_to_dict_uses_the_documented_keys() -> None:
    assert qv.Check("x", True, "y").to_dict() == {"ten": "x", "dat": True, "chi_tiet": "y"}
