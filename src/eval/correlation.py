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
    xs: Sequence[float], ys: Sequence[float], iterations: int = PERMUTATIONS, seed: int = SEED
) -> float:
    """p-value hai phia bang kiem dinh hoan vi.

    Dung hoan vi thay vi bang phan phoi t vi co mau cua do an nho va nhieu
    dong hang - hai dieu kien lam xap xi t kem tin cay. Seed co dinh de ket
    qua bao cao tai lap duoc.
    """
    if len(xs) < 3:
        return 1.0
    observed = abs(spearman(xs, ys))
    rng = random.Random(seed)
    shuffled = list(ys)
    hits = 0
    for _ in range(iterations):
        rng.shuffle(shuffled)
        if abs(spearman(xs, shuffled)) >= observed:
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

    @property
    def supports_hypothesis(self) -> bool:
        """Tuong quan duong va co y nghia thong ke o muc 0.05.

        Duong nghia la: advisor xep cang cao (rank nho) thi placement cang tot
        (so nho) - hai bien cung chieu.
        """
        return self.rho > 0 and self.p_value < 0.05

    def report(self) -> str:
        verdict = "ung ho" if self.supports_hypothesis else "chua du bang chung cho"
        return (
            f"Spearman rho = {self.rho:.3f} (n = {self.n}, p = {self.p_value:.4f}) "
            f"-> {verdict} gia thuyet.\n"
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
    for s in labelled:
        rank = s.pick_rank
        if rank is None or s.final_placement is None:
            continue
        xs.append(float(rank))
        ys.append(float(s.final_placement))

    skipped = len(all_scenarios) - len(xs)
    if len(xs) < 2:
        return CorrelationResult(0.0, len(xs), 1.0, 0.0, 0.0, skipped)

    return CorrelationResult(
        rho=spearman(xs, ys),
        n=len(xs),
        p_value=permutation_p_value(xs, ys),
        mean_pick_rank=sum(xs) / len(xs),
        mean_placement=sum(ys) / len(ys),
        skipped=skipped,
    )
