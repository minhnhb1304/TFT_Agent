"""Doc frame tu file video qua ffmpeg (SPEC 3.1 - nhanh VOD cua tang capture).

VI SAO LA NGUON HOP LE CHO DO AN, KHONG PHAI DUONG TAT

`research/vanguard/testing-protocol.md` buoc 3 - "Record once, develop offline
forever" - da chot: quay lai vai van roi dung ban ghi do de dung toan bo tang
vision va gan nhan 200-500 frame cho SPEC 12.1. Doc mot file video CHINH LA
buoc do. Khong co gi chay luc game dang mo, khong chup man hinh, khong overlay,
khong liet ke tien trinh - moi co che trong `detection-surface.md` deu doi hoi
dong-thuc-thi, nen o day rui ro anti-cheat bang khong ve mat cau truc.

VI SAO FFMPEG CHU KHONG PHAI cv2.VideoCapture

`cv2.VideoCapture.set(CAP_PROP_POS_MSEC)` tren file H.264 dai tra ve frame
lech vai giay va khong bao loi. ffmpeg voi `-ss` DAT TRUOC `-i` nhay theo
keyframe roi giai ma toi dung moc - chinh xac, va nhanh hon vi bo qua phan
truoc do. Do la khac biet giua "gan dung" va "truy nguyen duoc", ma ca dataset
danh gia dua tren viec truy nguyen duoc.

DO LON DON VI CONG VIEC LA I-FRAME, KHONG PHAI FRAME

VOD do bang do an co GOP = 1 giay (do 2026-09-06: 600 keyframe / 600 giay).
Vi the 5 gio video = 18.225 I-frame chu khong phai 1,09 trieu frame. Quet toan
bo o muc I-frame ton ~8 phut; khong can bat ky co che ne tranh nao ca.

BITRATE PHAI CO DUONG LUI (sua 2026-09-07)

WebM/VP9 **khong khai bao `bit_rate` o muc stream** - do that: mot file vp9
chi co `format.bit_rate`. Doc moi stream roi coi 0 la "bitrate bang khong" se
danh truot MOI ban tai VP9/AV1, ma do lai chinh la dinh dang duoc khuyen dung.
Vi the: stream -> format -> tu tinh tu `size/duration`.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Iterator

import numpy as np

from .frame_source import Frame, format_ref

# ffmpeg 9 da BO `-vsync`; ban thay the la `-fps_mode`. Ghim o day de khong
# ai vo tinh chep lai cau lenh cu tu tren mang.
FPS_MODE = ["-fps_mode", "passthrough"]

THUMB_W, THUMB_H = 128, 72


class VideoSourceError(RuntimeError):
    """ffmpeg/ffprobe thieu hoac that bai, hoac file khong doc duoc."""


def _run(cmd: list[str]) -> bytes:
    """Chay ffmpeg/ffprobe. Moi that bai deu thanh VideoSourceError.

    Bat rieng FileNotFoundError: khi ffmpeg khong co tren PATH, `subprocess`
    nem mot loi noi ve 'file khong tim thay' ma nguoi doc se tuong la noi ve
    file VIDEO. Doi thanh cau noi dung ten thu phai cai.
    """
    try:
        proc = subprocess.run(cmd, capture_output=True)
    except FileNotFoundError as exc:
        raise VideoSourceError(
            f"khong tim thay '{cmd[0]}' tren PATH. Cai ffmpeg roi thu lai."
        ) from exc
    except OSError as exc:
        raise VideoSourceError(f"khong chay duoc '{cmd[0]}': {exc}") from exc

    if proc.returncode != 0:
        tail = proc.stderr.decode("utf-8", "replace").strip().splitlines()[-3:]
        raise VideoSourceError(f"{cmd[0]} loi: " + " | ".join(tail))
    return proc.stdout


class VideoFrameSource:
    """Nguon frame doc tu file video. Cung Protocol voi capture man hinh."""

    def __init__(
        self,
        path: str | Path,
        ffmpeg: str = "ffmpeg",
        ffprobe: str = "ffprobe",
    ) -> None:
        self.path = Path(path)
        if not self.path.is_file():
            raise VideoSourceError(f"khong thay file video: {self.path}")
        self.ffmpeg = ffmpeg
        self.ffprobe = ffprobe
        self._meta: dict[str, object] | None = None

    # --- sieu du lieu ----------------------------------------------------

    @property
    def meta(self) -> dict[str, object]:
        if self._meta is None:
            raw = _run([
                self.ffprobe, "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=width,height,avg_frame_rate,nb_frames,"
                                 "codec_name,profile,bit_rate:"
                                 "format=duration,bit_rate,size",
                "-of", "json", str(self.path),
            ])
            try:
                data = json.loads(raw.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise VideoSourceError(f"ffprobe tra ve du lieu hong: {exc}") from exc

            streams = data.get("streams") or []
            if not streams:
                raise VideoSourceError(
                    f"{self.path.name}: khong co luong video nao. "
                    "File hong hoac chi co am thanh?"
                )
            stream = streams[0]
            fmt = data.get("format") or {}
            width = int(stream.get("width") or 0)
            height = int(stream.get("height") or 0)
            if width <= 0 or height <= 0:
                raise VideoSourceError(
                    f"{self.path.name}: kich thuoc khung khong hop le "
                    f"({width}x{height}). File hong?"
                )
            duration = float(fmt.get("duration") or 0.0)

            self._meta = {
                "width": width,
                "height": height,
                "codec": stream.get("codec_name", ""),
                "profile": stream.get("profile", ""),
                "bit_rate": _pick_bit_rate(stream, fmt, duration),
                "bit_rate_source": _bit_rate_source(stream, fmt, duration),
                "duration": duration,
                "fps": _parse_fps(stream.get("avg_frame_rate", "0/0")),
            }
        return self._meta

    @property
    def size(self) -> tuple[int, int]:
        return int(self.meta["width"]), int(self.meta["height"])   # type: ignore[arg-type]

    @property
    def duration(self) -> float:
        return float(self.meta["duration"])   # type: ignore[arg-type]

    @property
    def video_id(self) -> str:
        """Id de dat ten thu muc dan xuat.

        Ten file yt-dlp ket thuc bang `[<id>]`; lay duoc thi dung, khong thi
        lui ve ten file da lam sach. KHONG bam noi dung: 8,8 GB doc mot lan
        chi de dat ten la vo ly.

        Luon tra ve chuoi KHONG RONG: id rong se lam moi thu muc dan xuat do
        ve chung mot cho va hai VOD ghi de len nhau.
        """
        stem = self.path.stem
        if stem.endswith("]") and "[" in stem:
            inner = stem[stem.rindex("[") + 1:-1].strip()
            if inner:
                return _slug(inner)
        return _slug(stem) or "vod"

    # --- lay frame -------------------------------------------------------

    def grab(self, at: float | None = None) -> Frame | None:
        """Mot frame tai moc `at` giay (mac dinh: dau video)."""
        t = 0.0 if at is None else max(0.0, float(at))
        w, h = self.size
        need = w * h * 3
        raw = _run([
            self.ffmpeg, "-v", "error",
            "-ss", f"{t:.3f}", "-i", str(self.path),
            "-frames:v", "1", *FPS_MODE,
            "-pix_fmt", "bgr24", "-f", "rawvideo", "-",
        ])
        if need <= 0 or len(raw) < need:
            return None
        image = np.frombuffer(raw[:need], np.uint8).reshape(h, w, 3)
        return Frame(image=image, t=t, ref=format_ref(f"vod:{self.video_id}", t))

    def frames(
        self,
        start: float = 0.0,
        end: float | None = None,
        keyframes_only: bool = False,
        fps: float | None = None,
    ) -> Iterator[Frame]:
        """Duyet frame. `keyframes_only` dung luong I-frame lam nhip 1 fps."""
        w, h = self.size
        cmd = [self.ffmpeg, "-v", "error"]
        if keyframes_only:
            cmd += ["-skip_frame", "nokey"]
        cmd += ["-ss", f"{max(0.0, start):.3f}"]
        if end is not None:
            cmd += ["-t", f"{max(0.0, end - start):.3f}"]
        cmd += ["-i", str(self.path), "-an", *FPS_MODE]
        if fps is not None:
            if fps <= 0:
                raise ValueError(f"fps phai duong, nhan duoc {fps}")
            cmd += ["-vf", f"fps={fps}"]
        cmd += ["-pix_fmt", "bgr24", "-f", "rawvideo", "-"]

        step = 1.0 / fps if fps else 1.0     # I-frame = 1 giay o VOD nay
        yield from self._stream(cmd, w, h, 3, start, step)

    def thumbnails(
        self, width: int = THUMB_W, height: int = THUMB_H, start: float = 0.0
    ) -> tuple[np.ndarray, np.ndarray]:
        """Toan bo I-frame o dang anh xam thu nho.

        Tra `(thumbs, times)`: thumbs la (N, height, width) uint8, times la (N,)
        giay. Voi VOD 5 gio o 128x72 thi ton ~168 MB - vua du nam trong RAM va
        du de tuong quan cheo toan bo dong thoi gian bang numpy trong tich tac.
        """
        if width < 1 or height < 1:
            raise ValueError("kich thuoc anh thu nho phai duong")
        cmd = [
            self.ffmpeg, "-v", "error", "-skip_frame", "nokey",
            "-ss", f"{max(0.0, start):.3f}", "-i", str(self.path), "-an", *FPS_MODE,
            "-vf", f"scale={width}:{height}:flags=area,format=gray",
            "-f", "rawvideo", "-",
        ]
        frames = list(self._stream(cmd, width, height, 1, start, 1.0))
        if not frames:
            return np.empty((0, height, width), np.uint8), np.empty(0, np.float64)
        thumbs = np.stack([f.image[:, :, 0] for f in frames])
        times = np.array([f.t for f in frames], np.float64)
        return thumbs, times

    def _stream(
        self, cmd: list[str], w: int, h: int, channels: int, start: float, step: float
    ) -> Iterator[Frame]:
        """Doc rawvideo tu stdout cua ffmpeg thanh tung Frame."""
        nbytes = w * h * channels
        shape = (h, w, channels)
        prefix = f"vod:{self.video_id}"
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except FileNotFoundError as exc:
            raise VideoSourceError(
                f"khong tim thay '{cmd[0]}' tren PATH. Cai ffmpeg roi thu lai."
            ) from exc
        except OSError as exc:
            raise VideoSourceError(f"khong chay duoc '{cmd[0]}': {exc}") from exc

        with proc:
            if proc.stdout is None:                  # pragma: no cover - Popen dam bao
                raise VideoSourceError("khong mo duoc stdout cua ffmpeg")
            index = 0
            while True:
                buf = proc.stdout.read(nbytes)
                if len(buf) < nbytes:
                    break
                t = start + index * step
                yield Frame(
                    image=np.frombuffer(buf, np.uint8).reshape(shape),
                    t=t,
                    ref=format_ref(prefix, t),
                )
                index += 1
            proc.stdout.close()
            if proc.wait() != 0:
                tail = (proc.stderr.read() if proc.stderr else b"")
                raise VideoSourceError(
                    "ffmpeg dung giua chung: "
                    + tail.decode("utf-8", "replace").strip()[-300:]
                )

    # --- keyframe --------------------------------------------------------

    def keyframe_times(self, cache: str | Path | None = None) -> list[float]:
        """Moc thoi gian cua moi I-frame. Cache lai vi ffprobe quet ca file.

        Cache hong thi quet lai chu khong nem: mot file JSON dut giua chung
        khong duoc phep chan ca duong chay.
        """
        if cache is not None and Path(cache).is_file():
            try:
                data = json.loads(Path(cache).read_text(encoding="utf-8"))
                times = data["keyframes"]
                if isinstance(times, list) and all(
                    isinstance(t, (int, float)) for t in times
                ):
                    return [float(t) for t in times]
            except (json.JSONDecodeError, KeyError, TypeError, OSError):
                pass    # cache hong -> quet lai

        raw = _run([
            self.ffprobe, "-v", "error", "-select_streams", "v:0",
            "-show_entries", "packet=pts_time,flags", "-of", "csv=p=0", str(self.path),
        ])
        times: list[float] = []
        for line in raw.decode("utf-8", "replace").splitlines():
            parts = line.strip().split(",")
            if len(parts) >= 2 and parts[1].startswith("K"):
                try:
                    times.append(float(parts[0]))
                except ValueError:
                    continue
        if cache is not None:
            p = Path(cache)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(
                json.dumps({"source": str(self.path), "keyframes": times}),
                encoding="utf-8",
            )
        return times


def _slug(text: str) -> str:
    """Chuoi an toan de dat ten thu muc."""
    return "".join(c if c.isalnum() or c in "-_" else "-" for c in text)[:48].strip("-")


def _pick_bit_rate(stream: dict, fmt: dict, duration: float) -> int:
    """bit_rate cua stream -> cua format -> tu tinh. Xem docstring dau file."""
    for value in (stream.get("bit_rate"), fmt.get("bit_rate")):
        try:
            n = int(value)          # type: ignore[arg-type]
        except (TypeError, ValueError):
            continue
        if n > 0:
            return n
    try:
        size = int(fmt.get("size"))     # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0
    return int(size * 8 / duration) if duration > 0 and size > 0 else 0


def _bit_rate_source(stream: dict, fmt: dict, duration: float) -> str:
    """Bitrate lay tu dau - de bao cao noi that thay vi im lang."""
    try:
        if int(stream.get("bit_rate")) > 0:      # type: ignore[arg-type]
            return "stream"
    except (TypeError, ValueError):
        pass
    try:
        if int(fmt.get("bit_rate")) > 0:         # type: ignore[arg-type]
            return "format"
    except (TypeError, ValueError):
        pass
    return "size/duration" if _pick_bit_rate(stream, fmt, duration) else "khong ro"


def _parse_fps(rate: str | None) -> float:
    """`"60/1"` -> 60.0, `"60"` -> 60.0. Tra 0.0 khi ffprobe khong biet."""
    if not rate:
        return 0.0
    text = str(rate).strip()
    try:
        if "/" in text:
            num, _, den = text.partition("/")
            d = float(den)
            return float(num) / d if d else 0.0
        return float(text)
    except (ValueError, ZeroDivisionError):
        return 0.0
