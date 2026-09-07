"""Chinh sach reroll augment - bai toan dung toi uu huu han (SPEC 3.5.5).

`AugmentAdvisor.rank()` tra loi cau hoi "the nao tot nhat trong ba the DANG
hien". Module nay tra loi cau hoi khac han: "co nen doi mot the di khong, va
doi the nao".

MO HINH
-------
Trong MOT chang augment, goi `L` la diem cao nhat trong cac o da tieu ton
luot reroll (an toan vinh vien), `v(1) <= ... <= v(n)` la diem cac o con giu
luot. `F_S` la phan bo cua `Score(a | S)` tren pool cung bac.

    V(L, {})        = L
    V(L, v(1..n))   = max( max(L, v(n)),                       # PICK
                           E[ V(max(L,sigma), v(2..n)) ] - c )  # REROLL o te nhat

Ba ket qua khien bai toan sup xuong con MOT phep so sanh:

T1  Doi o te nhat la toi uu (lap luan ghep cap: tap giu lai troi hon tung
    phan tu so voi doi bat ky o nao khac).
T2  Neu c = 0 va n >= 2 thi REROLL TROI HON PICK theo nghia yeu - ca `L` lan
    `v(n)` deu song sot, nen gia tri dung sau khi doi khong the thap hon.
    Dung som luc do la LO EV. Day la cho trai voi truc giac "gap S thi chot".
T3  Voi `B` = diem tot nhat hien co va `R` = san giu lai neu doi o muc tieu:
        REROLL  <=>  g(R) - c > B ,  g(R) = E[max(R, sigma)]
    Ve phai giam theo B nen vung dung LIEN THONG - luat mot buoc chinh la
    luat toi uu, khong can bang nguong theo tung buoc.

Bai toan chuan la McCall sequential search WITH RECALL (Ferguson ch.2,
https://www.math.ucla.edu/~tom/Stopping/sr2.pdf). KHONG phai secretary
problem (khong nho, khong biet F) va KHONG phai Cayley-Moser (khong nho).

HAI DIEU DE LAM SAI
-------------------
1. `F_S` KHONG deu. Co che tailoring cua TFT uu tien augment trung trait dang
   bat - dung deu se DANH GIA THAP continuation value va lam may so hai reroll
   mot cach nhan tao. Xem `tailoring_beta`.
2. Muc do tin cay cua so lieu KHONG duoc chan quyet dinh. `B` va `F_S` cung
   sinh ra tu MOT ham diem, nen phep so sanh giua chung bat bien qua moi phep
   hieu chinh don dieu - no van dung khi `Base` trung tinh o ca 254 augment.
   Cai khong the tuyen bo la "nguong nay quy ra placement". Noi ro dieu do,
   dung tu choi tra loi.
"""

from __future__ import annotations

import math
from bisect import bisect_right
from dataclasses import dataclass, field
from typing import Any, Literal, Sequence

from ..knowledge.stats_provider import is_fabricated  # noqa: F401 - tai xuat
from .scoring.types import ScoringConfig

# Bac augment -> ten trong cost_matrix. Khop voi `AugmentFeature.tier` (1..3).
TIER_NAMES = {1: "silver", 2: "gold", 3: "prismatic"}

# Diem tong luon >= 0 (moi component da clamp01, moi trong so >= 0), nen 0.0
# la san hop le cho "chua giu duoc gi ca".
NO_FLOOR = 0.0

EvidenceLevel = Literal["measured", "ordinal", "uncalibrated"]


@dataclass(frozen=True)
class RerollState:
    """O nao con luot doi. Dau vao TUONG MINH: man hinh khong hien so dem.

    Da doi chieu tren frame Set 18 that (`augment_select_023_011007.png`):
    ba nut doi rieng tung the, trang thai phan biet duoc bang hinh anh, va
    KHONG co bo dem so o dau ca. Vi the lop nhan dang khong the suy ra con
    bao nhieu luot tu mot khung hinh don le - no phai duoc truyen vao.
    """

    available: tuple[bool, ...] = (True, True, True)
    # apiName da tung hien ra trong van nay. Chi co nghia khi burn_on_reveal.
    burned: tuple[str, ...] = ()

    @property
    def n_available(self) -> int:
        return sum(1 for a in self.available if a)

    def has(self, slot: int) -> bool:
        return 0 <= slot < len(self.available) and bool(self.available[slot])

    def spend(self, slot: int) -> "RerollState":
        """Ban sao da tieu luot cua mot o - dung cho mo phong va test."""
        av = list(self.available)
        if 0 <= slot < len(av):
            av[slot] = False
        return RerollState(tuple(av), self.burned)


