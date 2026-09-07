"""SPEC 12.2 - tuong quan giua xep hang cua advisor va ket qua that.

GIA THUYET: chon augment ma advisor xep cao -> placement tot hon.

Bien X = thu hang advisor gan cho augment nguoi choi DA chon (1 = cao nhat).
Bien Y = placement cuoi tran (1 = nhat).
Neu gia thuyet dung, hai bien nay tuong quan DUONG (chon hang thap -> ve nhi).

GIOI HAN PHAI NEU TRONG BAO CAO, KHONG DUOC IM:
    - Day la du lieu QUAN SAT, khong phai thi nghiem co doi chung. Nguoi choi
      chon augment nao la do ho, khong phai do ta phan cong ngau nhien.
    - Augment chi la MOT trong rat nhieu yeu to quyet dinh placement.
    - Vi the: bao cao rho, co mau, va khoang tin cay. KHONG duoc tuyen bo nhan qua.

HOAN VI PHAI THEO KHOI, KHONG DUOC HOAN VI TU DO (sua 2026-09-06)

`final_placement` la dai luong CUA MOT TRAN. Ba quyet dinh augment trong cung
mot van deu mang dung mot gia tri Y. Vay 18 scenario khong phai 18 quan sat
doc lap ma la 6 cum, moi cum 3 dong trung Y.

Ban cu hoan vi ys tu do tren ca 18 dong. Lam the la pha vo cau truc cum va
dung nen phan phoi null HEP HON that, khien p-value nho hon that -> de dai
(anti-conservative), tuc la co the bia ra y nghia thong ke khong co.

Gio hoan vi o CAP VAN: xao tron viec gan placement cho tung van, giu nguyen
bo ba scenario ben trong moi van. Khi thieu `game_id` (file schema 1) thi
KHONG im lang gia vo la doc lap - `n_games = None` va `report()` noi ro.

Spearman duoc tu cai dat (khong dung scipy) vi cong thuc ngan, va vi mot phu
thuoc nang chi de tinh mot he so la cai gia khong dang - nhung phai xu ly HANG
DONG HANG cho dung, do la cho de sai nhat.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterable, Sequence

from .scenario_logger import Scenario, iter_labelled

# So lan hoan vi de uoc luong p-value. 2000 la du de phan biet p < 0.05 ma van
# chay trong tich tac tren dataset co do lon cua mot do an.
PERMUTATIONS = 2000
SEED = 20260829


def rank_with_ties(values: Sequence[float]) -> list[float]:
    """Xep hang co xu ly dong hang bang hang trung binh.

    Bo qua buoc nay la loi kinh dien khi tu cai Spearman: dataset cua ta CHAC
    CHAN co dong hang (nhieu tran cung placement, nhieu lua chon cung thu hang),
    va xep hang tho se lam lech he so mot cach im lang.
    """
    indexed = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i
        while j + 1 < len(indexed) and values[indexed[j + 1]] == values[indexed[i]]:
            j += 1
        average = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[indexed[k]] = average
        i = j + 1
    return ranks


def pearson(xs: Sequence[float], ys: Sequence[float]) -> float:
    """He so Pearson. Tra 0.0 khi mot bien khong co phuong sai."""
    n = len(xs)
    if n < 2:
        return 0.0
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    return num / (dx * dy) if dx and dy else 0.0


def spearman(xs: Sequence[float], ys: Sequence[float]) -> float:
    """He so Spearman = Pearson tren hang."""
    if len(xs) != len(ys):
        raise ValueError("hai day phai cung do dai")
    return pearson(rank_with_ties(xs), rank_with_ties(ys))


def permutation_p_value(
    xs: Sequence[float],
    ys: Sequence[float],
    groups: Sequence[str] | None = None,
    iterations: int = PERMUTATIONS,
    seed: int = SEED,
) -> float:
    """p-value hai phia bang kiem dinh hoan vi.

    Dung hoan vi thay vi bang phan phoi t vi co mau cua do an nho va nhieu
    dong hang - hai dieu kien lam xap xi t kem tin cay. Seed co dinh de ket
    qua bao cao tai lap duoc.

    `groups` la nhan cum (o day: id van dau). Co nhan thi hoan vi THEO KHOI:
    xao tron viec gan Y cho tung cum, giu nguyen cac dong ben trong mot cum.
    Khong co nhan thi hoan vi tu do - chi dung duoc khi cac dong that su doc lap.
    """
    if len(xs) < 3:
        return 1.0
    observed = abs(spearman(xs, ys))
    rng = random.Random(seed)
    hits = 0

    if groups is None:
        shuffled = list(ys)
        for _ in range(iterations):
            rng.shuffle(shuffled)
            if abs(spearman(xs, shuffled)) >= observed:
                hits += 1
        return (hits + 1) / (iterations + 1)

    # Hoan vi theo khoi: Y khong doi trong mot cum, nen chi xao tron gia tri
    # cap cum roi phat lai xuong tung dong.
    order: list[str] = []
    value_of: dict[str, float] = {}
    for g, y in zip(groups, ys):
        if g not in value_of:
            value_of[g] = y
            order.append(g)
    if len(order) < 3:
        return 1.0

    values = [value_of[g] for g in order]
    for _ in range(iterations):
        rng.shuffle(values)
        remap = dict(zip(order, values))
        if abs(spearman(xs, [remap[g] for g in groups])) >= observed:
            hits += 1
    return (hits + 1) / (iterations + 1)


@dataclass
class CorrelationResult:
    """Ket qua 12.2, kem moi thu can de doc no cho dung."""

    rho: float
    n: int
    p_value: float
    mean_pick_rank: float
    mean_placement: float
    skipped: int = 0
    n_games: int | None = None      # so cum doc lap; None = thieu game_id

    @property
    def supports_hypothesis(self) -> bool:
        """Tuong quan duong va co y nghia thong ke o muc 0.05.

        Duong nghia la: advisor xep cang cao (rank nho) thi placement cang tot
        (so nho) - hai bien cung chieu.
        """
        return self.rho > 0 and self.p_value < 0.05

    def report(self) -> str:
        verdict = "ung ho" if self.supports_hypothesis else "chua du bang chung cho"
        if self.n_games is None:
            cum = (
                "CANH BAO: scenario khong co `game_id` nen khong gom cum duoc. "
                "p-value tinh bang hoan vi TU DO va vi the DE DAI - coi 3 quyet "
                "dinh cung mot van la doc lap la sai."
            )
        else:
            cum = (
                f"Co mau doc lap that su: {self.n_games} van (tren {self.n} "
                f"quyet dinh). p-value hoan vi theo khoi cap van."
            )
        return (
            f"Spearman rho = {self.rho:.3f} (n = {self.n}, p = {self.p_value:.4f}) "
            f"-> {verdict} gia thuyet.\n"
            f"{cum}\n"
            f"Thu hang trung binh cua lua chon: {self.mean_pick_rank:.2f}; "
            f"placement trung binh: {self.mean_placement:.2f}; "
            f"bo qua {self.skipped} scenario thieu nhan.\n"
            "Luu y: du lieu quan sat, khong phai thi nghiem co doi chung - "
            "khong duoc dien giai nhan qua."
        )


def analyze(scenarios: Iterable[Scenario]) -> CorrelationResult:
    """Tinh tuong quan tren cac scenario da co ca lua chon lan placement."""
    all_scenarios = list(scenarios)
    labelled = list(iter_labelled(all_scenarios))

    xs: list[float] = []
    ys: list[float] = []
    groups: list[str] = []
    for s in labelled:
        rank = s.pick_rank
        if rank is None or s.final_placement is None:
            continue
        xs.append(float(rank))
        ys.append(float(s.final_placement))
        groups.append(s.game_id or "")

    skipped = len(all_scenarios) - len(xs)
    if len(xs) < 2:
        return CorrelationResult(0.0, len(xs), 1.0, 0.0, 0.0, skipped)

    # Chi gom cum khi MOI scenario deu khai bao game_id. Thieu du mot cai la
    # khong biet dong do thuoc van nao -> bao None thay vi doan.
    clustered = all(groups)
    return CorrelationResult(
        rho=spearman(xs, ys),
        n=len(xs),
        p_value=permutation_p_value(xs, ys, groups if clustered else None),
        mean_pick_rank=sum(xs) / len(xs),
        mean_placement=sum(ys) / len(ys),
        skipped=skipped,
        n_games=len(set(groups)) if clustered else None,
    )
