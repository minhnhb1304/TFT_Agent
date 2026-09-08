"""Doi chung phan thuc cho chinh sach reroll (SPEC 12.4, mo rong 3.5.5).

VI SAO PHUONG PHAP NAY DUNG DUOC NGAY HOM NAY
---------------------------------------------
Ba phuong phap con lai o SPEC 12 deu can dataset that: 12.1 can frame gan
nhan, 12.2 can `final_placement`, 12.3 can chuyen gia xep hang. Ca ba deu bi
chan boi Track B.

Phuong phap nay thi khong: no do MOT CHINH SACH so voi MOT CHINH SACH KHAC
tren cung mot ham diem. Khong can nhan cua nguoi choi, va co mau muon bao
nhieu cung duoc.

DIEU PHAI NOI RO TRONG BAO CAO
------------------------------
Ket qua o day KHONG phai bang chung ve placement. No tra loi dung mot cau
hoi: "voi cung ham Score ay, chinh sach tuan tu co lay duoc diem cao hon
chinh sach nhin-mot-lan khong". Neu ham Score sai thi ca hai chinh sach cung
sai, va so delta o day van dep nhu thuong. Do la gioi han cua thiet ke, khong
phai loi cai dat.

RANG BUOC CO CHE DE BO QUEN
---------------------------
Doi mot o la THAY the trong o do. Cai the bi doi di BIEN MAT - khong chon lai
duoc. Nen sau ba lan doi, ba the ban dau deu khong con:

    0 lan doi:  max(v1, v2, v3)
    1 lan doi:  max(v2, v3, r1)      # v1 la o te nhat, da bi thay
    2 lan doi:  max(v3, r1, r2)
    3 lan doi:  max(r1, r2, r3)      # het the ban dau

Tran cua bai toan la chinh sach BIET TRUOC (`oracle`): chon moc dung tot nhat
trong bon moc tren khi da biet ca r1, r2, r3.

Mot dong nhat thuc dang de y: moc 0 phu {v1,v2,v3} va moc 3 phu {r1,r2,r3},
nen hop cua cac moc chinh la ca sau the. Vi vay

    oracle  ==  max cua ca sau the rut

luon dung, tung tinh huong mot. Ban dau tuong "max cua 6" chi la chan tren
long leo vi the bi doi di thi mat han - nhung nguoi biet truoc bao gio cung
dung lai dung luc, nen ho voi toi duoc. Dong nhat thuc nay duoc kiem tra nhu
mot BAT BIEN cua bo mo phong (test_reroll_ablation.py): neu no gay thi tap
moc kha di da bi cai dat sai.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

from ..decision.reroll_policy import PoolDistribution, RerollState, RerollTuning, SlotView, decide

SEED = 20260907
BOOTSTRAP = 2000
DEFAULT_TRIALS = 10_000


@dataclass(frozen=True)
class Draw:
    """Mot tinh huong: ba the ban dau va ba the se hien ra neu doi.

    Rut het truoc khi mo phong de MOI chinh sach gap cung mot bo bai. Do la
    ghep cap (paired design): delta giua hai chinh sach khong con lan nhieu
    cua viec chinh sach nay gap tay bai may hon chinh sach kia.
    """

    initial: tuple[float, float, float]
    redraws: tuple[float, float, float]


@dataclass(frozen=True)
class PolicyResult:
    name: str
    mean_score: float
    mean_rerolls: float
    n: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "mean_score": round(self.mean_score, 5),
            "mean_rerolls": round(self.mean_rerolls, 3),
            "n": self.n,
        }


@dataclass
class AblationReport:
    """Bang so sanh, LUON kem canh bao ve pham vi ket luan."""

    rows: list[PolicyResult] = field(default_factory=list)
    deltas: dict[str, tuple[float, float, float]] = field(default_factory=dict)
    baseline: str = "first_look"
    n: int = 0
    seed: int = SEED
    tier: int = 2
    pool_n: int = 0
    pool_source: str = "unknown"
    evidence: str = "uncalibrated"
    clairvoyant_ceiling: float = 0.0

    def _baseline_score(self) -> float:
        for row in self.rows:
            if row.name == self.baseline:
                return row.mean_score
        return 0.0

    def table(self) -> str:
        head = (
            f"Doi chung chinh sach reroll - n = {self.n} tinh huong, seed {self.seed}\n"
            f"Pool: bac {self.tier}, N = {self.pool_n}, nguon {self.pool_source} "
            f"({self.evidence})\n"
        )
        lines = [head, f"{'chinh sach':<22}{'diem TB':>10}{'so lan doi':>12}{'delta vs ' + self.baseline:>26}"]
        lines.append("-" * 70)
        for row in self.rows:
            delta = self.deltas.get(row.name)
            cell = (
                f"{delta[0]:+.5f} [{delta[1]:+.5f}, {delta[2]:+.5f}]"
                if delta
                else "(moc)"
            )
            lines.append(
                f"{row.name:<22}{row.mean_score:>10.5f}{row.mean_rerolls:>12.2f}{cell:>26}"
            )
        lines.append("-" * 70)
        best = max((r.mean_score for r in self.rows if r.name != "oracle"), default=0.0)
        captured = (
            (best - self._baseline_score()) / (self.clairvoyant_ceiling - self._baseline_score())
            if self.clairvoyant_ceiling > self._baseline_score()
            else 0.0
        )
        lines.append(
            f"Tran biet truoc (= max cua ca 6 the rut, xem chu thich dau file): "
            f"{self.clairvoyant_ceiling:.5f}"
        )
        lines.append(f"Chinh sach tot nhat lay duoc {captured:.1%} khoang cach den tran do.")
        lines.append("")
        lines.append(
            "GIOI HAN: day la chinh sach so voi chinh sach tren CHINH HAM SCORE "
            "cua he thong.\nDay KHONG phai bang chung ve placement: neu ham Score "
            "sai thi ca hai\nchinh sach cung sai, va so delta nay van dep nhu "
            "thuong.\nKhoang tin cay la bootstrap tren cap ghep."
        )
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rows": [r.to_dict() for r in self.rows],
            "deltas": {k: [round(x, 5) for x in v] for k, v in self.deltas.items()},
            "baseline": self.baseline,
            "n": self.n,
            "seed": self.seed,
            "tier": self.tier,
            "pool_n": self.pool_n,
            "pool_source": self.pool_source,
            "evidence": self.evidence,
            "clairvoyant_ceiling": round(self.clairvoyant_ceiling, 5),
            "caveat": (
                "chinh sach vs chinh sach tren cung ham Score; "
                "KHONG phai bang chung ve placement"
            ),
        }


def sample_draws(pool: PoolDistribution, trials: int, rng: random.Random) -> list[Draw]:
    """Rut `trials` tinh huong, moi tinh huong 6 the KHONG lap lai.

    Khong lap lai la dung co che: mot augment khong the hien ra hai lan trong
    cung mot chang. Voi N = 60..132 va 6 the thi hieu chinh nay be, nhung no
    mien phi nen khong co ly do gi de lam sai.
    """
    scores = list(pool.scores)
    weights = list(pool.weights)
    out: list[Draw] = []
    for _ in range(trials):
        picked: list[float] = []
        pool_idx = list(range(len(scores)))
        w = list(weights)
        for _ in range(6):
            if not pool_idx:
                picked.append(scores[-1] if scores else 0.0)
                continue
            j = rng.choices(range(len(pool_idx)), weights=w, k=1)[0]
            picked.append(scores[pool_idx[j]])
            pool_idx.pop(j)
            w.pop(j)
        out.append(Draw(tuple(picked[:3]), tuple(picked[3:])))  # type: ignore[arg-type]
    return out


def _views(values: Sequence[float]) -> list[SlotView]:
    return [
        SlotView(index=i, lo=v, hi=v, ambiguous=False, name=f"s{i}", api_names=(f"DA_{i}",))
        for i, v in enumerate(values)
    ]


def run_sequential(draw: Draw, pool: PoolDistribution, cost: float, risk_lambda: float) -> tuple[float, int]:
    """Chinh sach tuan tu: hoi lai `decide` sau moi lan doi, dung khi no bao dung."""
    values = list(draw.initial)
    tokens = RerollState((True, True, True))
    used = 0
    for redraw in draw.redraws:
        action, target, _, _, _ = decide(_views(values), tokens, pool, cost, risk_lambda)
        if action == "PICK":
            return values[target], used
        values[target] = redraw
        tokens = tokens.spend(target)
        used += 1
    return max(values), used


def run_first_look(draw: Draw, *_: Any) -> tuple[float, int]:
    """Moc doi chung: lay the tot nhat trong ba the DAU, khong doi lan nao.

    Day chinh la hanh vi cua he thong truoc khi co module nay - `rank()` roi
    chon dong dau bang."""
    return max(draw.initial), 0


def run_exhaust(draw: Draw, *_: Any) -> tuple[float, int]:
    """Vet het ba luot doi. Chinh sach toi uu khi c = 0... nhung khong phai
    khi c > 0, va dac biet KHONG phai o day: doi lan thu ba vut mat the ban
    dau cuoi cung."""
    values = list(draw.initial)
    tokens = [True, True, True]
    for redraw in draw.redraws:
        # Chi duoc doi o CON LUOT - o da doi roi thi khong doi lai duoc.
        worst = min((i for i in range(3) if tokens[i]), key=lambda i: values[i])
        values[worst] = redraw
        tokens[worst] = False
    return max(values), 3


def run_random(draw: Draw, *_: Any, rng: random.Random | None = None) -> tuple[float, int]:
    r = rng or random.Random(SEED)
    return r.choice(draw.initial), 0


def run_oracle(draw: Draw, *_: Any) -> tuple[float, int]:
    """Tran CHAT: biet truoc r1, r2, r3 thi dung o moc nao la tot nhat.

    Bon moc kha di duoi rang buoc "doi o te nhat, the bi doi thi mat han".
    Khong chinh sach nao khong-biet-truoc vuot duoc con so nay.
    """
    v = sorted(draw.initial)
    r1, r2, r3 = draw.redraws
    reachable = [
        max(v[0], v[1], v[2]),   # 0 lan doi
        max(v[1], v[2], r1),     # doi o te nhat
        max(v[2], r1, r2),
        max(r1, r2, r3),
    ]
    best = max(reachable)
    return best, reachable.index(best)


def _bootstrap_delta(
    diffs: Sequence[float], iterations: int, seed: int
) -> tuple[float, float, float]:
    """Trung binh + khoang tin 95% bootstrap tren CHENH LECH da ghep cap."""
    n = len(diffs)
    point = sum(diffs) / n if n else 0.0
    if n < 2:
        return point, point, point
    rng = random.Random(seed)
    means = []
    for _ in range(iterations):
        means.append(sum(diffs[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    return point, means[int(0.025 * iterations)], means[int(0.975 * iterations)]


def analyze(
    pool: PoolDistribution,
    tuning: RerollTuning,
    stage_number: int = 2,
    trials: int = DEFAULT_TRIALS,
    seed: int = SEED,
    bootstrap: int = BOOTSTRAP,
) -> AblationReport:
    """Chay toan bo bang doi chung tren mot pool."""
    rng = random.Random(seed)
    draws = sample_draws(pool, trials, rng)
    cost = tuning.cost_for(pool, stage_number)

    rand = random.Random(seed + 1)
    policies: dict[str, Callable[[Draw], tuple[float, int]]] = {
        "first_look": lambda d: run_first_look(d),
        "random": lambda d: run_random(d, rng=rand),
        "exhaust_all": lambda d: run_exhaust(d),
        "sequential": lambda d: run_sequential(d, pool, cost, tuning.risk_lambda),
        "oracle": lambda d: run_oracle(d),
    }

    scores: dict[str, list[float]] = {}
    rerolls: dict[str, list[int]] = {}
    for name, fn in policies.items():
        pairs = [fn(d) for d in draws]
        scores[name] = [p[0] for p in pairs]
        rerolls[name] = [p[1] for p in pairs]

    baseline = "first_look"
    rows = [
        PolicyResult(
            name=name,
            mean_score=sum(scores[name]) / trials,
            mean_rerolls=sum(rerolls[name]) / trials,
            n=trials,
        )
        for name in policies
    ]
    deltas = {
        name: _bootstrap_delta(
            [a - b for a, b in zip(scores[name], scores[baseline])], bootstrap, seed + 2
        )
        for name in policies
        if name != baseline
    }

    return AblationReport(
        rows=rows,
        deltas=deltas,
        baseline=baseline,
        n=trials,
        seed=seed,
        tier=pool.tier,
        pool_n=len(pool),
        pool_source=pool.source,
        evidence=pool.evidence,
        clairvoyant_ceiling=sum(
            max(list(d.initial) + list(d.redraws)) for d in draws
        )
        / trials,
    )


def main(argv: Sequence[str] | None = None) -> int:
    from ..decision.augment_advisor import AugmentAdvisor
    from ..decision.scoring import ScoringConfig
    from ..game_state.models import Champion, GameState
    from ..knowledge.augment_features import FeatureTable
    from ..knowledge.stats_provider import default_provider

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--features", default="data/augment_features.json")
    parser.add_argument("--weights", default="config/scoring_weights.yaml")
    parser.add_argument("--stats-csv", default="data/augment_stats.csv")
    parser.add_argument("--tiers", default="data/augment_tiers.json")
    parser.add_argument("--tier", type=int, default=2, choices=(1, 2, 3))
    parser.add_argument("--stage", type=int, default=2, choices=(2, 3, 4))
    parser.add_argument("--trials", type=int, default=DEFAULT_TRIALS)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--tailoring-beta", type=float, default=None)
    parser.add_argument(
        "--traits",
        default="DA_Primal18:3",
        help="Trait dang bat, dang 'key:count,key:count'. Quyet dinh augment nao "
        "duoc tailoring nhan trong so - nen la can gat duy nhat cua --tailoring-beta.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    # Bang ma console Windows mac dinh (cp1252) khong in duoc tieng Viet co dau
    # trong chuoi provenance. Ep utf-8 de lenh trong tai lieu chay duoc nhu la.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    active_traits = {}
    for chunk in args.traits.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        key, _, count = chunk.partition(":")
        active_traits[key.strip()] = int(count) if count.strip() else 1

    config = ScoringConfig.load(args.weights)
    advisor = AugmentAdvisor(
        FeatureTable.load(args.features),
        default_provider(args.stats_csv, args.tiers),
        config,
    )
    tuning = RerollTuning.from_config(config)
    if args.tailoring_beta is not None:
        tuning = RerollTuning(
            risk_lambda=tuning.risk_lambda,
            tailoring_beta=args.tailoring_beta,
            burn_on_reveal=tuning.burn_on_reveal,
            cost_unit=tuning.cost_unit,
            cost_matrix=tuning.cost_matrix,
        )

    state = GameState(
        gold=30,
        level=7,
        hp=60,
        stage=f"{args.stage}-1",
        board=[
            Champion(
                name="Carry",
                cost=4,
                star_level=2,
                items=["BFSword", "RecurveBow"],
                position=(3, 3),
                traits=list(active_traits),
            )
        ],
        item_components=["BFSword"],
        # Trait CO THAT cua Set 18. Dung ten set cu ("Ravager") thi khong khop
        # augment nao ca va nhanh tailoring im lang khong lam gi.
        active_traits=active_traits,
    )
    # Pool phai dung `tailoring_beta` cua tuning nay, nen dung advisor voi
    # config da sua thay vi goi thang pool_distribution.
    advisor.config = config
    pool = advisor.pool_distribution(args.tier, state)
    if args.tailoring_beta is not None:
        pool = PoolDistribution(
            tier=pool.tier,
            scores=pool.scores,
            weights=tuple(1.0 / len(pool) for _ in pool.scores)
            if args.tailoring_beta == 0.0
            else pool.weights,
            api_names=pool.api_names,
            source=pool.source,
            sample_n=pool.sample_n,
            is_evidence=pool.is_evidence,
            evidence=pool.evidence,
        )

    report = analyze(pool, tuning, args.stage, args.trials, args.seed)
    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(report.table())
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
