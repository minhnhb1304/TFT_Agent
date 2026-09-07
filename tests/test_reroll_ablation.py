"""Test bo doi chung phan thuc cho chinh sach reroll (SPEC 12.4).

Giong tinh than test_eval.py: bo cong cu danh gia phai duoc kiem chung TRUOC
khi co du lieu that. Mot bo mo phong sai se cho ra mot bang so dep va vo
nghia, va khong co gi ben ngoai bat duoc no.
"""

from __future__ import annotations

import random

import pytest

from src.decision.reroll_policy import PoolDistribution, RerollTuning
from src.eval.reroll_ablation import (
    Draw,
    analyze,
    run_exhaust,
    run_first_look,
    run_oracle,
    run_sequential,
    sample_draws,
)


def pool(scores, *, tier: int = 2, weights=None) -> PoolDistribution:
    ordered = sorted(float(s) for s in scores)
    w = list(weights) if weights else [1.0] * len(ordered)
    total = sum(w)
    return PoolDistribution(
        tier=tier,
        scores=tuple(ordered),
        weights=tuple(x / total for x in w),
        api_names=tuple(f"DA_{i}" for i in range(len(ordered))),
        source="test",
        sample_n=0,
        is_evidence=False,
    )


LADDER = pool([i / 20 for i in range(1, 21)])


# --- Bat bien cua bo mo phong ----------------------------------------------


@pytest.mark.parametrize("seed", [1, 7, 99])
def test_oracle_equals_the_max_of_all_six_cards(seed: int) -> None:
    """Dong nhat thuc: moc 0 phu ba the dau, moc 3 phu ba the sau.

    Hop cua cac moc kha di chinh la ca sau the, nen nguoi biet truoc bao gio
    cung voi toi duoc the tot nhat trong sau. Neu dong nay gay thi tap moc
    kha di trong `run_oracle` da bi cai dat sai - va do la loi im lang nhat
    co the co: bang so van chay, chi la tran bi dat sai cho.
    """
    rng = random.Random(seed)
    for draw in sample_draws(LADDER, 200, rng):
        assert run_oracle(draw)[0] == pytest.approx(max(draw.initial + draw.redraws))


def test_oracle_is_never_beaten_by_any_real_policy() -> None:
    rng = random.Random(3)
    tuning = RerollTuning()
    cost = tuning.cost_for(LADDER, 2)
    for draw in sample_draws(LADDER, 300, rng):
        ceiling = run_oracle(draw)[0]
        assert run_first_look(draw)[0] <= ceiling + 1e-12
        assert run_exhaust(draw)[0] <= ceiling + 1e-12
        assert run_sequential(draw, LADDER, cost, 0.0)[0] <= ceiling + 1e-12


def test_draws_never_repeat_an_augment_within_one_situation() -> None:
    """Mot augment khong the hien ra hai lan trong cung mot chang."""
    rng = random.Random(11)
    names = pool([i / 50 for i in range(50)])
    for draw in sample_draws(names, 100, rng):
        six = draw.initial + draw.redraws
        assert len(set(six)) == 6


def test_sampling_is_reproducible_from_the_seed() -> None:
    a = sample_draws(LADDER, 50, random.Random(5))
    b = sample_draws(LADDER, 50, random.Random(5))
    assert a == b


def test_tailoring_weights_shift_which_cards_get_drawn() -> None:
    """beta > 0 nghia la the trung trait duoc chao nhieu hon - phai thay duoc."""
    scores = [0.1] * 10 + [0.9] * 10
    flat = pool(scores)
    tilted = pool(scores, weights=[1.0] * 10 + [9.0] * 10)
    mean_flat = sum(
        sum(d.initial) / 3 for d in sample_draws(flat, 400, random.Random(2))
    )
    mean_tilted = sum(
        sum(d.initial) / 3 for d in sample_draws(tilted, 400, random.Random(2))
    )
    assert mean_tilted > mean_flat


# --- Hanh vi cua tung chinh sach -------------------------------------------


def test_first_look_never_rerolls() -> None:
    draw = Draw((0.1, 0.2, 0.3), (0.9, 0.9, 0.9))
    assert run_first_look(draw) == (0.3, 0)


def test_exhaust_spends_every_token_and_loses_the_initial_cards() -> None:
    """Doi du ba lan thi ba the ban dau deu mat - ke ca the tot nhat.

    Day la rang buoc co che de bo quen nhat, va la ly do `exhaust_all` khong
    he tot hon `first_look` trong bang doi chung.
    """
    draw = Draw((0.1, 0.2, 0.95), (0.3, 0.3, 0.3))
    score, used = run_exhaust(draw)
    assert used == 3
    assert score == pytest.approx(0.3)  # 0.95 da bi vut di


