"""Test tang capture (SPEC 3.1) - nguon frame va vung quan tam.

Test video tu SINH mot file .mp4 nho bang ffmpeg thay vi phu thuoc vao VOD
5 gio nam ngoai repo: bo test phai chay duoc tren may khac, va phai chay
hoan toan offline. Khong co ffmpeg thi skip - khong fail, vi ffmpeg la phu
thuoc he thong chu khong phai goi pip.
"""

from __future__ import annotations

import shutil
import subprocess

import numpy as np
import pytest

from src.capture.frame_source import Frame, FrameSource, format_ref
from src.capture.regions import Region, RegionError, ScreenRegions, crop
from src.capture.video_source import (
    VideoFrameSource,
    VideoSourceError,
    _bit_rate_source,
    _parse_fps,
    _pick_bit_rate,
    _slug,
)

HAS_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
needs_ffmpeg = pytest.mark.skipif(not HAS_FFMPEG, reason="can ffmpeg tren PATH")


# --- Region ----------------------------------------------------------------


def test_pixels_round_trip_through_the_normalised_form() -> None:
    box = Region.from_pixels(768, 5, 815, 34, 1920, 1080)
    assert box.to_pixels(1920, 1080) == (768, 5, 815, 34)


def test_normalised_regions_scale_to_another_resolution() -> None:
    """Ly do luu ti le: cung mot file chay duoc o do phan giai khac."""
    box = Region.from_pixels(960, 540, 1920, 1080, 1920, 1080)
    assert box.to_pixels(3840, 2160) == (1920, 1080, 3840, 2160)


@pytest.mark.parametrize("bad", [
    {"x": -0.1, "y": 0.0, "w": 0.5, "h": 0.5},
    {"x": 0.0, "y": 0.0, "w": 0.0, "h": 0.5},
    {"x": 0.8, "y": 0.0, "w": 0.5, "h": 0.5},      # tran ra ngoai khung
])
def test_impossible_regions_are_rejected_loudly(bad: dict) -> None:
    """Fail fast: ROI sai ma im lang thi sinh ra so lieu sai ma khong ai biet."""
    with pytest.raises(RegionError):
        Region(**bad)


def test_regions_that_touch_edge_to_edge_do_not_intersect() -> None:
    left = Region(0.0, 0.0, 0.5, 1.0)
    right = Region(0.5, 0.0, 0.5, 1.0)
    assert not left.intersects(right)
    assert left.intersects(Region(0.49, 0.0, 0.5, 1.0))


def test_crop_returns_the_requested_pixels() -> None:
    image = np.arange(100 * 200 * 3, dtype=np.uint8).reshape(100, 200, 3)
    piece = crop(image, Region.from_pixels(10, 20, 30, 40, 200, 100))
    assert piece.shape == (20, 20, 3)
    assert np.array_equal(piece, image[20:40, 10:30])


# --- ScreenRegions ---------------------------------------------------------


def _regions() -> ScreenRegions:
    return ScreenRegions(
        screens={"hud": {
            "gold": Region.from_pixels(1022, 882, 1058, 910, 1920, 1080),
            "stage": Region.from_pixels(768, 5, 815, 34, 1920, 1080),
        }},
        blockers={"stream_chat": Region.from_pixels(0, 0, 890, 218, 1920, 1080)},
        meta={"set": "TFTSet18"},
    )


def test_yaml_round_trip_preserves_geometry(tmp_path) -> None:
    p = tmp_path / "screen_regions.yaml"
    p.write_text(_regions().to_yaml(), encoding="utf-8")
    loaded = ScreenRegions.load(p)
    assert loaded.region("hud", "gold").to_pixels(1920, 1080) == (1022, 882, 1058, 910)
    assert loaded.meta["set"] == "TFTSet18"


def test_missing_file_says_how_to_generate_it(tmp_path) -> None:
    """Loi phai chi duoc viec tiep theo, khong chi bao 'khong tim thay'."""
    with pytest.raises(RegionError, match="calibrate"):
        ScreenRegions.load(tmp_path / "khong-co.yaml")


