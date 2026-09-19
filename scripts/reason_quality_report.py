"""Cau ly do co thong tin khong, hay chi lap lai? (buoc A3, moc M4)

    python scripts/reason_quality_report.py data/eval/playtest/<id>.json

Buoi test 2026-09-16 de lai mot phan nan rat cu the: ba cot ly do noi gan
nhu cung mot thu ("Bac S theo bang tier...", "HP 64 con thoai mai"), nen doc
xong van khong biet chon cai nao. G3 dat dich `dup_reasons = 0`.

Do tren CHINH DU LIEU NGUOI CHOI NHIN THAY, khong do tren `entry.reasons`
tho: `build_view` gom cau chung len dai trang thai roi cat khoi tung cot
(buoc A1), nen do truoc gom se bao cao mot con so bi quan sai.

Khong can video: nhan da chua the va trang thai.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
import sys

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.decision.advisor import Advisor  # noqa: E402
from src.decision.augment_advisor import AugmentChoice  # noqa: E402
from src.eval.playtest_labels import PlaytestLabels, ScreenLabel, load  # noqa: E402
from src.game_state.models import GameState  # noqa: E402
from src.live.events import AdviceReady  # noqa: E402
from src.replay.viewmodel import build_view  # noqa: E402
from src.utils.settings import Settings  # noqa: E402
from src.vision.augment_reader import CardRead  # noqa: E402


def state_of(screen: ScreenLabel) -> GameState:
    hud = screen.hud or {}
    return GameState(
        gold=int(hud.get("gold") or 0),
        level=int(hud.get("level") or 1),
        hp=int(hud.get("hp") or 100),
        xp=int(hud.get("xp") or 0),
        xp_needed=hud.get("xp_needed"),
        stage=screen.stage,
        streak=int(hud.get("streak") or 0),
        active_traits=dict(screen.traits or {}),
    )


def cards_of(offer) -> tuple[CardRead, ...]:
    """Nhan -> `CardRead` nhu the bo doc vua tra ve, de di dung duong that."""
    return tuple(
        CardRead(slot=i, title="", body="", api_names=tuple(slot), confidence=1.0, reason="")
        for i, slot in enumerate(offer.cards)
        if slot
    )


def measure(labels: PlaytestLabels, advisor: Advisor) -> dict[str, object]:
    offers = 0
    dup_slots = 0                     # so O mang mot cau trung voi o khac
    dup_examples: Counter[str] = Counter()
    empty_slots = 0                   # cot khong co cau nao - im lang cung la loi
    per_slot: list[int] = []
    seen: Counter[str] = Counter()
    edges = 0
    edge_examples: list[str] = []
    dup_chars = [0]
    total_chars = [0]

    for screen in labels.verified_screens:
        state = state_of(screen)
        for offer in screen.offers:
            cards = cards_of(offer)
            if len(cards) < 2:
                continue
            offers += 1
            choices = [AugmentChoice(list(c.api_names)) for c in cards]
            bundle = advisor.advise(state, choices)
            event = AdviceReady(t=offer.at_s, stage=screen.stage, bundle=bundle, state=state,
                                cards=cards, rerolls=None)
            _strip, verdict, slots = build_view(event)

            if verdict.edge:
                edges += 1
                if len(edge_examples) < 8:
                    edge_examples.append(f"{screen.stage} @{offer.at_s:.0f}s: {verdict.edge}")

            counts: Counter[str] = Counter()
            for slot in slots:
                per_slot.append(len(slot.reasons))
                if not slot.reasons:
                    empty_slots += 1
                for reason in slot.reasons:
                    counts[reason] += 1
                    seen[reason] += 1
            for reason, n in counts.items():
                if n > 1:
                    dup_slots += n
                    dup_examples[reason] += n
                    # Dem CHU chu khong chi dem cau: rut ngan mot doan lap 20
                    # chu xuong 6 chu la mot cai thien that, ma `dup_reasons`
                    # khong nhin thay - hai lan lap van la hai lan lap.
                    dup_chars[0] += len(reason) * (n - 1)
            total_chars[0] += sum(len(r) for s in slots for r in s.reasons)

    total_slots = len(per_slot)
    return {
        "offers": offers,
        "slots": total_slots,
        "dup_reasons": dup_slots,
        "dup_rate": round(dup_slots / total_slots, 3) if total_slots else None,
        "dup_chars": dup_chars[0],
        "dup_char_rate": round(dup_chars[0] / total_chars[0], 3) if total_chars[0] else None,
        "empty_slots": empty_slots,
        "distinct_reasons": len(seen),
        "reasons_per_slot": round(sum(per_slot) / total_slots, 2) if total_slots else None,
        "edge_coverage": round(edges / offers, 3) if offers else None,
        "top_repeated": dup_examples.most_common(5),
        "most_common": seen.most_common(5),
        "edge_examples": edge_examples,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Đo chất lượng câu lý do (G3)")
    ap.add_argument("labels", nargs="+")
    ap.add_argument("--examples", type=int, default=8, help="số câu so sánh in ra")
    args = ap.parse_args(argv)

    advisor = Advisor(settings=Settings.load())
    total = {"offers": 0, "slots": 0, "dup_reasons": 0, "empty_slots": 0,
             "dup_chars": 0}

    for path in args.labels:
        result = measure(load(path), advisor)
        examples = result.pop("edge_examples")
        print(f"\n== {Path(path).stem}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        for line in examples[: args.examples]:
            print(f"  - {line}")
        for key in total:
            total[key] += int(result[key] or 0)

    if len(args.labels) > 1 and total["slots"]:
        print(f"\n== tổng: {total['dup_reasons']}/{total['slots']} ô mang câu trùng "
              f"({total['dup_reasons'] / total['slots']:.0%}), "
              f"{total['empty_slots']} ô không có câu nào")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
