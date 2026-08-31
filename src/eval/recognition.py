"""SPEC 12.1 - do chinh xac nhan dang (CV/OCR).

Harness nay xong TRUOC khi co frame that, va do la co y: khi Track B bat dau
sinh anh, so lieu ra ngay thay vi phai viet code phan tich duoi suc ep deadline.

BA DIEU NHAY CAM PHAI LAM DUNG:

1. Bao cao THEO TUNG LOAI THUC THE (augment, champion, item, gold, level, hp,
   stage). Gop chung lai se giau mat viec augment - thu quan trong nhat - co
   the dang te hon han cac truong so de doc.

2. Bao cao RIENG 4 cap augment map mo. Chung khong the phan biet duoc bang bat
   ky phuong phap nao; tron vao chi so chung se lam mot GIOI HAN DU LIEU trong
   giong nhu mot LOI MODEL.

3. Latency do khi GAME DANG CHAY. Moi con so latency san co deu do tren may
   ranh, va vi the deu la so lac quan.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence


@dataclass
class Prediction:
    """Mot du doan doi chieu voi nhan tay."""

    entity: str            # "augment" | "champion" | "item" | "gold" | ...
    predicted: str | None
    truth: str | None
    latency_ms: float | None = None
    ambiguous_pair: bool = False


@dataclass
class EntityMetrics:
    """P/R/F1 cua mot loai thuc the."""

    entity: str
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def support(self) -> int:
        return self.tp + self.fn

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity": self.entity,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "support": self.support,
            "tp": self.tp, "fp": self.fp, "fn": self.fn, "tn": self.tn,
        }


def percentile(values: Sequence[float], q: float) -> float:
    """Phan vi bang noi suy tuyen tinh. Day rong -> 0.0."""
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * q
    low = int(pos)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (pos - low)


@dataclass
class RecognitionReport:
    """Bao cao 12.1 day du."""

    per_entity: dict[str, EntityMetrics] = field(default_factory=dict)
    ambiguous: EntityMetrics = field(default_factory=lambda: EntityMetrics("augment/map-mo"))
    latencies: dict[str, list[float]] = field(default_factory=dict)
    n: int = 0

    def latency_stats(self, entity: str) -> dict[str, float]:
        values = self.latencies.get(entity, [])
        return {
            "p50": round(percentile(values, 0.50), 2),
            "p95": round(percentile(values, 0.95), 2),
            "n": len(values),
        }

    def table(self) -> str:
        head = f"{'Thuc the':<20}{'P':>8}{'R':>8}{'F1':>8}{'n':>7}{'p50 ms':>10}{'p95 ms':>10}"
        lines = [head, "-" * len(head)]
        for entity in sorted(self.per_entity):
            m = self.per_entity[entity]
            lat = self.latency_stats(entity)
            lines.append(
                f"{entity:<20}{m.precision:>8.3f}{m.recall:>8.3f}{m.f1:>8.3f}"
                f"{m.support:>7}{lat['p50']:>10.1f}{lat['p95']:>10.1f}"
            )
        if self.ambiguous.support:
            m = self.ambiguous
            lines.append("")
            lines.append(
                f"{'4 cap map mo':<20}{m.precision:>8.3f}{m.recall:>8.3f}{m.f1:>8.3f}"
                f"{m.support:>7}"
            )
            lines.append(
                "  ^ day la GIOI HAN DU LIEU (trung ca ten lan icon), khong phai loi model."
            )
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "n": self.n,
            "per_entity": {k: v.to_dict() for k, v in self.per_entity.items()},
            "ambiguous_pairs": self.ambiguous.to_dict(),
            "latency": {k: self.latency_stats(k) for k in self.latencies},
        }


def evaluate(predictions: Iterable[Prediction]) -> RecognitionReport:
    """Doi chieu du doan voi nhan tay, tra ve bao cao 12.1.

    Quy uoc dem:
        truth co, predicted dung   -> TP
        truth co, predicted sai    -> FP + FN (mot lan doc sai vua la bo sot
                                      nhan dung vua la bao sai nhan khac)
        truth co, predicted None   -> FN
        truth None, predicted co   -> FP
        ca hai None                -> TN
    """
    report = RecognitionReport()

    for p in predictions:
        report.n += 1
        metrics = report.per_entity.setdefault(p.entity, EntityMetrics(p.entity))
        targets = [metrics] + ([report.ambiguous] if p.ambiguous_pair else [])

        for m in targets:
            if p.truth is None and p.predicted is None:
                m.tn += 1
            elif p.truth is None:
                m.fp += 1
            elif p.predicted is None:
                m.fn += 1
            elif p.predicted == p.truth:
                m.tp += 1
            else:
                m.fp += 1
                m.fn += 1

        if p.latency_ms is not None:
            report.latencies.setdefault(p.entity, []).append(p.latency_ms)

    return report
