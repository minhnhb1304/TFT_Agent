"""Khung hinh -> FrameReader (3 chan hop nhat) -> Advisor.advise() (SPEC 3.1, Nhiem vu 3).

    # Che do anh don le:
    python scripts/advise_from_frame.py --frame data/frames/5tshRxYLwv8/augment_select/augment_select_041_020047.png

    # Che do tu video: duyet lui de prime GameStateTracker, vang/cap/xp thanh gia tri that:
    python scripts/advise_from_frame.py --from-video "downloads/midfeed_tpc_final [s7h-jHMpFmQ].mkv" --at 4205

    # Cac co ghi de thu cong khi can thiet:
    python scripts/advise_from_frame.py --frame <anh.png> --stage 3-2 --gold 32 --level 6 \
        --choices DA_BandOfThieves1,DA_ComponentBuffet,DA_18_RiftbeastTraitAugment
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.capture.video_source import VideoFrameSource  # noqa: E402
from src.decision.advisor import Advisor  # noqa: E402
from src.decision.augment_advisor import AugmentChoice  # noqa: E402
from src.decision.reroll_policy import RerollState  # noqa: E402
from src.game_state.models import GameState  # noqa: E402
from src.game_state.state_tracker import GameStateTracker  # noqa: E402
from src.utils.settings import Settings  # noqa: E402
from src.vision.augment_reader import (  # noqa: E402
    DEFAULT_MODEL,
    DEFAULT_NAME_INDEX,
    DEFAULT_TIMEOUT_S,
)
from src.vision.frame_reader import FrameReader, FrameReading  # noqa: E402
from src.vision.hud_reader import DEFAULT_REGIONS  # noqa: E402
from src.vision.reroll_buttons import DEFAULT_TEMPLATE, RerollButtonReader  # noqa: E402


def _prime_tracker_from_video(
    video_path: str | Path,
    target_t: float,
    frame_reader: FrameReader,
) -> GameStateTracker:
    """Duyet lui cac frame truoc do tu VOD de nap du lieu HUD (vang, cap, xp) vao tracker."""
    tracker = GameStateTracker()
    vs = VideoFrameSource(video_path)

    # Thu thap mau nguoc thoi gian trong khoang 30s truoc moc target_t
    # de tim cac khung hinh giai doan planning co thanh HUD day du
    offsets = [30.0, 25.0, 20.0, 15.0, 10.0, 5.0, 3.0]
    sampled_times = [max(0.0, target_t - off) for off in offsets]

    for t_sample in sorted(sampled_times):
        f = vs.grab(t_sample)
        if f is not None and f.image is not None and f.image.size > 0:
            try:
                hud_reading = frame_reader.hud_reader.read(f.image)
                tracker.update(hud_reading)
            except Exception:
                pass

    return tracker


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--frame", help="duong dan khung hinh anh PNG")
    ap.add_argument("--from-video", dest="from_video", help="duong dan file video de doc frame va prime tracker")
    ap.add_argument("--at", type=float, default=0.0, help="moc thoi gian (giay) trong video khi dung --from-video")
    ap.add_argument("--regions", default=DEFAULT_REGIONS, help="file cau hinh ScreenRegions")
    ap.add_argument("--template", default=DEFAULT_TEMPLATE, help="file anh mau glyph reroll")
    ap.add_argument("--names", default=DEFAULT_NAME_INDEX, help="file chi muc ten")
    ap.add_argument("--model", default=None, help="ten model Gemini Vision (mac dinh lay tu Settings)")
    ap.add_argument("--timeout", type=float, default=None, help="timeout goi Vision (giay, mac dinh lay tu Settings)")

    # Cac co ghi de (None = lay tu pixel)
    ap.add_argument("--stage", default=None, help="ghi de stage (vi du: 3-2)")
    ap.add_argument("--gold", type=int, default=None, help="ghi de vang (vi du: 32)")
    ap.add_argument("--level", type=int, default=None, help="ghi de cap (vi du: 6)")
    ap.add_argument("--hp", type=int, default=None, help="ghi de mau (vi du: 85)")
    ap.add_argument("--traits", default=None, help='ghi de toc/he, dang "TFT13_Bruiser:2,TFT13_Dominance:3"')
    ap.add_argument("--choices", default=None, help="ghi de ba apiName, phan cach bang dau phay")
    ap.add_argument("--json", action="store_true", help="in JSON thay vi van ban")
    args = ap.parse_args(argv)

    if not args.frame and not args.from_video:
        ap.error("phai truyen --frame <anh.png> hoac --from-video <video.mkv> --at <t>")

    import cv2

    frame_ref = args.frame or f"{args.from_video}@{args.at:.1f}s"
    frame_img = None

    settings = Settings.load()
    reader = FrameReader.load(
        regions=args.regions,
        settings=settings,
        template=args.template,
        names=args.names,
        model=args.model,
        timeout_s=args.timeout,
    )

    tracker = None
    if args.from_video:
        vs = VideoFrameSource(args.from_video)
        f = vs.grab(args.at)
        if f is None or f.image is None:
            print(f"Không thể trích xuất khung hình tại giây {args.at} từ {args.from_video}")
            return 1
        frame_img = f.image
        # Prime tracker tu cac frame truoc
        tracker = _prime_tracker_from_video(args.from_video, args.at, reader)
    else:
        frame_img = cv2.imread(args.frame)
        if frame_img is None:
            print(f"Không đọc được khung hình: {args.frame}")
            return 1

    # Doc hop nhat tu FrameReader
    reading: FrameReading = reader.read(frame_img, tracker=tracker)

    # 1. Guards: kiem tra man hinh augment_select va nut reroll
    reroll_reading = reader.reroll_reader.read(frame_img)
    if not reroll_reading.screen_present:
        print("Khung này không phải màn chọn augment — không có gì để tư vấn.")
        for r in reroll_reading.reads:
            print(f"  {r.reason}")
        return 1

    if not reroll_reading.settled:
        print("Một ô chưa ngã ngũ (khung nháy lúc bấm chuột). Đọc lại ở khung kế tiếp:")
        for r in reroll_reading.reads:
            if not r.settled:
                print(f"  {r.reason}")
        return 1

    rerolls = reading.rerolls or reroll_reading.to_reroll_state()

    # 2. Xu ly cac co override va xac dinh provenance (pixel vs co)
    provenance: dict[str, str] = {}

    final_stage = reading.state.stage
    if args.stage is not None:
        final_stage = args.stage
        provenance["stage"] = "từ cờ --stage"
    else:
        provenance["stage"] = "từ pixel"

    final_hp = reading.state.hp
    if args.hp is not None:
        final_hp = args.hp
        provenance["hp"] = "từ cờ --hp"
    else:
        provenance["hp"] = "từ pixel"

    final_gold = reading.state.gold
    if args.gold is not None:
        final_gold = args.gold
        provenance["gold"] = "từ cờ --gold"
    else:
        provenance["gold"] = "từ video (tracker)" if any("gold: stale" in d for d in reading.degraded) else (
            "mặc định (chưa thấy trên HUD)" if any("gold: never_seen" in d for d in reading.degraded) else "từ pixel"
        )

    final_level = reading.state.level
    if args.level is not None:
        final_level = args.level
        provenance["level"] = "từ cờ --level"
    else:
        provenance["level"] = "từ video (tracker)" if any("level: stale" in d for d in reading.degraded) else (
            "mặc định (chưa thấy trên HUD)" if any("level: never_seen" in d for d in reading.degraded) else "từ pixel"
        )

    final_xp = reading.state.xp

    final_traits = dict(reading.state.active_traits)
    if args.traits is not None:
        final_traits = {}
        for part in args.traits.split(","):
            key, _, count = part.partition(":")
            final_traits[key.strip()] = int(count or 1)
        provenance["traits"] = "từ cờ --traits"
    else:
        provenance["traits"] = "từ pixel (Gemini Vision)"

    state = GameState(
        gold=final_gold,
        level=final_level,
        hp=final_hp,
        stage=final_stage,
        xp=final_xp,
        active_traits=final_traits,
    )

    # Choices
    choices: list[AugmentChoice | str] = []
    if args.choices is not None:
        choices = [c.strip() for c in args.choices.split(",") if c.strip()]
        provenance["choices"] = "từ cờ --choices"
    else:
        choices = list(reading.choices)
        provenance["choices"] = "từ pixel (Gemini Vision)"

    if not choices:
        print("Chưa có 3 thẻ augment để xếp hạng (Gemini không khả dụng hoặc chưa đọc được).")
        print("Hãy kiểm tra GEMINI_API_KEY hoặc truyền --choices để ghi đè.")
        if reading.degraded:
            print(f"Lỗi chi tiết: {'; '.join(reading.degraded)}")
        return 1

    # 3. Goi Advisor
    bundle = Advisor().advise(state, choices, frame_ref=frame_ref, rerolls=rerolls)

    if args.json:
        out_data = {
            "state": state.__dict__,
            "provenance": provenance,
            "rerolls": reading.rerolls.available if reading.rerolls else None,
            "advice": bundle.to_dict(),
            "degraded": reading.degraded,
            "latency_ms": reading.latency_ms,
        }
        print(json.dumps(out_data, indent=2, ensure_ascii=False, default=str))
        return 0

    print(f"Khung hình: {frame_ref}")
    print("Nguồn dữ liệu:")
    print(f"  chặng:  {state.stage:<8} ({provenance['stage']})")
    print(f"  máu:    {state.hp:<8} ({provenance['hp']})")
    print(f"  vàng:   {state.gold:<8} ({provenance['gold']})")
    print(f"  cấp:    {state.level:<8} ({provenance['level']})")
    print(f"  tộc/hệ: {len(state.active_traits)} tộc/hệ ({provenance['traits']})")
    print(f"  lõi:    {len(choices)} thẻ    ({provenance['choices']})")

    print("\nTrạng thái nút đổi thẻ:")
    for r in reroll_reading.reads:
        print(f"  ô {r.slot + 1}: {r.state:9s} {r.reason}")
    print(f"  -> RerollState.available = {rerolls.available}\n")

    if bundle.ranking:
        print("Xếp hạng augment:")
        for i, row in enumerate(bundle.ranking.entries):
            print(f"  #{i + 1} ô {row.choice_index + 1}: {row.name:<25} {row.total:.3f}")

    if bundle.reroll:
        print(f"\nKhuyến nghị đổi thẻ:")
        print(f"  hành động: {bundle.reroll.action} -> ô {bundle.reroll.target_slot + 1}")
        print(f"  lý do:     {bundle.reroll.reason}")

    if reading.degraded:
        print(f"\nThông tin suy giảm (degraded):")
        for d in reading.degraded:
            print(f"  - {d}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