@dataclass(frozen=True)
class PoolDistribution:
    """Phan bo thuc nghiem CO TRONG SO cua Score(a|S) tren mot bac augment.

    Dung MOT LAN moi khi man chon augment hien ra (do duoc: 1.39 ms p50 /
    2.18 ms p95 cho bac dong nhat, N=132), roi moi quyet dinh sau do chi la
    O(log N) tren mang da sap - vai microsecond. Trang thai game dung yen
    trong ~30 giay nen khong can tinh lai.
    """

    tier: int
    scores: tuple[float, ...]      # da sap TANG DAN
    weights: tuple[float, ...]     # trong so tailoring, da chuan hoa, khop chi so
    api_names: tuple[str, ...]     # khop chi so voi `scores`
    source: str
    sample_n: int                  # tong co mau tu StatsProvider, 0 neu khong co
    is_evidence: bool
    evidence: EvidenceLevel = "uncalibrated"
    # Do lech chuan cua pool - DON VI cua chi phi doi. Xem `RerollTuning.cost_unit`.
    sigma: float = field(default=0.0, compare=False)
    # Tong hau to, de tra loi expected_max trong O(log N). Khong tham gia so sanh.
    _suf_w: tuple[float, ...] = field(default=(), repr=False, compare=False)
    _suf_ws: tuple[float, ...] = field(default=(), repr=False, compare=False)

    def __post_init__(self) -> None:
        n = len(self.scores)
        suf_w = [0.0] * (n + 1)
        suf_ws = [0.0] * (n + 1)
        for i in range(n - 1, -1, -1):
            suf_w[i] = suf_w[i + 1] + self.weights[i]
            suf_ws[i] = suf_ws[i + 1] + self.weights[i] * self.scores[i]
        object.__setattr__(self, "_suf_w", tuple(suf_w))
        object.__setattr__(self, "_suf_ws", tuple(suf_ws))
        if n and not self.sigma:
            mean = sum(self.scores) / n
            var = sum((x - mean) ** 2 for x in self.scores) / n
            object.__setattr__(self, "sigma", math.sqrt(var))

    def __len__(self) -> int:
        return len(self.scores)

    def expected_max(self, floor: float) -> float:
        """g(floor) = E[max(floor, sigma)] - chinh xac, khong xap xi.

        Vi `scores` da sap va `weights` da chuan hoa, tich phan viet duoi dang
        tong hau to: phan <= floor dong gop `floor`, phan con lai dong gop
        chinh no.
        """
        if not self.scores:
            return floor
        i = bisect_right(self.scores, floor)
        return floor * (1.0 - self._suf_w[i]) + self._suf_ws[i]

    def tail_integral(self, floor: float) -> float:
        """int_floor^1 (1 - F) du = g(floor) - floor. Luon >= 0."""
        return max(0.0, self.expected_max(floor) - floor)

    def certainty_equivalent(self, floor: float, risk_lambda: float = 0.0) -> float:
        """Tuong duong chac chan cua max(floor, sigma) duoi thoa dung mu.

        `risk_lambda` > 0 = ngai rui ro, < 0 = ua rui ro, 0 = trung lap va rot
        thang ve `expected_max`. Mac dinh 0: anh huong cua HP len GIA TRI cua
        augment da nam o TempoFit roi, dua no vao day nua la dem hai lan.
        """
        if risk_lambda == 0.0 or not self.scores:
            return self.expected_max(floor)
        lam = float(risk_lambda)
        i = bisect_right(self.scores, floor)
        acc = math.exp(-lam * floor) * (1.0 - self._suf_w[i])
        for j in range(i, len(self.scores)):
            acc += self.weights[j] * math.exp(-lam * self.scores[j])
        return -math.log(acc) / lam if acc > 0 else floor


@dataclass(frozen=True)
class RerollAdvice:
    """Mot buoc khuyen nghi. `action` LUON co gia tri."""

    action: Literal["PICK", "REROLL"]
    target_slot: int        # o de bam: chon no, hoac doi no
    fallback_slot: int      # o giu lai lam luoi an toan
    expected_gain: float    # loi ky vong cua viec doi, sau khi tru c
    reason: str
    threshold: float        # theta* - nguong ma diem tot nhat phai vuot de PICK
    depletion_cost: float   # c(tier, stage)
    pool_source: str
    pool_n: int
    evidence: EvidenceLevel = "uncalibrated"
    ambiguous: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "target_slot": self.target_slot,
            "fallback_slot": self.fallback_slot,
            "expected_gain": round(self.expected_gain, 4),
            "reason": self.reason,
            "threshold": round(self.threshold, 4),
            "depletion_cost": round(self.depletion_cost, 4),
            "pool_source": self.pool_source,
            "pool_n": self.pool_n,
            "evidence": self.evidence,
            "ambiguous": self.ambiguous,
        }


