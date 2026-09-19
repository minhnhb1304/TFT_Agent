"""Vi sao lua chon dau bang hon lua chon ke? (buoc A2, moc M4)

Panel da noi "hon lua chon ke +0.12" tu truoc, nhung khong noi HON O DAU.
Buoi test 2026-09-16: ba cot ly do gan giong nhau, nguoi choi doc het van
khong biet vi sao #1 lai la #1 - va do la cau hoi duy nhat ho thuc su hoi.

`total = sum(w_c * s_c)` (xem `AugmentAdvisor.score_one`) nen chenh lech giua
hai the tach duoc CHINH XAC theo tung thanh phan:

    gap = total_1 - total_2 = sum_c  w_c * (s1_c - s2_c)

Day khong phai uoc luong ma la mot dang thuc: tong cac phan bang dung con so
`delta` panel dang hien. Neu mot ngay nao do `total` khong con la to hop
tuyen tinh nua thi `compare()` phai doi theo, va `test_margin.py` se do.

Danh doi phai noi ca hai chieu. Mot the co the DAN chung cuoc ma van KEM o
mot thanh phan; im lang ve chuyen do la cach nhanh nhat de mat tin cay, vi
nguoi choi nhin bang diem thanh phan la thay ngay.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Ten hien cho nguoi choi doc. Khoa trung voi `ScoringConfig.COMPONENTS`;
# thanh phan la nao khong co trong day thi dung nguyen khoa - thieu mot dong
# o day khong duoc phep lam mat mot cau giai thich.
LABELS = {
    "base": "bảng tier",
    "board_fit": "khớp bàn cờ",
    "econ_fit": "kinh tế",
    "item_fit": "trang bị",
    "tempo_fit": "nhịp độ",
}

# Duoi nguong nay thi phan dong gop khong dang goi ten. Cung thang do voi
# `state_effect.min_delta`: sd(Score) tren mot bac chi ~0.05.
MIN_PART = 0.01
MIN_TRADE = 0.02


@dataclass
class Margin:
    """Chenh lech giua #1 va #2, da tach ve tung thanh phan cham diem."""

    winner: str = ""                                   # apiName cua #1
    runner_up: str = ""                                # apiName cua #2
    gap: float = 0.0
    parts: dict[str, float] = field(default_factory=dict)   # component -> w*(s1-s2)

    @property
    def leading(self) -> tuple[str, float] | None:
        """Thanh phan keo #1 len nhieu nhat, hoac None neu khong co phan duong."""
        gains = {k: v for k, v in self.parts.items() if v > 0}
        if not gains:
            return None
        key = max(gains, key=lambda k: gains[k])
        return key, gains[key]

    @property
    def trailing(self) -> tuple[str, float] | None:
        """Thanh phan ma #1 KEM #2 nhieu nhat, hoac None neu khong kem o dau."""
        losses = {k: v for k, v in self.parts.items() if v < 0}
        if not losses:
            return None
        key = min(losses, key=lambda k: losses[k])
        return key, losses[key]


def compare(ranking: Any) -> Margin | None:
    """Tach chenh lech #1 vs #2 cua mot `Ranking`. None neu chua co du hai the."""
    entries = list(getattr(ranking, "entries", []) or [])
    if len(entries) < 2:
        return None
    first, second = entries[0], entries[1]
    weights = dict(getattr(ranking, "weights", {}) or {})

    parts: dict[str, float] = {}
    for name, comp in first.components.items():
        other = second.components.get(name)
        if other is None:
            continue
        delta = weights.get(name, 0.0) * (comp.score - other.score)
        if abs(delta) >= MIN_PART:
            parts[name] = round(delta, 4)

    return Margin(
        winner=first.api_name,
        runner_up=second.api_name,
        gap=round(first.total - second.total, 4),
        parts=parts,
    )


def explain(margin: Margin | None, ranking: Any, *, min_trade: float = MIN_TRADE) -> str:
    """Mot cau cho nguoi choi, hoac chuoi rong khi khong noi duoc gi that.

    Rong trong ba truong hop, va ca ba deu co chu y: chua du hai the; hai the
    sat nhau den muc khong thanh phan nao vuot `MIN_PART` (noi "hon nhung
    khong ro hon o dau" thi to ra biet nhieu hon thuc te); va khi #1 khong
    dan o bat ky thanh phan nao - luc do chenh lech den tu nhieu manh vun,
    khong co mot ly do nao de goi ten.
    """
    if margin is None or not margin.parts:
        return ""
    lead = margin.leading
    if lead is None:
        return ""

    name, amount = lead
    text = f"Hơn lựa chọn kế chủ yếu nhờ {LABELS.get(name, name)} (+{amount:.2f})"

    detail = _detail(ranking, margin.winner, name)
    if detail:
        text += f": {detail}"

    trade = margin.trailing
    if trade is not None and abs(trade[1]) >= min_trade:
        text += f" — dù kém {LABELS.get(trade[0], trade[0])} ({abs(trade[1]):.2f})"
    return text


def _detail(ranking: Any, api_name: str, component: str) -> str:
    """Manh dau cua `reason` thanh phan do - cau da co san so that trong no.

    Cat o dau " · " vi cac scorer noi nhieu y vao mot `reason`; o day chi can
    y DAU, phan con lai van hien nguyen o cot cua the.
    """
    entry = next((e for e in getattr(ranking, "entries", []) if e.api_name == api_name), None)
    comp = entry.components.get(component) if entry is not None else None
    if comp is None or comp.is_neutral or not comp.reason:
        return ""
    return comp.reason.split(" · ")[0].strip()