def test_blocker_overlap_is_detected_not_ignored() -> None:
    """Do that tren VOD: khung chat cua stream dam vao o hien stage.

    Doc xuyen qua chu cua nguoi xem se ra so rac ma khong bao loi, nen va cham
    nay phai NOI ra chu khong duoc bo qua.
    """
    hits = _regions().check_blockers("hud")
    assert hits == {"stage": ["stream_chat"]}


def test_known_clashes_can_be_excluded_explicitly() -> None:
    assert _regions().check_blockers("hud", ignore=["stage"]) == {}


def test_unknown_region_name_is_an_error() -> None:
    with pytest.raises(RegionError, match="hud.khongco"):
        _regions().region("hud", "khongco")


# --- Frame / ref -----------------------------------------------------------


def test_ref_is_a_timestamp_a_human_can_paste_into_a_player() -> None:
    assert format_ref("vod:abc", 11000.0) == "vod:abc@03:03:20.000"
    assert format_ref("vod:abc", 0.0) == "vod:abc@00:00:00.000"
    assert format_ref("vod:abc", 1.5) == "vod:abc@00:00:01.500"


def test_frame_reports_size_in_screen_order_not_numpy_order() -> None:
    frame = Frame(image=np.zeros((1080, 1920, 3), np.uint8), t=0.0, ref="x")
    assert frame.size == (1920, 1080)


# --- VideoFrameSource ------------------------------------------------------


@pytest.fixture(scope="module")
def tiny_video(tmp_path_factory) -> str:
    """5 giay 320x180 @10fps, moi giay mot keyframe - giong GOP cua VOD that."""
    if not HAS_FFMPEG:
        pytest.skip("can ffmpeg tren PATH")
    out = tmp_path_factory.mktemp("video") / "tiny.mp4"
    subprocess.run([
        "ffmpeg", "-v", "error", "-y",
        "-f", "lavfi", "-i", "testsrc=size=320x180:rate=10:duration=5",
        "-c:v", "libx264", "-g", "10", "-pix_fmt", "yuv420p", str(out),
    ], check=True, capture_output=True)
    return str(out)


@needs_ffmpeg
def test_reads_size_and_duration(tiny_video: str) -> None:
    src = VideoFrameSource(tiny_video)
    assert src.size == (320, 180)
    assert src.duration == pytest.approx(5.0, abs=0.2)


@needs_ffmpeg
def test_grab_returns_a_bgr_frame_with_a_traceable_ref(tiny_video: str) -> None:
    frame = VideoFrameSource(tiny_video).grab(2.0)
    assert frame is not None
    assert frame.image.shape == (180, 320, 3)
    assert frame.image.dtype == np.uint8
    assert frame.ref.endswith("@00:00:02.000")


@needs_ffmpeg
def test_grabbing_different_moments_gives_different_pixels(tiny_video: str) -> None:
    src = VideoFrameSource(tiny_video)
    a, b = src.grab(0.5), src.grab(4.0)
    assert a is not None and b is not None
    assert not np.array_equal(a.image, b.image)


@needs_ffmpeg
def test_keyframe_scan_is_cached_to_disk(tiny_video: str, tmp_path) -> None:
    src = VideoFrameSource(tiny_video)
    cache = tmp_path / "keyframes.json"
    first = src.keyframe_times(cache=cache)
    assert cache.is_file()
    assert first and first[0] == pytest.approx(0.0)
    assert src.keyframe_times(cache=cache) == first


@needs_ffmpeg
def test_thumbnails_are_grayscale_and_time_stamped(tiny_video: str) -> None:
    thumbs, times = VideoFrameSource(tiny_video).thumbnails(width=32, height=18)
    assert thumbs.ndim == 3 and thumbs.shape[1:] == (18, 32)
    assert thumbs.dtype == np.uint8
    assert len(times) == len(thumbs)
    assert times[0] == pytest.approx(0.0)


@needs_ffmpeg
def test_video_source_satisfies_the_capture_protocol(tiny_video: str) -> None:
    """Hop dong nay la ly do VOD va capture song thay nhau duoc."""
    assert isinstance(VideoFrameSource(tiny_video), FrameSource)