def test_sequential_keeps_a_strong_card_instead_of_burning_it() -> None:
    """Cung tay bai voi test tren: chinh sach tuan tu phai GIU 0.95."""
    draw = Draw((0.1, 0.2, 0.95), (0.3, 0.3, 0.3))
    score, used = run_sequential(draw, LADDER, cost=0.0, risk_lambda=0.0)
    assert score == pytest.approx(0.95)
    assert used <= 2  # khong bao gio dung luot cuoi de vut chinh the dan dau


def test_sequential_collapses_to_first_look_when_rerolling_is_expensive() -> None:
    rng = random.Random(4)
    for draw in sample_draws(LADDER, 100, rng):
        assert run_sequential(draw, LADDER, cost=99.0, risk_lambda=0.0) == (
            max(draw.initial),
            0,
        )


def test_cheaper_rerolls_mean_more_rerolls() -> None:
    draws = sample_draws(LADDER, 300, random.Random(6))
    free = sum(run_sequential(d, LADDER, 0.0, 0.0)[1] for d in draws)
    dear = sum(run_sequential(d, LADDER, 0.02, 0.0)[1] for d in draws)
    assert free > dear


# --- Bang doi chung ---------------------------------------------------------


@pytest.fixture(scope="module")
def report():
    return analyze(LADDER, RerollTuning(), stage_number=2, trials=3000, bootstrap=300)


def test_sequential_beats_the_first_look_baseline(report) -> None:
    """Cau hoi ma ca module nay sinh ra de tra loi.

    Neu khoang tin cay om lay 0 thi do CUNG la mot ket qua nghien cuu hop le
    va phai bao cao trung thuc - nhung tren pool tong hop nay thi khong.
    """
    point, low, high = report.deltas["sequential"]
    assert point > 0
    assert low > 0, "khoang tin cay phai loai tru 0"


def test_exhausting_every_reroll_is_not_an_improvement(report) -> None:
    """Ket qua dang chu y: vet het luot doi KHONG hon gi khong doi lan nao.

    Luot thu ba bat buoc phai doi chinh o dang giu the tot nhat, nen loi cua
    hai lan dau bi tra lai gan het. Day la ly do "cu doi cho het" la mot loi
    khuyen toi, va la ly do phai co nguong chu khong chi co T2.
    """
    point, low, high = report.deltas["exhaust_all"]
    assert low <= 0.0 <= high, "phai khong phan biet duoc voi moc"


def test_random_choice_is_clearly_worse(report) -> None:
    point, _, high = report.deltas["random"]
    assert high < 0


def test_no_policy_beats_the_clairvoyant_ceiling(report) -> None:
    for row in report.rows:
        assert row.mean_score <= report.clairvoyant_ceiling + 1e-9


def test_report_states_the_limit_of_the_claim(report) -> None:
    """Bang nay rat de bi doc thanh "chung minh advisor tot hon". No khong.

    Cau gioi han phai nam ngay trong ban in ra, khong phai chi trong docstring.
    """
    text = report.table()
    assert "KHONG phai bang chung ve placement" in text
    assert "chinh sach so voi chinh sach" in text
    assert report.to_dict()["caveat"]


def test_report_carries_pool_provenance(report) -> None:
    assert report.pool_source == "test"
    assert report.pool_n == len(LADDER)
    assert "test" in report.table()


def test_analysis_is_reproducible(report) -> None:
    again = analyze(LADDER, RerollTuning(), stage_number=2, trials=3000, bootstrap=300)
    assert again.to_dict()["rows"] == report.to_dict()["rows"]


def test_stage_four_lets_the_policy_reroll_more_than_stage_two() -> None:
    """c(4-2) = 0 tuyet doi, nen chang cuoi phai doi nhieu hon chang dau.

    Dung tren pool prismatic vi day la bac duy nhat co c du lon de thay khac
    biet - o gold thi c da gan 0 san.
    """
    pris = pool([i / 20 for i in range(1, 21)], tier=3)
    early = analyze(pris, RerollTuning(), stage_number=2, trials=2000, bootstrap=100)
    late = analyze(pris, RerollTuning(), stage_number=4, trials=2000, bootstrap=100)
    seq = lambda r: next(x for x in r.rows if x.name == "sequential").mean_rerolls
    assert seq(late) > seq(early)
