"""Bang xac suat roll va kich thuoc pool - CO GATE (SPEC 3.4.2).

DOC KY TRUOC KHI DUNG. Cac con so trong file nay CHUA DUOC XAC MINH cho
Set 18 / patch 18.1. Da scan `map22.bin.json` (72.6 MB) tren PBE:

    ShopOdds / TierOdds / ChampionTierOdds / LevelXP  ->  0 hit

Nghia la Riot khong con phat cac bang nay ra cho cong dong o dang doc duoc.
Nhung so duoi day la chuan cua CAC SET TRUOC va dang duoc lan truyen, khong
phai so do duoc cua 18.1.

Vi the module nay KHONG cho doc so mot cach im lang. Muon dung thi phai noi ro
`allow_unverified=True`, va moi ket qua tra ve deu keo theo nhan
`verified=False` de overlay bat buoc phai hien canh bao.

Ly do thiet ke: mot Economy Advisor tu tin dua tren bang xac suat sai la kieu
hong khong ai phat hien duoc - loi khuyen van nghe rat hop ly.
"""

from __future__ import annotations

from dataclasses import dataclass

VERIFIED_FOR_SET18 = False
SOURCE_NOTE = (
    "Chuan cua cac set truoc. Chua xac minh cho 18.1 - "
    "khong tim thay ShopOdds/TierOdds/LevelXP trong du lieu PBE."
)

# Level -> ti le shop theo cost (1..5).
SHOP_ODDS: dict[int, tuple[float, float, float, float, float]] = {
    1: (1.00, 0.00, 0.00, 0.00, 0.00),
    2: (1.00, 0.00, 0.00, 0.00, 0.00),
    3: (0.75, 0.25, 0.00, 0.00, 0.00),
    4: (0.55, 0.30, 0.15, 0.00, 0.00),
    5: (0.45, 0.33, 0.20, 0.02, 0.00),
    6: (0.30, 0.40, 0.25, 0.05, 0.00),
    7: (0.19, 0.30, 0.35, 0.15, 0.01),
    8: (0.18, 0.25, 0.32, 0.22, 0.03),
    9: (0.10, 0.20, 0.25, 0.30, 0.15),
    10: (0.05, 0.10, 0.20, 0.30, 0.35),
}

# Hai bang pool dang luu hanh MAU THUAN nhau. Giu ca hai, khong chon ho.
POOL_SIZE_CANDIDATES = {
    "pbe_character_wizard_default": (29, 22, 18, 11, 10),
    "community_reported": (29, 22, 16, 12, 10),
}


class UnverifiedDataError(RuntimeError):
    """Doc so chua xac minh ma khong noi ro la chap nhan rui ro."""


@dataclass(frozen=True)
class RollOdds:
    """Ti le shop cua mot level, LUON kem co xac minh."""

    level: int
    odds: tuple[float, float, float, float, float]
    verified: bool
    note: str

    def chance_of(self, cost: int) -> float:
        """Ti le xuat hien cua mot cost trong mot o shop."""
        if not 1 <= cost <= 5:
            raise ValueError(f"cost phai trong 1..5, nhan duoc {cost}")
        return self.odds[cost - 1]


def get_odds(level: int, allow_unverified: bool = False) -> RollOdds:
    """Tra ti le shop cua mot level.

    Args:
        allow_unverified: bat buoc phai True chung nao 18.1 chua duoc xac minh.
            Co nay den tu config/settings.yaml (`allow_unverified_roll_odds`),
            mac dinh false - tuc la mac dinh he thong TU CHOI doan.

    Raises:
        UnverifiedDataError: khi du lieu chua xac minh va nguoi goi chua chap
            nhan rui ro mot cach tuong minh.
    """
    if level not in SHOP_ODDS:
        raise ValueError(f"khong co bang cho level {level}")
    if not VERIFIED_FOR_SET18 and not allow_unverified:
        raise UnverifiedDataError(
            f"Ti le roll chua xac minh cho Set 18. {SOURCE_NOTE} "
            "Bat allow_unverified_roll_odds trong config/settings.yaml neu chap nhan."
        )
    return RollOdds(level, SHOP_ODDS[level], VERIFIED_FOR_SET18, SOURCE_NOTE)


def pool_size(cost: int, variant: str = "community_reported") -> tuple[int, str]:
    """Kich thuoc pool cua mot cost, kem ten bien the dang dung.

    Tra ve ca ten bien the vi hai nguon mau thuan nhau va bao cao do an phai
    noi ro dang trich dan cai nao.
    """
    if variant not in POOL_SIZE_CANDIDATES:
        raise ValueError(f"khong co bien the {variant!r}")
    if not 1 <= cost <= 5:
        raise ValueError(f"cost phai trong 1..5, nhan duoc {cost}")
    return POOL_SIZE_CANDIDATES[variant][cost - 1], variant