def test_missing_file_fails_immediately_not_on_first_read() -> None:
    with pytest.raises(VideoSourceError, match="khong thay file"):
        VideoFrameSource("khong-ton-tai-dau.mp4")


# --- Hoi quy: bitrate co duong lui (2026-09-07) ---------------------------


def test_stream_bitrate_is_used_when_present() -> None:
    assert _pick_bit_rate({"bit_rate": "3740612"}, {}, 100.0) == 3_740_612
    assert _bit_rate_source({"bit_rate": "3740612"}, {}, 100.0) == "stream"


def test_webm_falls_back_to_format_bitrate() -> None:
    """HOI QUY: WebM/VP9 KHONG khai bao bit_rate o muc stream.

    Do that tren mot file vp9: `streams[0]` chi co codec_name va
    avg_frame_rate. Doc moi stream roi coi 0 la that se danh truot MOI ban
    tai VP9/AV1 - dinh dang duoc khuyen dung cho cac VOD tiep theo.
    """
    stream = {"codec_name": "vp9", "avg_frame_rate": "30/1"}
    assert _pick_bit_rate(stream, {"bit_rate": "29498"}, 3.0) == 29_498
    assert _bit_rate_source(stream, {"bit_rate": "29498"}, 3.0) == "format"


def test_last_resort_is_size_over_duration() -> None:
    got = _pick_bit_rate({}, {"size": "11062"}, 3.0)
    assert got == int(11062 * 8 / 3.0)
    assert _bit_rate_source({}, {"size": "11062"}, 3.0) == "size/duration"


def test_bitrate_is_zero_only_when_truly_unknowable() -> None:
    assert _pick_bit_rate({}, {}, 0.0) == 0
    assert _bit_rate_source({}, {}, 0.0) == "khong ro"


@pytest.mark.parametrize("bad", [None, "", "N/A", "0", 0])
def test_garbage_bitrate_fields_do_not_raise(bad) -> None:
    assert _pick_bit_rate({"bit_rate": bad}, {"bit_rate": bad}, 0.0) == 0


# --- Hoi quy: phan tich fps ----------------------------------------------


@pytest.mark.parametrize("raw,want", [
    ("60/1", 60.0), ("30000/1001", pytest.approx(29.97, abs=0.01)),
    ("60", 60.0),          # so tran, khong co dau /
    ("0/0", 0.0), ("", 0.0), ("abc", 0.0), (None, 0.0),
])
def test_fps_parsing_covers_the_odd_shapes(raw, want) -> None:
    assert _parse_fps(raw) == want


# --- Hoi quy: video_id khong bao gio rong --------------------------------


@pytest.mark.parametrize("stem,want", [
    ("clip [abc123]", "abc123"),
    ("khong-co-ngoac", "khong-co-ngoac"),
    ("[]", "vod"),                      # truoc day tra "" -> moi VOD chung mot thu muc
    ("[   ]", "vod"),
])
def test_video_id_is_never_empty(stem, want, tmp_path) -> None:
    f = tmp_path / f"{stem}.mp4"
    f.write_bytes(b"x")
    assert VideoFrameSource(f).video_id == want


def test_slug_strips_unsafe_characters() -> None:
    assert _slug("4/9/2026 RRQ") == "4-9-2026-RRQ"
    assert _slug("---") == ""


# --- Hoi quy: ffmpeg vang mat --------------------------------------------


def test_missing_ffmpeg_becomes_a_readable_error(tmp_path) -> None:
    """Khong bat thi `subprocess` nem loi noi ve 'file khong tim thay' - va
    nguoi doc se tuong la noi ve file VIDEO."""
    f = tmp_path / "x.mp4"
    f.write_bytes(b"x")
    src = VideoFrameSource(f, ffprobe="ffprobe-khong-co-that-9z")
    with pytest.raises(VideoSourceError, match="PATH"):
        _ = src.meta


@needs_ffmpeg
def test_corrupt_file_gives_a_clear_message(tmp_path) -> None:
    """File rac co duoi .mp4: phai noi ro, khong duoc nem loi ffprobe tho."""
    f = tmp_path / "hong.mp4"
    f.write_bytes(b"khong phai video" * 100)
    with pytest.raises(VideoSourceError):
        _ = VideoFrameSource(f).meta


