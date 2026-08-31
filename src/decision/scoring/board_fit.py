"""Thanh phan w2 - BoardFit: augment co khop board dang co khong (SPEC 3.5.4).

Day la thanh phan lam nen su khac biet giua du an nay va mot bang stats tinh.
No cong hai tin hieu:

    1. TRAIT  - trait_affinity cua augment cat voi state.active_traits.
    2. CARRY  - carry_type cua augment so voi loai carry SUY RA tu item tren board.

Vi sao carry type phai suy ra tu ITEM chu khong tu tuong: du lieu CDragon
khong noi tuong nao danh AD hay AP. Nhung item thi noi: mot con dang cam hai
B.F. Sword la carry AD, khong can biet ten no la gi. Day la suy luan tu du lieu
CO THAT thay vi mot bang tra cuu tu bia ra.
"""

from __future__ import annotations

import re

from ...game_state.models import GameState
from ...knowledge.augment_features import AugmentFeature
from .types import ComponentScore, ScoringConfig, clamp01, neutral

NAME = "board_fit"

# Component -> loai carry ma no phuc vu. Ban do nay la kien thuc TFT on dinh
# qua nhieu set (BF Sword luon la AD), khong phai so lieu can verify moi patch.
COMPONENT_CARRY_TYPE: dict[str, str] = {
    "BFSword": "AD",
    "RecurveBow": "AD",
    "NeedlesslyLargeRod": "AP",
    "TearOfTheGoddess": "AP",
    "ChainVest": "tank",
    "NegatronCloak": "tank",
    "GiantsBelt": "tank",
}

# Nhan tieng Anh/tieng Viet thuong gap tren item da ghep, dung de doan loai
# carry khi chi doc duoc ten item hoan chinh.
COMPLETED_ITEM_HINTS: dict[str, list[str]] = {
    "AD": [r"blade", r"bow", r"sword", r"kiem", r"cung", r"deathblade", r"bloodthirster"],
    "AP": [r"rabadon", r"archangel", r"jeweled", r"gauntlet", r"phap", r"trung"],
    "tank": [r"warmog", r"bramble", r"dragon", r"sunfire", r"giap", r"khien"],
}


def trait_key(trait: str) -> str:
    """Chuan hoa dinh danh trait de so sanh duoc giua cac cach viet.

    `DA_18_Ravager`, `DA_Ravager18`, `Ravager` va `ravager` deu phai ve mot
    khoa. Reader doc trait tu overlay se cho ra ten hien thi, con feature table
    giu apiName - hai dau khac nhau nen phai chuan hoa truoc khi cat.
    """
    key = re.sub(r"^DA[_-]?", "", str(trait), flags=re.I)
    key = re.sub(r"\d+", "", key)
    return re.sub(r"[^a-z]", "", key.lower())


def infer_carry_type(state: GameState) -> tuple[str, str]:
    """Suy ra loai carry cua board tu item dang mang.

    Returns:
        (loai carry, bang chung dang chuoi). Loai la "unknown" khi board chua
        co item nao - va "unknown" phai duoc doi xu nhu THIEU TIN HIEU, khong
        phai nhu mot loai carry that.
    """
    votes: dict[str, int] = {"AD": 0, "AP": 0, "tank": 0}
    evidence: list[str] = []

    for champ in state.carries:
        for item in champ.items:
            direct = COMPONENT_CARRY_TYPE.get(item)
            if direct:
                votes[direct] += 1
                evidence.append(item)
                continue
            for carry_type, hints in COMPLETED_ITEM_HINTS.items():
                if any(re.search(h, item, re.I) for h in hints):
                    votes[carry_type] += 1
                    evidence.append(item)
                    break

    best = max(votes.values())
    if best == 0:
        return "unknown", ""
    winners = [k for k, v in votes.items() if v == best]
    if len(winners) > 1:
        return "unknown", ", ".join(evidence)
    return winners[0], ", ".join(evidence)


class BoardFitScorer:
    """Cham diem do khop giua augment va board hien tai."""

    def __init__(self, config: ScoringConfig) -> None:
        tune = config.tune(NAME)
        self.trait_weight = float(tune.get("trait_weight", 0.6))
        self.carry_weight = float(tune.get("carry_weight", 0.4))
        self.min_units = int(tune.get("active_trait_min_units", 2))

    def __call__(
        self, api_name: str, feature: AugmentFeature | None, state: GameState
    ) -> ComponentScore:
        if feature is None:
            return neutral(NAME, "Không có dữ liệu đặc trưng cho augment này")

        trait_score, trait_reason, trait_detail = self._trait_part(feature, state)
        carry_score, carry_reason, carry_detail = self._carry_part(feature, state)

        total = self.trait_weight + self.carry_weight
        score = (
            (trait_score * self.trait_weight + carry_score * self.carry_weight) / total
            if total
            else 0.5
        )

        reasons = [r for r in (trait_reason, carry_reason) if r]
        return ComponentScore(
            NAME,
            clamp01(score),
            " · ".join(reasons),
            {**trait_detail, **carry_detail},
        )

    # -- hai nua cua diem --------------------------------------------------

    def _trait_part(
        self, feature: AugmentFeature, state: GameState
    ) -> tuple[float, str, dict]:
        if not feature.trait_affinity:
            return 0.5, "Không gắn tộc/hệ nào — không có tín hiệu trait", {}

        active = {trait_key(k): v for k, v in state.active_traits.items()}
        hits: list[tuple[str, int]] = []
        for trait in feature.trait_affinity:
            units = active.get(trait_key(trait), 0)
            hits.append((trait, units))

        best_units = max((u for _, u in hits), default=0)
        best_trait = next((t for t, u in hits if u == best_units), "")

        if best_units >= self.min_units:
            score = 1.0
            reason = f"Khớp tộc/hệ đang chạy: {best_trait} ({best_units} đơn vị trên sân)"
        elif best_units == 1:
            score = 0.65
            reason = f"Mới có 1 đơn vị {best_trait} — cần thêm để phát huy"
        else:
            score = 0.15
            reason = f"Board chưa có đơn vị nào thuộc {feature.trait_affinity[0]}"

        return score, reason, {"trait_hits": hits}

    def _carry_part(
        self, feature: AugmentFeature, state: GameState
    ) -> tuple[float, str, dict]:
        board_type, evidence = infer_carry_type(state)

        if feature.carry_type == "none":
            return 0.5, "", {"board_carry_type": board_type}
        if board_type == "unknown":
            return (
                0.5,
                f"Board chưa đủ trang bị để biết đang theo hướng {feature.carry_type}",
                {"board_carry_type": board_type},
            )
        if board_type == feature.carry_type:
            return (
                1.0,
                f"Đúng hướng carry {board_type} của board (căn cứ: {evidence})",
                {"board_carry_type": board_type, "evidence": evidence},
            )
        return (
            0.2,
            f"Augment thiên {feature.carry_type} nhưng board đang đi {board_type}",
            {"board_carry_type": board_type, "evidence": evidence},
        )
