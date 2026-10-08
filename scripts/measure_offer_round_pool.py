"""Do truoc/sau cua co `reroll_policy.pool_by_offer_round` va cong P5.

    python scripts/measure_offer_round_pool.py            # bang truoc/sau
    python scripts/measure_offer_round_pool.py --p5       # cong P5 (nhan dien)
    python scripts/measure_offer_round_pool.py --json

PHEP DO. The gioi that = pool theo luot (cung bac VA chao o luot nay). Rut
`--trials` tay bai 6 the tu pool THAT do, roi cho chinh sach tuan tu choi hai
lan tren CUNG tay bai: mot lan tin vao pool cung bac (co tat), mot lan tin vao
pool theo luot (co bat). Chenh lech la ghep cap, khoang tin bootstrap - cung
thiet ke voi src/eval/reroll_ablation.py.

Hai cot delta. "diem" = diem the cuoi cung, KHONG tru gi. "muc tieu" = diem tru
c * so lan doi, voi c tinh tren pool THAT - day moi la dai luong chinh sach toi
uu hoa (V = ... - c). Khi c > 0, chinh sach tin pool cung bac doi NHIEU hon vi
tuong con the tot hon de rut; no co the nhat them chut diem tho nhung tra gia c
ma cot "diem" khong thay.

Bang feature chua co `offer_rounds` thi luot duoc nap tu snapshot
data/augment_rounds.datatft.json vao bo nho (KHONG ghi file) va dong dau cua
bao cao noi ro dieu do.

GIOI HAN nhu reroll_ablation: chinh sach so voi chinh sach tren cung ham Score,
KHONG phai bang chung ve placement.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import replace
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.decision.augment_advisor import AugmentAdvisor  # noqa: E402
from src.decision.reroll_policy import RerollState, RerollTuning, decide  # noqa: E402
from src.decision.scoring import ScoringConfig  # noqa: E402
from src.eval.reroll_ablation import (  # noqa: E402
    SEED,
    _bootstrap_delta,
    _views,
    run_sequential,
    sample_draws,
)
from src.game_state.models import Champion, GameState  # noqa: E402
from src.knowledge.augment_catalog import AugmentCatalog  # noqa: E402
from src.knowledge.augment_features import OFFER_ROUNDS, FeatureTable  # noqa: E402
from src.knowledge.stats_provider import default_provider  # noqa: E402


def load_snapshot_rounds(path: Path) -> dict[str, list[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {api: list(row.get("rounds") or []) for api, row in data["augments"].items()}


def overlay_rounds(table: FeatureTable, rounds: dict[str, list[str]]) -> int:
    """Nap luot tu snapshot vao cac dong CHUA co offer_rounds. Tra so dong da nap."""
    filled = 0
    for api, feature in table.features.items():
        if not feature.offer_rounds and rounds.get(api):
            feature.offer_rounds = [r for r in OFFER_ROUNDS if r in rounds[api]]
            filled += 1
    return filled


def demo_state(offer_round: str, traits: dict[str, int]) -> GameState:
    """Cung ban co gia lap voi reroll_ablation.main, chi doi stage."""
    return GameState(
        gold=30,
        level=7,
        hp=60,
        stage=offer_round,
        board=[
            Champion(name="Carry", cost=4, star_level=2, items=["BFSword", "RecurveBow"],
                     position=(3, 3), traits=list(traits))
        ],
        item_components=["BFSword"],
        active_traits=traits,
    )


def measure_cell(advisor, tuning, tier: int, offer_round: str, traits, trials: int, seed: int) -> dict:
    state = demo_state(offer_round, traits)
    stage = state.stage_number
    off = advisor.pool_distribution(tier, state, tuning=replace(tuning, pool_by_offer_round=False))
    on = advisor.pool_distribution(tier, state, tuning=replace(tuning, pool_by_offer_round=True))

    draws = sample_draws(on, trials, random.Random(seed))  # the gioi that = pool theo luot
    c_off, c_on = tuning.cost_for(off, stage), tuning.cost_for(on, stage)
    tokens = RerollState()

    first_flips = to_pick = to_reroll = path_flips = 0
    diffs: list[float] = []
    net_diffs: list[float] = []
    sum_off = sum_on = used_off = used_on = 0.0
    for d in draws:
        a_off = decide(_views(d.initial), tokens, off, c_off, tuning.risk_lambda)[0]
        a_on = decide(_views(d.initial), tokens, on, c_on, tuning.risk_lambda)[0]
        if a_off != a_on:
            first_flips += 1
            to_pick += a_on == "PICK"
            to_reroll += a_on == "REROLL"
        s_off, u_off = run_sequential(d, off, c_off, tuning.risk_lambda)
        s_on, u_on = run_sequential(d, on, c_on, tuning.risk_lambda)
        path_flips += u_off != u_on
        diffs.append(s_on - s_off)
        net_diffs.append((s_on - c_on * u_on) - (s_off - c_on * u_off))
        sum_off += s_off
        sum_on += s_on
        used_off += u_off
        used_on += u_on

    delta = _bootstrap_delta(diffs, 2000, seed + 2)
    net_delta = _bootstrap_delta(net_diffs, 2000, seed + 2)
    median = on.scores[len(on) // 2] if len(on) else 0.0
    return {
        "tier": tier,
        "round": offer_round,
        "scope_on": on.scope,
        "n_off": len(off),
        "n_on": len(on),
        "sigma_off": off.sigma,
        "sigma_on": on.sigma,
        "top_off": off.scores[-1] if len(off) else 0.0,
        "top_on": on.scores[-1] if len(on) else 0.0,
        # g(R) tai R = trung vi cua pool that: gia tri ky vong cua mot lan doi.
        "floor": median,
        "emax_off": off.expected_max(median),
        "emax_on": on.expected_max(median),
        "trials": trials,
        "first_flips": first_flips,
        "flip_to_pick": to_pick,
        "flip_to_reroll": to_reroll,
        "path_flips": path_flips,
        "score_off": sum_off / trials,
        "score_on": sum_on / trials,
        "rerolls_off": used_off / trials,
        "rerolls_on": used_on / trials,
        "delta": list(delta),
        "cost_off": c_off,
        "cost_on": c_on,
        "net_delta": list(net_delta),
    }


def p5_gate(rounds: dict[str, list[str]], locale_paths: dict[str, Path]) -> list[dict]:
    """Nhom trung ten hien thi co offer_rounds KHAC nhau khong (luot tach duoc khong)."""
    out = []
    for lang, path in locale_paths.items():
        catalog = AugmentCatalog(json.loads(path.read_text(encoding="utf-8")))
        for key, group in sorted(catalog.ambiguous_groups.items()):
            members = [
                {"api_name": a.api_name, "tier": a.tier, "rounds": rounds.get(a.api_name, [])}
                for a in group
            ]
            sets = [set(m["rounds"]) for m in members]
            known = all(sets)
            # Tach duoc HOAN TOAN: khong luot nao chung. Tach MOT PHAN: tap khac nhau
            # nhung con luot chung (o luot chung do van map mo).
            disjoint = known and all(
                not (sets[i] & sets[j]) for i in range(len(sets)) for j in range(i + 1, len(sets))
            )
            differ = known and any(s != sets[0] for s in sets)
            out.append({
                "lang": lang,
                "name": key,
                "members": members,
                "verdict": "tach hoan toan" if disjoint else "tach mot phan" if differ
                else "khong tach duoc" if known else "thieu du lieu",
            })
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--features", default="data/augment_features.json")
    ap.add_argument("--weights", default="config/scoring_weights.yaml")
    ap.add_argument("--stats-csv", default="data/augment_stats.csv")
    ap.add_argument("--tiers", default="data/augment_tiers.json")
    ap.add_argument("--snapshot", default="data/augment_rounds.datatft.json")
    ap.add_argument("--traits", default="DA_Primal18:3")
    ap.add_argument("--trials", type=int, default=10_000)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--p5", action="store_true", help="chi chay cong P5")
    ap.add_argument("--locale-en", default="tests/fixtures/cdragon/en_us.trimmed.json")
    ap.add_argument("--locale-vi", default="tests/fixtures/cdragon/vi_vn.trimmed.json")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    rounds = load_snapshot_rounds(ROOT / args.snapshot)

    if args.p5:
        groups = p5_gate(rounds, {"en": ROOT / args.locale_en, "vi": ROOT / args.locale_vi})
        if args.json:
            print(json.dumps(groups, ensure_ascii=False, indent=2))
            return 0
        for g in groups:
            cells = "; ".join(
                f"{m['api_name']} (bac {m['tier']}): {','.join(m['rounds']) or '?'}"
                for m in g["members"]
            )
            print(f"[{g['lang']}] {g['name']}: {cells} -> {g['verdict']}")
        return 0

    table = FeatureTable.load(ROOT / args.features)
    filled = overlay_rounds(table, rounds)
    config = ScoringConfig.load(ROOT / args.weights)
    advisor = AugmentAdvisor(table, default_provider(ROOT / args.stats_csv, ROOT / args.tiers), config)
    tuning = RerollTuning.from_config(config)
    traits = {}
    for chunk in args.traits.split(","):
        key, _, count = chunk.strip().partition(":")
        if key:
            traits[key] = int(count) if count else 1

    cells = [
        measure_cell(advisor, tuning, tier, r, traits, args.trials, args.seed)
        for tier in (1, 2, 3)
        for r in OFFER_ROUNDS
    ]
    if args.json:
        print(json.dumps({"rounds_from_snapshot": filled, "cells": cells}, ensure_ascii=False, indent=2))
        return 0

    print(
        f"offer_rounds: {filled} dong nap tu snapshot {args.snapshot} vao bo nho"
        if filled
        else "offer_rounds: doc tu bang feature"
    )
    print(f"n = {args.trials} tay bai/o, seed {args.seed}, min_round_pool = {tuning.min_round_pool}\n")
    print("bac luot  pham vi      N tat->bat   sigma tat->bat    dinh tat->bat    g(med) tat->bat")
    for c in cells:
        print(
            f"{c['tier']:>3} {c['round']:<5} {c['scope_on']:<11} {c['n_off']:>4}->{c['n_on']:<4}  "
            f"{c['sigma_off']:.4f}->{c['sigma_on']:.4f}   {c['top_off']:.4f}->{c['top_on']:.4f}   "
            f"{c['emax_off']:.4f}->{c['emax_on']:.4f}"
        )
    print("\nbac luot  lat buoc 1 (->PICK/->REROLL)   lat ca van   so lan doi tat->bat   delta diem bat-tat [KTC 95%]          c that   delta muc tieu [KTC 95%]")
    for c in cells:
        d, m = c["delta"], c["net_delta"]
        print(
            f"{c['tier']:>3} {c['round']:<5} {c['first_flips']:>6} ({c['flip_to_pick']}/{c['flip_to_reroll']})"
            f"{'':<12}{c['path_flips']:>6}       {c['rerolls_off']:.2f}->{c['rerolls_on']:.2f}"
            f"          {d[0]:+.5f} [{d[1]:+.5f}, {d[2]:+.5f}]"
            f"   {c['cost_on']:.5f}   {m[0]:+.5f} [{m[1]:+.5f}, {m[2]:+.5f}]"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