@dataclass(frozen=True)
class SlotView:
    """Mot o tren man hinh, gop tu cac ung vien da cham diem.

    `lo`/`hi` khac nhau khi o do la mot CAP MAP MO ma nhan dang khong tach
    duoc. Chinh sach chi hanh dong khi quyet dinh khong doi giua hai dau.
    """

    index: int
    lo: float
    hi: float
    ambiguous: bool
    name: str
    api_names: tuple[str, ...]

    def value(self, upper: bool) -> float:
        return self.hi if upper else self.lo


DEFAULT_COST_MATRIX: dict[str, dict[str, float]] = {
    "prismatic": {"stage_2": 0.08, "stage_3": 0.04, "stage_4": 0.00},
    "gold": {"stage_2": 0.01, "stage_3": 0.01, "stage_4": 0.00},
    "silver": {"stage_2": 0.01, "stage_3": 0.01, "stage_4": 0.00},
}


@dataclass(frozen=True)
class RerollTuning:
    """Tham so doc tu khoi `reroll_policy:` trong config/scoring_weights.yaml."""

    risk_lambda: float = 0.0
    tailoring_beta: float = 1.0
    burn_on_reveal: bool = True
    cost_unit: str = "sigma"
    cost_matrix: dict[str, dict[str, float]] = field(
        default_factory=lambda: {k: dict(v) for k, v in DEFAULT_COST_MATRIX.items()}
    )

    @classmethod
    def from_config(cls, config: ScoringConfig) -> "RerollTuning":
        t = config.tune("reroll_policy")
        base = cls()
        matrix = t.get("cost_matrix")
        return cls(
            risk_lambda=float(t.get("risk_lambda", base.risk_lambda)),
            tailoring_beta=float(t.get("tailoring_beta", base.tailoring_beta)),
            burn_on_reveal=bool(t.get("burn_on_reveal", base.burn_on_reveal)),
            cost_unit=str(t.get("cost_unit", base.cost_unit)),
            cost_matrix=(
                {str(k): {str(kk): float(vv) for kk, vv in v.items()} for k, v in matrix.items()}
                if isinstance(matrix, dict)
                else base.cost_matrix
            ),
        )

    def cost(self, tier: int, stage_number: int) -> float:
        """c(tier, stage) - mot phep tra bang O(1), khong to hop luc chay.

        Bang so nay la TIEN NGHIEM do nguoi dat, KHONG phai so do. Lap luan
        sinh ra hinh dang cua no nam o docs/augment-reroll/depletion-cost.md;
        no khong chay luc runtime vi tham so gamma (xac suat mot chang sau lai
        rut dung bac nay) khong quan sat doc lap duoc o Set 18.

        Chang 4-2 la chang augment CUOI: khong con chang nao de dot pool, nen
        c == 0 va vet het luot doi luon troi hon.
        """
        row = self.cost_matrix.get(TIER_NAMES.get(tier, ""), {})
        return float(row.get("stage_%d" % int(stage_number), 0.0))

    def cost_for(self, pool: PoolDistribution, stage_number: int) -> float:
        """He so trong bang, quy ve DON VI DIEM that cua pool.

        DO DUOC 2026-09-07: do lech chuan cua Score tren mot bac chi khoang
        0,05, va tich phan duoi voi mot the dan dau thuc te chi 0,002-0,009.
        Hieu bang so la tuyet doi thi gold c=0,01 va prismatic c=0,08 deu LON
        HON moi loi ich co the co - chinh sach se khong bao gio doi the, trai
        han y do da phat bieu ("gold thi c ~ 0, vet het luot").

        Doc chung nhu BOI CUA SIGMA thi dung cac so ay lai roi vao dung cho:
        gold 0,01*sigma ~ 0,0006 (van doi tru phi da gan dinh bang), prismatic
        2-1 0,08*sigma ~ 0,0045 (dung lai khi the dan dau vuot ~q90). Nho the
        bang so khong phai hieu chinh lai khi Score doi thang do - vi du khi
        so lieu that thay cho MOCK-NOT-REAL.

        `cost_unit: absolute` giu nguyen ngu nghia cu, danh cho ablation.
        """
        coefficient = self.cost(pool.tier, stage_number)
        if self.cost_unit == "absolute":
            return coefficient
        return coefficient * pool.sigma