@needs_ffmpeg
def test_audio_only_file_is_rejected_with_a_reason(tmp_path) -> None:
    out = tmp_path / "chi-am-thanh.m4a"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                    "-i", "sine=frequency=440:duration=1", str(out)],
                   check=True, capture_output=True)
    with pytest.raises(VideoSourceError, match="luong video"):
        _ = VideoFrameSource(out).meta


@needs_ffmpeg
def test_corrupt_keyframe_cache_is_rebuilt_not_fatal(tiny_video: str, tmp_path) -> None:
    """Mot file JSON dut giua chung khong duoc phep chan ca duong chay."""
    cache = tmp_path / "keyframes.json"
    cache.write_text('{"keyframes": [1.0, 2.0', encoding="utf-8")
    times = VideoFrameSource(tiny_video).keyframe_times(cache=cache)
    assert times and times[0] == pytest.approx(0.0)


@needs_ffmpeg
def test_cache_with_wrong_types_is_rebuilt(tiny_video: str, tmp_path) -> None:
    cache = tmp_path / "keyframes.json"
    cache.write_text('{"keyframes": ["a", "b"]}', encoding="utf-8")
    assert len(VideoFrameSource(tiny_video).keyframe_times(cache=cache)) > 1


@needs_ffmpeg
def test_negative_seek_is_clamped_not_passed_to_ffmpeg(tiny_video: str) -> None:
    frame = VideoFrameSource(tiny_video).grab(-5.0)
    assert frame is not None and frame.t == 0.0


@needs_ffmpeg
def test_zero_fps_filter_is_rejected(tiny_video: str) -> None:
    with pytest.raises(ValueError):
        next(VideoFrameSource(tiny_video).frames(fps=0))


# --- Hoi quy: ROI suy bien ------------------------------------------------


def test_a_tiny_region_never_yields_an_empty_crop() -> None:
    """Vung ti le rat nho o do phan giai thap lam tron ve 0 pixel; khi do
    `crop` tra mang RONG va cv2 nem mot loi kho hieu o tan sau."""
    tiny = Region(0.5, 0.5, 0.0005, 0.0005)
    left, top, right, bottom = tiny.to_pixels(128, 72)
    assert right > left and bottom > top
    piece = crop(np.zeros((72, 128, 3), np.uint8), tiny)
    assert piece.size > 0


def test_a_region_at_the_far_edge_stays_inside_the_frame() -> None:
    edge = Region(0.999, 0.999, 0.001, 0.001)
    left, top, right, bottom = edge.to_pixels(128, 72)
    assert 0 <= left < right <= 128
    assert 0 <= top < bottom <= 72


def test_cropping_an_empty_image_says_so() -> None:
    with pytest.raises(RegionError, match="rong"):
        crop(np.zeros((0, 0, 3), np.uint8), Region(0.0, 0.0, 1.0, 1.0))


# --- Hoi quy: nap file ROI hong ------------------------------------------


def test_malformed_yaml_names_the_file(tmp_path) -> None:
    p = tmp_path / "screen_regions.yaml"
    p.write_text("screens: [unclosed\n", encoding="utf-8")
    with pytest.raises(RegionError):
        ScreenRegions.load(p)


def test_region_missing_keys_names_the_region(tmp_path) -> None:
    p = tmp_path / "screen_regions.yaml"
    p.write_text("screens:\n  hud:\n    gold: {x: 0.5, y: 0.5}\n", encoding="utf-8")
    with pytest.raises(RegionError, match="gold"):
        ScreenRegions.load(p)


def test_region_with_non_numeric_values_names_the_region(tmp_path) -> None:
    p = tmp_path / "screen_regions.yaml"
    p.write_text("screens:\n  hud:\n    gold: {x: a, y: 0.1, w: 0.1, h: 0.1}\n",
                 encoding="utf-8")
    with pytest.raises(RegionError, match="gold"):
        ScreenRegions.load(p)


def test_a_yaml_list_is_rejected_with_a_reason(tmp_path) -> None:
    p = tmp_path / "screen_regions.yaml"
    p.write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(RegionError, match="anh xa"):
        ScreenRegions.load(p)
