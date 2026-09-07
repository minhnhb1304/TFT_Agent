"""SPEC 12.3 - dong thuan chuyen gia.

Quy trinh:
    1. `export_scenarios()` xuat ~50 tinh huong ra JSON de nguoi choi rank cao
       xep hang DOC LAP. Ban xuat co CHU Y KHONG kem xep hang cua advisor -
       neu thay truoc, chuyen gia se bi neo (anchoring) va so lieu thanh vo nghia.
    2. Chuyen gia dien `expert_ranking` vao tung muc.
    3. `analyze()` tinh top-1 agreement va he so dong thuan da hieu chinh ngau nhien.
    4. So them voi baseline "chi dung stats tinh" de tach phan dong gop cua
       nhan thuc board (SPEC 12.3 - doi chung).

VI SAO KHONG CON LA COHEN'S KAPPA (sua 2026-09-06)

Docstring cu da noi dung y dinh: "voi 3 lua chon, doan bua da trung 33% roi".
Nhung cai duoc cai dat lai khong lam dieu do.

Cohen's kappa uoc luong dong thuan ngau nhien tu PHAN PHOI BIEN cua tung
nguoi cham tren MOT khong gian nhan chung. O day khong gian nhan chung do
khong ton tai: moi tinh huong chao 3 augment KHAC NHAU, gan nhu roi nhau.
Gop tat ca apiName lai lam moi nhan chi con tan suat ~1/n, keo dong thuan
ky vong xuong ~1/n thay vi 1/3 dung ra phai co.

Hau qua do duoc: voi n = 18 va p_o = 0.60, cong thuc cu tra 0.577 ("kha"),
gia tri dung la 0.40 ("trung binh"). Cong thuc cu THOI PHONG ket qua, va
thoi phong theo huong co loi cho do an - dung loai sai so khong duoc phep lot.

Thay bang Brennan-Prediger S: p_e = trung binh cua 1/k_i voi k_i la so lua
chon duoc chao o tinh huong i. Voi k = 3 thi p_e = 1/3, dung bang cai ma
docstring cu da tuyen bo la muon hieu chinh.

CO MAU NHO THI PHAI NOI RA

Voi n = 18, sai so chuan cua S vao khoang 0.2: mot uoc luong diem 0.40 di kem
khoang tin cay trai qua ba bac cua thang Landis-Koch. Vi the `report()` CHI
in nhan dinh bac khi khoang tin cay bootstrap nam gon trong mot bac.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

from .scenario_logger import Scenario

# Seed co dinh: ban xuat phai tai lap duoc, neu khong thi khong kiem chung lai
# duoc thu tu da cho chuyen gia xem.
SHUFFLE_SEED = 20260906

# So lan bootstrap de uoc luong khoang tin cay cua S.
BOOTSTRAP = 2000
BOOTSTRAP_SEED = 20260906


@dataclass
class ExpertEntry:
    """Mot tinh huong da co ca xep hang cua advisor lan cua chuyen gia."""

    scenario_id: str
    candidates: list[str]
    advisor_ranking: list[str]
    expert_ranking: list[str]
    expert_id: str = "expert-1"

    @property
    def advisor_top(self) -> str | None:
        return self.advisor_ranking[0] if self.advisor_ranking else None

    @property
    def expert_top(self) -> str | None:
        return self.expert_ranking[0] if self.expert_ranking else None

    @property
    def agrees(self) -> bool:
        return self.advisor_top is not None and self.advisor_top == self.expert_top

    @property
    def n_choices(self) -> int:
        """So lua chon duoc chao - mau so cua xac suat doan bua o tinh huong nay."""
        return max(
            len(self.candidates), len(self.advisor_ranking), len(self.expert_ranking)
        )


@dataclass
class ExpertReport:
    n: int = 0
    top1_agreement: float = 0.0
    kappa: float = 0.0                  # Brennan-Prediger S
    expected_agreement: float = 0.0
    ci_low: float = 0.0
    ci_high: float = 0.0
    per_expert: dict[str, float] = field(default_factory=dict)
    statistic: str = "brennan-prediger-s"

    def report(self) -> str:
        head = (
            f"Dong thuan top-1: {self.top1_agreement:.1%} tren {self.n} tinh huong\n"
            f"Brennan-Prediger S: {self.kappa:.3f} "
            f"[KTC 95%: {self.ci_low:.3f} .. {self.ci_high:.3f}] "
            f"(dong thuan ky vong do ngau nhien: {self.expected_agreement:.1%})\n"
        )
        return head + _verdict(self.ci_low, self.ci_high)

    def to_dict(self) -> dict[str, Any]:
        return {
            "n": self.n,
            "statistic": self.statistic,
            "top1_agreement": round(self.top1_agreement, 4),
            "kappa": round(self.kappa, 4),
            "expected_agreement": round(self.expected_agreement, 4),
            "ci_low": round(self.ci_low, 4),
            "ci_high": round(self.ci_high, 4),
            "per_expert": {k: round(v, 4) for k, v in self.per_expert.items()},
        }


# Thang Landis & Koch, dang (nguong tren, ten bac).
_BANDS: tuple[tuple[float, str], ...] = (
    (0.00, "te hon ngau nhien"),
    (0.20, "khong dang ke"),
    (0.40, "yeu"),
    (0.60, "trung binh"),
    (0.80, "kha"),
    (float("inf"), "rat cao"),
)


def _band(value: float) -> str:
    """Bac Landis & Koch cua mot gia tri."""
    for upper, label in _BANDS:
        if value < upper:
            return label
    return _BANDS[-1][1]


def _verdict(ci_low: float, ci_high: float) -> str:
    """Doc S theo thang Landis & Koch - nhung CHI khi co mau du de doc.

    Neu khoang tin cay trai qua nhieu hon mot bac thi in mot bac duy nhat la
    tu lua: uoc luong diem khong phan biet duoc voi cac bac ben canh. Truong
    hop do bao cao chinh khoang tin cay, khong bao cao nhan dinh.
    """
    low_band, high_band = _band(ci_low), _band(ci_high)
    if low_band != high_band:
        return (
            "Muc do dong thuan: CHUA KET LUAN DUOC - khoang tin cay trai tu "
            f"'{low_band}' den '{high_band}'. Co mau chua du de xep bac; bao cao "
            "uoc luong diem kem khoang tin cay, KHONG kem nhan dinh bac."
        )
    return f"Muc do dong thuan: {low_band}."


def export_scenarios(
    scenarios: Iterable[Scenario],
    out_path: str | Path,
    limit: int = 50,
    seed: int = SHUFFLE_SEED,
) -> Path:
    """Xuat ban de chuyen gia xep hang - KHONG kem ket qua cua advisor.

    Giau xep hang cua advisor la yeu cau phuong phap, khong phai tuy chon: cho
    chuyen gia thay truoc thi so lieu dong thuan do niem tin vao advisor chu
    khong do chat luong cua no.

    GIAU KHOA KHONG DU - PHAI GIAU CA THU TU (sua 2026-09-06)

    Ban cu ghi `candidates = list(scenario.ranking)`, tuc la giu DUNG THU TU
    advisor da xep: lua chon so 1 cua advisor luon nam dau danh sach. Bo khoa
    "ranking" di nhung de nguyen thu tu thi khong giau duoc gi - chuyen gia doc
    tu tren xuong van bi neo y het nhu khi thay xep hang.

    Test cu (`test_export_hides_advisor_ranking_to_avoid_anchoring`) chi kiem
    tra khoa "ranking" vang mat, nen no xanh trong khi loi van con - cung loai
    sai lam da ghi o dev_log muc 6.

    Gio thu tu duoc xao tron tat dinh theo `scenario_id`; seed ghi kem tung dong
    de tai lap va kiem chung lai duoc.
    """
    payload: list[dict[str, Any]] = []
    for i, scenario in enumerate(list(scenarios)[:limit], start=1):
        state = scenario.game_state
        scenario_id = scenario.path.stem if scenario.path else f"s{i:03d}"

        # Tat dinh va khong phu thuoc PYTHONHASHSEED: bam tu chinh chuoi id.
        row_seed = seed + (
            int.from_bytes(scenario_id.encode("utf-8"), "little", signed=False) % 65536
            if scenario_id
            else i
        )
        candidates = list(scenario.ranking)
        random.Random(row_seed).shuffle(candidates)

        payload.append({
            "scenario_id": scenario_id,
            "frame_ref": scenario.frame_ref,
            "tinh_huong": {
                "stage": state.stage,
                "hp": state.hp,
                "gold": state.gold,
                "level": state.level,
                "traits": state.active_traits,
                "board": [
                    {"ten": c.name, "sao": c.star_level, "items": c.items}
                    for c in state.board
                ],
                "manh_trang_bi": state.item_components,
                "augment_dang_co": state.augments,
            },
            "candidates": candidates,
            "candidate_seed": row_seed,
            "expert_ranking": [],   # <- chuyen gia dien vao day
        })

    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return p


def load_expert_entries(
    export_path: str | Path, scenarios: Iterable[Scenario], expert_id: str = "expert-1"
) -> list[ExpertEntry]:
    """Ghep ban chuyen gia da dien voi xep hang cua advisor.

    Khong tim thay scenario goc thi BO QUA dong do. Ban cu lay
    `row["candidates"]` lam xep hang cua advisor; sau khi `export_scenarios`
    xao tron thi thu tu do khong con la cua advisor nua, va dung bua se tao ra
    mot con so dong thuan hoan toan gia.
    """
    filled = json.loads(Path(export_path).read_text(encoding="utf-8"))
    by_id = {
        (s.path.stem if s.path else ""): s for s in scenarios
    }

    entries: list[ExpertEntry] = []
    for row in filled:
        expert_ranking = row.get("expert_ranking") or []
        if not expert_ranking:
            continue    # chua dien thi bo qua, khong doan ho
        scenario = by_id.get(row.get("scenario_id", ""))
        if scenario is None:
            continue    # khong truy nguoc duoc advisor ranking -> khong dem
        entries.append(
            ExpertEntry(
                scenario_id=row.get("scenario_id", ""),
                candidates=list(row.get("candidates", [])),
                advisor_ranking=list(scenario.ranking),
                expert_ranking=list(expert_ranking),
                expert_id=row.get("expert_id", expert_id),
            )
        )
    return entries


def chance_corrected_agreement(
    entries: Sequence[ExpertEntry],
) -> tuple[float, float, float]:
    """Brennan-Prediger S tren lua chon top-1.

    p_e = trung binh cua 1/k_i, voi k_i la so augment duoc chao o tinh huong i.
    Voi 3 lua chon moi tinh huong thi p_e = 1/3 - dung xac suat doan bua that,
    khong phu thuoc vao viec cac tinh huong co chung nhan hay khong.

    Returns:
        (S, dong thuan quan sat, dong thuan ky vong)
    """
    valid = [e for e in entries if e.advisor_top and e.expert_top]
    if not valid:
        return 0.0, 0.0, 0.0

    observed = sum(1 for e in valid if e.agrees) / len(valid)

    chances = [1.0 / e.n_choices for e in valid if e.n_choices >= 2]
    if not chances:
        # Chi co mot lua chon -> khong co gi de dong thuan. Bao 1.0 la tu khen.
        return 0.0, observed, 1.0
    expected = sum(chances) / len(chances)

    s = (observed - expected) / (1 - expected) if expected < 1 else 0.0
    return s, observed, expected


def bootstrap_ci(
    entries: Sequence[ExpertEntry],
    iterations: int = BOOTSTRAP,
    seed: int = BOOTSTRAP_SEED,
) -> tuple[float, float]:
    """Khoang tin cay 95% cua S, bootstrap lay lai mau theo tinh huong.

    Bat buoc o co mau cua do an: uoc luong diem mot minh khong doc duoc -
    xem docstring dau file.
    """
    valid = [e for e in entries if e.advisor_top and e.expert_top]
    if len(valid) < 2:
        return 0.0, 0.0

    rng = random.Random(seed)
    stats: list[float] = []
    for _ in range(iterations):
        sample = [valid[rng.randrange(len(valid))] for _ in range(len(valid))]
        stats.append(chance_corrected_agreement(sample)[0])
    stats.sort()
    lo = stats[int(0.025 * (len(stats) - 1))]
    hi = stats[int(0.975 * (len(stats) - 1))]
    return lo, hi


def analyze(entries: Sequence[ExpertEntry]) -> ExpertReport:
    """Tinh dong thuan top-1 va S, tach theo tung chuyen gia."""
    if not entries:
        return ExpertReport()

    s, observed, expected = chance_corrected_agreement(entries)
    ci_low, ci_high = bootstrap_ci(entries)

    per_expert: dict[str, float] = {}
    for expert in {e.expert_id for e in entries}:
        subset = [e for e in entries if e.expert_id == expert]
        per_expert[expert] = sum(1 for e in subset if e.agrees) / len(subset)

    return ExpertReport(
        n=len(entries),
        top1_agreement=observed,
        kappa=s,
        expected_agreement=expected,
        ci_low=ci_low,
        ci_high=ci_high,
        per_expert=per_expert,
    )
