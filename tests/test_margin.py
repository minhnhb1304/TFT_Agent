"""Test câu so sánh #1 vs #2 (bước A2, mốc M4).

Buổi test 2026-09-16: panel nói "hơn lựa chọn kế +0.12" nhưng không nói **hơn
ở đâu**, nên ba cột lý do đọc xong vẫn như nhau. Các test ở đây khoá lại hai
điều: phép tách phải **cộng đúng** về `delta` đang hiện, và câu nói ra phải
nêu cả chiều **thua thiệt** khi có.
"""

from __future__ import annotations

import pytest

from src.decision import margin
from src.decision.augment_advisor import AugmentAdvisor
from src.decision.scoring.types import ComponentScore, ScoringConfig
from src.game_state.models import GameState
from src.knowledge.augment_features import AugmentFeature, FeatureTable

ECON = "DA_Econ"
COMBAT = "DA_Combat"


class FakeEntry:
    """Một dòng xếp hạng tối giản — test phép tách, không test scorer."""

    def __init__(self, api_name: str, total: float, components: dict[str, ComponentScore]):
        self.api_name = api_name
        self.name = api_name
        self.total = total
        self.components = components


class FakeRanking:
    def __init__(self, entries, weights):
        self.entries = entries
        self.weights = weights


def comp(name: str, score: float, reason: str = "") -> ComponentScore:
    return ComponentScore(name, score, reason)


def fake(weights: dict[str, float], first: dict[str, float], second: dict[str, float],
         reasons: dict[str, str] | None = None) -> FakeRanking:
    reasons = reasons or {}
    c1 = {k: comp(k, v, reasons.get(k, "")) for k, v in first.items()}
    c2 = {k: comp(k, v) for k, v in second.items()}
    t1 = sum(weights[k] * v for k, v in first.items())
    t2 = sum(weights[k] * v for k, v in second.items())
    return FakeRanking([FakeEntry("A", t1, c1), FakeEntry("B", t2, c2)], weights)


# -- phep tach ------------------------------------------------------------

def test_parts_cong_lai_bang_dung_gap():
    """Bất biến cốt lõi: `total` là tổ hợp tuyến tính nên các phần phải khớp.

    Nếu một ngày `score_one` không còn cộng tuyến tính thì test này đỏ — đó
    đúng là lúc `compare()` phải viết lại, không phải lúc bỏ qua.
    """
    weights = {"base": 0.5, "board_fit": 0.3, "tempo_fit": 0.2}
    ranking = fake(weights, {"base": 0.8, "board_fit": 0.9, "tempo_fit": 0.2},
                            {"base": 0.6, "board_fit": 0.4, "tempo_fit": 0.7})
    m = margin.compare(ranking)

    assert sum(m.parts.values()) == pytest.approx(m.gap, abs=1e-4)


def test_bo_qua_phan_dong_gop_qua_nho():
    weights = {"base": 0.5, "board_fit": 0.5}
    ranking = fake(weights, {"base": 0.500, "board_fit": 0.9},
                            {"base": 0.501, "board_fit": 0.4})
    m = margin.compare(ranking)

    assert "base" not in m.parts
    assert "board_fit" in m.parts


def test_chua_du_hai_the_thi_khong_so_sanh():
    weights = {"base": 1.0}
    ranking = FakeRanking([FakeEntry("A", 0.6, {"base": comp("base", 0.6)})], weights)

    assert margin.compare(ranking) is None
    assert margin.explain(None, ranking) == ""


def test_leading_va_trailing_doc_dung_hai_chieu():
    weights = {"base": 0.5, "tempo_fit": 0.5}
    ranking = fake(weights, {"base": 0.9, "tempo_fit": 0.2},
                            {"base": 0.3, "tempo_fit": 0.8})
    m = margin.compare(ranking)

    assert m.leading[0] == "base"
    assert m.trailing[0] == "tempo_fit"


# -- cau noi --------------------------------------------------------------

def test_cau_neu_ten_thanh_phan_va_so():
    weights = {"base": 0.5, "board_fit": 0.5}
    ranking = fake(weights, {"base": 0.5, "board_fit": 0.9},
                            {"base": 0.5, "board_fit": 0.5},
                   reasons={"board_fit": "Khớp tộc/hệ đang chạy: Ravager (3 đơn vị trên sân)"})
    text = margin.explain(margin.compare(ranking), ranking)

    assert "khớp bàn cờ" in text
    assert "+0.20" in text
    assert "Ravager" in text


