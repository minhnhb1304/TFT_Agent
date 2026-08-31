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

    def __call__(
        self, api_name: str, feature: AugmentFeature | None, state: GameState
    ) -> ComponentScore:
        stats = self.provider.get(api_name)
        if stats is None:
            return neutral(
                NAME,
                f"Chưa có số liệu ({getattr(self.provider, 'name', 'unknown')}) — điểm trung tính",
                source=getattr(self.provider, "name", "unknown"),
                sample_n=0,
            )

        # Placement thap = tot, nen dao chieu khi chuan hoa.
        span = self.worst_place - self.best_place
        raw = clamp01((self.worst_place - stats.avg_place) / span) if span else 0.5

        # Co mau nho thi keo diem ve trung tinh thay vi tin han vao no. Day la
        # shrinkage co chu y: mot augment 12 tran khong duoc phep dieu khien
        # xep hang chi vi tinh co dep so.
        trust = clamp01(stats.sample_n / self.min_sample_n) if self.min_sample_n else 1.0
        score = 0.5 + (raw - 0.5) * trust

        evidence = "" if stats.is_evidence else " ⚠ cỡ mẫu nhỏ"
        reason = (
            f"Vị trí trung bình {stats.avg_place:.2f} "
            f"(n={stats.sample_n}, nguồn: {stats.source}){evidence}"
        )
        return ComponentScore(
            NAME,
            score,
            reason,
            {
                "avg_place": stats.avg_place,
                "top4_rate": stats.top4_rate,
                "sample_n": stats.sample_n,
                "source": stats.source,
                "trust": round(trust, 3),
            },
        )
