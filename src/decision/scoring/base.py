"""Thanh phan w1 - Base: so lieu thong ke tinh (SPEC 3.5.4).

Day la thanh phan DUY NHAT khong nhin vao board. Chinh vi the no la baseline
cua ablation study: cau hinh "chi w1" tuong duong mot bang stats tinh, va delta
giua no voi mo hinh day du la cau tra loi dinh luong cho cau hoi "vi sao phai
lam advisor dong".
"""

from __future__ import annotations

from ...game_state.models import GameState
from ...knowledge.augment_features import AugmentFeature
from ...knowledge.stats_provider import AugmentStatsProvider
from .types import ComponentScore, ScoringConfig, clamp01, neutral

NAME = "base"


class BaseScorer:
    """Chuan hoa avg placement thanh diem [0, 1], co xet co mau."""

    def __init__(self, provider: AugmentStatsProvider, config: ScoringConfig) -> None:
        self.provider = provider
        tune = config.tune(NAME)
        self.best_place = float(tune.get("best_place", 3.5))
        self.worst_place = float(tune.get("worst_place", 5.0))
        self.min_sample_n = int(tune.get("min_sample_n", 200))
        # Muc tin toi da cho mot tin hieu THU TU (bang tier do nguoi xep).
        # Khong the suy tu co mau vi bang tier khong co co mau - day la mot
        # phan xet doan, va no phai nam trong file config de ablation thay
        # duoc no dang dong gop bao nhieu.
        self.ordinal_trust = clamp01(float(tune.get("ordinal_trust", 0.65)))
        # Diem cho loi chua biet / chua co data/tier list chinh xac.
        # Dat 0.35 (duoi bac B = 0.370) de phat rui ro thieu thong tin, tao dong co reroll.
        self.unknown_score = clamp01(float(tune.get("unknown_score", 0.35)))

    def __call__(
        self, api_name: str, feature: AugmentFeature | None, state: GameState
    ) -> ComponentScore:
        stats = self.provider.get(api_name)
        if stats is None:
            return ComponentScore(
                NAME,
                self.unknown_score,
                f"Chưa có data/tier list chính xác ({getattr(self.provider, 'name', 'unknown')}) — hạ điểm xuống {self.unknown_score:.2f}",
                {
                    "avg_place": None,
                    "top4_rate": 0.0,
                    "sample_n": 0,
                    "source": getattr(self.provider, "name", "unknown"),
                    "tier": "",
                    "is_ordinal": False,
                    "trust": 0.0,
                    "is_unknown": True,
                },
            )

        # Placement thap = tot, nen dao chieu khi chuan hoa.
        span = self.worst_place - self.best_place
        raw = clamp01((self.worst_place - stats.avg_place) / span) if span else 0.5

        if stats.is_ordinal:
            # Bang tier khong co co mau, nen cong thuc shrinkage theo n khong
            # ap dung duoc: no se cho trust = 0 va tin hieu bien mat hoan toan.
            # Thay bang mot tran co dinh, doc tu config. Ly do phai hien thi
            # khac han: day la THU TU do nguoi xep, khong phai so do duoc.
            trust = self.ordinal_trust
            reason = (
                f"Bậc {stats.tier} theo bảng tier của người chơi "
                f"({stats.source}) — xếp hạng chủ quan, KHÔNG phải số đo"
            )
        else:
            # Co mau nho thi keo diem ve trung tinh thay vi tin han vao no. Day la
            # shrinkage co chu y: mot augment 12 tran khong duoc phep dieu khien
            # xep hang chi vi tinh co dep so.
            trust = clamp01(stats.sample_n / self.min_sample_n) if self.min_sample_n else 1.0
            evidence = "" if stats.is_evidence else " ⚠ cỡ mẫu nhỏ"
            reason = (
                f"Vị trí trung bình {stats.avg_place:.2f} "
                f"(n={stats.sample_n}, nguồn: {stats.source}){evidence}"
            )

        score = 0.5 + (raw - 0.5) * trust
        return ComponentScore(
            NAME,
            score,
            reason,
            {
                "avg_place": stats.avg_place,
                "top4_rate": stats.top4_rate,
                "sample_n": stats.sample_n,
                "source": stats.source,
                "tier": stats.tier,
                "is_ordinal": stats.is_ordinal,
                "trust": round(trust, 3),
            },
        )