def tailoring_weight(feature: Any, active_traits: dict[str, int], beta: float) -> float:
    """Trong so rut bai cua mot augment duoi co che tailoring.

    TFT uu tien chao augment trung trait dang bat. Coi moi the la deu nhau se
    danh gia THAP g(R) - va vi the lam may so reroll mot cach nhan tao. Mot
    tham so: `beta = 0` tra ve phan bo deu (nhanh ablation).

    Chi mo hinh phan BI DONG cua co che. Phan chu dong (don quan len bang ghe
    de bop pool tailoring) la thao tac cua nguoi choi, khong phai viec cua
    advisor - va SPEC 1.3 cam he thong tac dong vao game.
    """
    if beta == 0.0 or feature is None:
        return 1.0
    affinity = getattr(feature, "trait_affinity", None) or []
    if not affinity or not active_traits:
        return 1.0
    active = {trait_key_of(t) for t in active_traits}
    hit = any(trait_key_of(t) in active for t in affinity)
    return 1.0 + beta if hit else 1.0


def trait_key_of(trait: str) -> str:
    """Vo boc quanh `scoring.board_fit.trait_key` de tranh import vong."""
    from .scoring.board_fit import trait_key

    return trait_key(trait)


def slot_views(ranking: Any) -> list[SlotView]:
    """Gop cac entry cua `Ranking` ve tung o theo `choice_index`.

    `Ranking` co the co NHIEU HON 3 entry: mot cap map mo duoc cham diem ca
    hai nua. Gop lai thanh khoang [lo, hi] thay vi doan lay mot nua.
    """
    groups: dict[int, list[Any]] = {}
    for entry in getattr(ranking, "entries", []):
        groups.setdefault(int(entry.choice_index), []).append(entry)

    views: list[SlotView] = []
    for idx in sorted(groups):
        entries = groups[idx]
        totals = [float(e.total) for e in entries]
        views.append(
            SlotView(
                index=idx,
                lo=min(totals),
                hi=max(totals),
                ambiguous=len(entries) > 1 or any(bool(e.ambiguous) for e in entries),
                name=entries[0].name,
                api_names=tuple(e.api_name for e in entries),
            )
        )
    return views


def _best(views: Sequence[SlotView], upper: bool) -> SlotView:
    """O co diem cao nhat. Hoa thi lay chi so nho hon - de ket qua tai lap."""
    return max(views, key=lambda v: (v.value(upper), -v.index))


def decide(
    views: Sequence[SlotView],
    rerolls: RerollState,
    pool: PoolDistribution,
    cost: float,
    risk_lambda: float = 0.0,
    upper: bool = False,
) -> tuple[str, int, int, float, float]:
    """Loi quyet dinh MOT buoc. Tra (action, target, fallback, gain, threshold).

    `upper` chon dau nao cua khoang map mo duoc dung. Goi hai lan voi hai gia
    tri de biet quyet dinh co bat bien qua su map mo hay khong.
    """
    if not views:
        return "PICK", 0, 0, 0.0, 0.0

    best = max(v.value(upper) for v in views)
    token = [v for v in views if rerolls.has(v.index)]

    if not token:
        # Het luot: chi con viec chon o cao nhat.
        pick = _best(views, upper)
        rest = [v for v in views if v.index != pick.index]
        fallback = _best(rest, upper).index if rest else pick.index
        return "PICK", pick.index, fallback, 0.0, best

    # T1: doi o te nhat trong so cac o CON LUOT.
    worst = min(token, key=lambda v: (v.value(upper), v.index))
    # R = san giu lai neu doi o do. MOT cong thuc cho ca n=1 lan n>=2: bo dung
    # o muc tieu ra khoi phep max. Khi n>=2 thi R == best (nen gain >= 0, dung
    # T2); khi n==1 va o do dang la cao nhat thi R tut ve `L` - dung nhu
    # backward induction yeu cau.
    others = [v for v in views if v.index != worst.index]
    retained = max((v.value(upper) for v in others), default=NO_FLOOR)

    threshold = pool.certainty_equivalent(retained, risk_lambda) - cost
    gain = threshold - best

    # HOA THI DUNG. T2 la troi hon theo nghia YEU: khi tich phan duoi bang 0
    # (the dan dau da bang dinh pool) thi doi hay khong deu toi uu. Chon dung,
    # vi mot cu bam khong doi lay gi van ton dong ho ~30 giay va - duoi gia
    # dinh burn_on_reveal - dot them mot the khoi pool cua chang sau.
    if gain > 1e-12:
        fallback = _best(others, upper).index if others else worst.index
        return "REROLL", worst.index, fallback, gain, threshold

    pick = _best(views, upper)
    rest = [v for v in views if v.index != pick.index]
    fallback = _best(rest, upper).index if rest else pick.index
    return "PICK", pick.index, fallback, gain, threshold