def test_cau_noi_ca_chieu_thua_thiet():
    """Dẫn chung cuộc mà vẫn kém một thành phần — phải nói ra."""
    weights = {"base": 0.5, "tempo_fit": 0.5}
    ranking = fake(weights, {"base": 1.0, "tempo_fit": 0.2},
                            {"base": 0.3, "tempo_fit": 0.8})
    text = margin.explain(margin.compare(ranking), ranking)

    assert "dù kém nhịp độ" in text


def test_khong_kem_o_dau_thi_khong_them_menh_de_thua():
    weights = {"base": 0.5, "board_fit": 0.5}
    ranking = fake(weights, {"base": 0.9, "board_fit": 0.9},
                            {"base": 0.4, "board_fit": 0.4})
    text = margin.explain(margin.compare(ranking), ranking)

    assert "dù kém" not in text


def test_sat_nhau_thi_im_lang():
    """Không thành phần nào vượt ngưỡng → không cố tỏ ra biết vì sao."""
    weights = {"base": 0.5, "board_fit": 0.5}
    ranking = fake(weights, {"base": 0.500, "board_fit": 0.502},
                            {"base": 0.501, "board_fit": 0.500})

    assert margin.explain(margin.compare(ranking), ranking) == ""


def test_thanh_phan_trung_tinh_khong_gop_chi_tiet():
    """Điểm trung tính = thiếu dữ liệu; câu của nó không phải một lý do."""
    weights = {"base": 1.0}
    ranking = FakeRanking(
        [FakeEntry("A", 0.5, {"base": comp("base", 0.5, "Không có dữ liệu")}),
         FakeEntry("B", 0.2, {"base": comp("base", 0.2, "Bậc C")})],
        weights,
    )
    m = margin.compare(ranking)

    assert margin._detail(ranking, "A", "base") == ""
    assert "Không có dữ liệu" not in margin.explain(m, ranking)


# -- chay that tren advisor ----------------------------------------------

def test_chay_tren_ranking_that():
    """Đầu ra của `AugmentAdvisor.rank` phải đi thẳng vào được, không cần bọc."""
    features = FeatureTable({
        ECON: AugmentFeature(api_name=ECON, name="Lõi Tiền", tier=2, category="econ",
                             econ_value=3, tempo="scaling"),
        COMBAT: AugmentFeature(api_name=COMBAT, name="Lõi Đánh", tier=2, category="combat",
                               econ_value=0, tempo="immediate"),
    })
    advisor = AugmentAdvisor(features, config=ScoringConfig.default())
    ranking = advisor.rank([ECON, COMBAT],
                           GameState(stage="3-2", gold=5, level=6, hp=70, streak=-3))
    m = margin.compare(ranking)

    assert m is not None
    assert sum(m.parts.values()) == pytest.approx(m.gap, abs=1e-4)
    assert margin.explain(m, ranking)


# -- xuat xu phai noi len, dung mot lan -----------------------------------

def test_xuat_xu_noi_len_dai_trang_thai_dung_mot_lan():
    """Thay cho bất biến cũ "reason luôn mang xuất xứ".

    Mệnh đề xuất xứ rời khỏi `reason` để hết lặp (A3), nên nó **phải** nổi
    lên ở dải trạng thái — nếu không thì việc tách ra chính là xoá đi một
    rào chắn trung thực, không phải dọn câu chữ.
    """
    from src.replay.viewmodel import _sources

    weights = {"base": 1.0}
    src = "expert-tierlist:TFT Academy"
    entries = [
        FakeEntry("A", 0.63, {"base": ComponentScore("base", 0.63, "Bậc S",
                                                     {"caveat": f"bậc lấy từ {src}"})}),
        FakeEntry("B", 0.37, {"base": ComponentScore("base", 0.37, "Bậc B",
                                                     {"caveat": f"bậc lấy từ {src}"})}),
    ]
    sources = _sources(FakeRanking(entries, weights))

    assert sources == [f"bậc lấy từ {src}"], "hai thẻ cùng nguồn -> nói đúng một lần"


def test_cli_explain_van_in_xuat_xu():
    """Đường headless (CLI, log) cũng không được mất rào chắn đó."""
    features = FeatureTable({
        ECON: AugmentFeature(api_name=ECON, name="Lõi Tiền", tier=2, category="econ",
                             econ_value=3, tempo="scaling"),
        COMBAT: AugmentFeature(api_name=COMBAT, name="Lõi Đánh", tier=2, category="combat",
                               econ_value=0, tempo="immediate"),
    })
    advisor = AugmentAdvisor(features, config=ScoringConfig.default())
    text = advisor.explain(advisor.rank([ECON, COMBAT], GameState(stage="3-2")))

    assert "không có lõi này" in text, "NullProvider vẫn phải khai ra là chưa tra được"
    assert text.count("không có lõi này") == 1, "in một lần, không lặp theo từng thẻ"
