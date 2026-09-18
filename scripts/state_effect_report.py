"""Trang thai tran co doi duoc xep hang khong? Do bang nhan playtest (moc M3).

    python scripts/state_effect_report.py data/eval/playtest/<id>.json

Cham MOI offer da verified hai lan: mot lan voi trang thai that trong nhan, mot
lan voi trang thai trung tinh (cung stage, cung toc/he). Neu hai xep hang giong
het nhau o moi man thi viec doc vang/cap/chuoi tu man hinh la vo nghia - do
dung la ket luan cua buoi test 2026-09-16, va la thu M3 phai lam cho khac di.

Khong can video: nhan da chua the va trang thai.
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

import copy  # noqa: E402

from src.decision.advisor import Advisor  # noqa: E402
from src.decision.augment_advisor import AugmentAdvisor, AugmentChoice  # noqa: E402
from src.decision.state_effect import explain, measure  # noqa: E402
from src.eval.playtest_labels import PlaytestLabels, ScreenLabel, load  # noqa: E402
from src.game_state.models import GameState  # noqa: E402
from src.utils.settings import Settings  # noqa: E402


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


# Cac nut M3 dua trang thai tran vao diem. Tat het = hanh vi truoc M3.
M3_KNOBS = {
    "econ_fit": {"gold_swing": 0.0, "loss_streak_bonus": 0.0},
    "tempo_fit": {"pace_weight": 0.0},
}


def without_m3(advisor: Advisor) -> AugmentAdvisor:
    """Ban sao cua engine voi cac tin hieu M3 tat han - de doi chung."""
    config = copy.deepcopy(advisor.augment_advisor.config)
    for component, knobs in M3_KNOBS.items():
        config.tuning.setdefault(component, {}).update(knobs)
    return AugmentAdvisor(advisor.augment_advisor.features, advisor.augment_advisor.stats, config)


def report(labels: PlaytestLabels, engine: AugmentAdvisor) -> dict[str, object]:
    offers = changed = top_changed = 0
    notes: list[str] = []

    for screen in labels.verified_screens:
        state = state_of(screen)
        for offer in screen.offers:
            choices = [AugmentChoice(list(slot)) for slot in offer.cards if slot]
            if len(choices) < 2:
                continue
            offers += 1
            effect = measure(engine, choices, state)
            changed += effect.order_changed
            top_changed += effect.top_changed
            text = explain(effect, state, engine.rank(choices, state))
            if text:
                notes.append(f"{screen.stage} @{offer.at_s:.0f}s: {text}")

    return {
        "offers": offers,
        "order_changed": changed,
        "top_changed": top_changed,
        "state_effect": round(changed / offers, 3) if offers else None,
        "top_effect": round(top_changed / offers, 3) if offers else None,
        "notes": notes,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Đo ảnh hưởng của trạng thái trận lên xếp hạng")
    ap.add_argument("labels", nargs="+")
    ap.add_argument("--notes", type=int, default=10, help="số câu giải thích in ra")
    ap.add_argument("--ablate", action="store_true",
                    help="tắt các tín hiệu M3 để lấy số đối chứng trước M3")
    args = ap.parse_args(argv)

    advisor = Advisor(settings=Settings.load())
    engine = without_m3(advisor) if args.ablate else advisor.augment_advisor
    if args.ablate:
        print("ĐỐI CHỨNG: đã tắt các tín hiệu M3 (tiền, chuỗi, nhịp lên cấp)")
    total = {"offers": 0, "order_changed": 0, "top_changed": 0}
    for path in args.labels:
        result = report(load(path), engine)
        notes = result.pop("notes")
        print(f"\n== {Path(path).stem}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        for note in notes[: args.notes]:
            print(f"  - {note}")
        for key in total:
            total[key] += int(result[key] or 0)

    if len(args.labels) > 1 and total["offers"]:
        print(f"\n== tổng: {total['order_changed']}/{total['offers']} offer đổi thứ hạng "
              f"({total['order_changed'] / total['offers']:.0%}), "
              f"{total['top_changed']} lần đổi cả lựa chọn đầu")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