def _evidence_note(pool: PoolDistribution) -> str:
    """Cau noi ro dieu gi KHONG duoc tuyen bo. Khong bao gio chan hanh dong."""
    if pool.evidence == "measured":
        return f"nguồn {pool.source}, cỡ mẫu {pool.sample_n}"
    if pool.evidence == "ordinal":
        return (
            f"⚠ nền phân bố dựa trên bảng xếp hạng chủ quan ({pool.source}), "
            "KHÔNG phải số đo"
        )
    return (
        f"⚠ thứ tự tương đối trong mô hình, chưa quy ra placement "
        f"(nguồn {pool.source}, cỡ mẫu {pool.sample_n})"
    )


def build_advice(
    views: Sequence[SlotView],
    rerolls: RerollState,
    pool: PoolDistribution,
    tuning: RerollTuning,
    stage_number: int,
) -> RerollAdvice:
    """Rap mot `RerollAdvice` hoan chinh tu loi quyet dinh.

    BAT BIEN MAP MO: neu o nao do la mot cap khong tach duoc, chay quyet dinh
    o CA HAI dau khoang. Chi hanh dong khi hai dau cho cung mot ket qua; lech
    nhau thi lui ve PICK va gan nhan - dung nhu quy tac "khong bao gio doan
    cap map mo" o augment_advisor.py.
    """
    cost = tuning.cost_for(pool, stage_number)
    lo = decide(views, rerolls, pool, cost, tuning.risk_lambda, upper=False)
    has_ambiguous = any(v.ambiguous for v in views)

    invariant = True
    if has_ambiguous:
        hi = decide(views, rerolls, pool, cost, tuning.risk_lambda, upper=True)
        invariant = lo[0] == hi[0] and lo[1] == hi[1]

    action, target, fallback, gain, threshold = lo
    by_index = {v.index: v for v in views}
    t_view = by_index.get(target)
    f_view = by_index.get(fallback)
    t_name = t_view.name if t_view else "?"
    t_val = t_view.lo if t_view else 0.0
    note = _evidence_note(pool)

    if has_ambiguous and not invariant:
        # Quyet dinh lat khi doi dau khoang -> khong du can cu de doi the.
        pick = _best(views, upper=False)
        rest = [v for v in views if v.index != pick.index]
        fb = _best(rest, upper=False).index if rest else pick.index
        return RerollAdvice(
            action="PICK",
            target_slot=pick.index,
            fallback_slot=fb,
            expected_gain=0.0,
            reason=(
                f"Chọn ô {pick.index + 1} ({pick.name}). Có cặp KHÔNG PHÂN BIỆT ĐƯỢC "
                f"và quyết định đổi/chọn lật theo cách đọc — không đổi khi chưa chắc. "
                f"[{note}]"
            ),
            threshold=threshold,
            depletion_cost=cost,
            pool_source=pool.source,
            pool_n=len(pool),
            evidence=pool.evidence,
            ambiguous=True,
        )

    if action == "REROLL":
        reason = (
            f"Đổi ô {target + 1} ({t_name}, {t_val:.3f}) — dưới ngưỡng {threshold:.3f}. "
            f"Giữ ô {fallback + 1} ({f_view.name if f_view else '?'}) làm lưới an toàn; "
            f"đổi ô kém nhất không thể làm hỏng nó. Lợi kỳ vọng +{gain:.3f}. [{note}]"
        )
    elif rerolls.n_available == 0:
        reason = (
            f"Chọn ô {target + 1} ({t_name}, {t_val:.3f}) — đã hết lượt đổi. [{note}]"
        )
    else:
        reason = (
            f"Chọn ô {target + 1} ({t_name}, {t_val:.3f}) — đạt ngưỡng {threshold:.3f}, "
            f"đổi thêm lỗ {-gain:.3f}. [{note}]"
        )
        if cost > 0:
            reason += (
                f" c={cost:.3f} (bậc {TIER_NAMES.get(pool.tier, pool.tier)}, "
                f"chặng {stage_number}): lộ thêm thẻ là đốt pool của chặng sau."
            )

    return RerollAdvice(
        action=action,
        target_slot=target,
        fallback_slot=fallback,
        expected_gain=gain,
        reason=reason,
        threshold=threshold,
        depletion_cost=cost,
        pool_source=pool.source,
        pool_n=len(pool),
        evidence=pool.evidence,
        ambiguous=has_ambiguous,
    )
