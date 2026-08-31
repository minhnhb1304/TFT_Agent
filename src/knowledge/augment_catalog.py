"""Catalog augment Set 18 - giai tier, chuan hoa ten, khop ket qua OCR.

Day la noi research/vision-stack/augments.md tro thanh code. Moi con so trong
module nay deu do duoc tu du lieu that ngay 2026-08-28 va duoc test khoa lai.

HAI QUY TAC QUAN TRONG NHAT
---------------------------
1. TEN LA CHINH, ICON LA PHU.
   Icon art bi dung lai giua cac tier: 19/254 duong dan icon MAU THUAN voi
   chinh ten cua augment (vd DA_BronzeForLifeII co icon bronzeforlife_iii.tex).
   Vi vay ladder giai tier phai kiem tra apiName/name TRUOC. Dao thu tu lai
   thi 19 augment bi gan sai tier.

2. CO 4 CAP KHONG THE PHAN BIET - PHAI CHAP NHAN, KHONG DUOC DOAN.
   Bon cap augment trung CA ten hien thi LAN icon. Khong phuong phap nhan dang
   nao tach duoc chung vi khong con tin hieu nao de doc. Ba trong bon cap chi
   khac nhau o TIER - dung thu ma advisor can phan biet nhat.
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable

# --- Ladder giai tier: uu tien TIN HIEU DANH TINH truoc ---------------------
RE_API_ROMAN = re.compile(r"(I{1,3})$")
RE_NAME_ROMAN = re.compile(r"\b(I{1,3})$")
RE_PLACEHOLDER = re.compile(r"missing-t(\d)\.tex$")
RE_ICON_ROMAN = re.compile(r"[-_](i{1,3})\.tex$")  # CA underscore LAN hyphen
RE_ICON_DIGIT = re.compile(r"(\d)\.tex$")

# Ky tu D-gach-ngang tieng Viet, chuan hoa ve 'd'.
_D_STROKE = {ord("đ"): "d", ord("Đ"): "d"}


def normalize(text: str) -> str:
    """Chuan hoa de so sanh: bo dau, d-gach -> d, lowercase.

    Do duoc: bo TOAN BO dau tieng Viet van cho 0 collision tren 36 trait va
    249 ten augment. Dieu kien duy nhat la phai normalize CA HAI PHIA truoc
    khi so sanh - so ket qua OCR tho voi ten chua normalize thi moi vo.
    """
    decomposed = unicodedata.normalize("NFD", str(text))
    stripped = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return stripped.translate(_D_STROKE).lower().strip()


def strip_tier_token(name: str) -> str:
    """Bo hau to tier khoi ten, tra ve phan GOC de fuzzy match.

    Vi sao phai tach truoc khi fuzzy match: cac cap cung goc khac tier co do
    tuong dong rat cao (vd 0.97-0.98). Fuzzy match thang tren ten day du se
    lan lon dung thu can phan biet nhat.
    """
    stem = str(name).strip()
    stem = re.sub(r"\+{1,2}$", "", stem).strip()
    stem = re.sub(r"\s+I{1,3}$", "", stem).strip()
    return stem


@dataclass(frozen=True)
class Augment:
    """Mot augment Set 18 kem tier da giai va nguon tin hieu tier."""

    api_name: str
    name: str
    desc: str
    icon: str
    tier: int
    tier_source: str
    effects: dict[str, Any] = field(default_factory=dict)
    associated_traits: tuple[str, ...] = ()

    @property
    def stem(self) -> str:
        """Ten da bo token tier."""
        return strip_tier_token(self.name)


def resolve_tier(api_name: str, name: str, icon: str) -> tuple[int, str]:
    """Giai tier bang ladder 4 buoc, uu tien tin hieu danh tinh.

    Do duoc tren 254 augment Set 18 (2026-08-28):
        buoc 1 apiName/name  ->  75
        buoc 2 missing-tN    ->  28
        buoc 3 icon roman    -> 135
        buoc 4 icon digit    ->  16
        tong                 -> 254, khong con cai nao chua giai

    THU TU LA THIET YEU. Dat cac buoc icon len truoc van giai duoc du 254
    nhung gan SAI tier cho 19 cai.

    Returns:
        (tier, ten_buoc_da_giai) - tra ca nguon de audit va debug duoc.
    """
    icon_l = str(icon).lower()

    # Buoc 1 - tin hieu danh tinh: chinh augment tu khai bao tier cua no.
    if api_name.endswith("PlusPlus"):
        return 3, "apiName/name token"
    if api_name.endswith("Plus"):
        return 2, "apiName/name token"
    m = RE_API_ROMAN.search(api_name)
    if m:
        return len(m.group(1)), "apiName/name token"
    if name.endswith("++"):
        return 3, "apiName/name token"
    if name.endswith("+"):
        return 2, "apiName/name token"
    m = RE_NAME_ROMAN.search(name)
    if m:
        return len(m.group(1)), "apiName/name token"

    # Buoc 2 - placeholder ma hoa tier ngay trong ten file.
    # Nghich ly: chinh cac placeholder lam template matching bat kha thi lai la
    # mot trong nhung tin hieu tier dang tin cay nhat.
    m = RE_PLACEHOLDER.search(icon_l)
    if m:
        return int(m.group(1)), "missing-tN"

    # Buoc 3 - hau to la ma trong duong dan icon. CA _ LAN - deu phai bat.
    m = RE_ICON_ROMAN.search(icon_l)
    if m:
        return len(m.group(1)), "icon roman"

    # Buoc 4 - chu so cuoi duong dan icon.
    m = RE_ICON_DIGIT.search(icon_l)
    if m:
        return int(m.group(1)), "icon digit"

    return 0, "UNRESOLVED"


@dataclass
class MatchResult:
    """Ket qua khop mot chuoi (thuong tu OCR) vao catalog.

    Attributes:
        candidates: cac augment khop. Nhieu hon 1 nghia la MAP MO that su,
            khong phai loi - xem AMBIGUOUS o docstring dau module.
        ambiguous: True khi khong the tach bang bat ky phuong phap nao.
        matched_on: mo ta cach khop, de debug.
    """

    candidates: list[Augment]
    ambiguous: bool
    matched_on: str

    @property
    def resolved(self) -> Augment | None:
        """Tra augment duy nhat neu khong map mo, nguoc lai None."""
        return self.candidates[0] if len(self.candidates) == 1 else None


class AugmentCatalog:
    """Catalog augment cho mot ngon ngu, da giai tier va danh dau cap map mo."""

    def __init__(self, locale_data: dict[str, Any]) -> None:
        """Dung catalog tu du lieu locale CommunityDragon da nap.

        Args:
            locale_data: dict co key "items" (danh sach item cua cdragon).
        """
        self.augments: list[Augment] = []
        for item in locale_data.get("items", []):
            api = str(item.get("apiName", ""))
            if not api.startswith("DA_") or not item.get("isAugment"):
                continue
            name = str(item.get("name", ""))
            icon = str(item.get("icon", ""))
            tier, source = resolve_tier(api, name, icon)
            self.augments.append(
                Augment(
                    api_name=api,
                    name=name,
                    desc=str(item.get("desc", "")),
                    icon=icon,
                    tier=tier,
                    tier_source=source,
                    effects=item.get("effects") or {},
                    associated_traits=tuple(item.get("associatedTraits") or ()),
                )
            )

        self._by_api = {a.api_name: a for a in self.augments}

        # Index chinh: ten da normalize -> cac augment mang ten do.
        # Nhom nhieu hon 1 phan tu chinh la cac cap map mo.
        self._by_norm_name: dict[str, list[Augment]] = defaultdict(list)
        for a in self.augments:
            self._by_norm_name[normalize(a.name)].append(a)

        # Index phu: goc (da bo tier) -> cac augment cung goc, de fuzzy match.
        self._by_stem: dict[str, list[Augment]] = defaultdict(list)
        for a in self.augments:
            self._by_stem[normalize(a.stem)].append(a)

    # -- truy van ----------------------------------------------------------

    def __len__(self) -> int:
        return len(self.augments)

    def get(self, api_name: str) -> Augment | None:
        return self._by_api.get(api_name)

    @property
    def ambiguous_groups(self) -> dict[str, list[Augment]]:
        """Cac nhom augment trung ten hien thi sau khi normalize.

        Duoc SUY RA tu du lieu, khong hardcode - de tu dong dung lai o set sau.
        """
        return {k: v for k, v in self._by_norm_name.items() if len(v) > 1}

    def tier_source_counts(self) -> dict[str, int]:
        """Dem so augment giai duoc o moi buoc ladder. Dung cho regression test."""
        counts: dict[str, int] = defaultdict(int)
        for a in self.augments:
            counts[a.tier_source] += 1
        return dict(counts)

    def icon_tier_conflicts(self) -> list[Augment]:
        """Cac augment co duong dan icon MAU THUAN voi tier that.

        Do duoc: 19/254. Day la bang chung dinh luong cho quy tac "ten la chinh".
        """
        conflicts = []
        for a in self.augments:
            m = RE_ICON_ROMAN.search(a.icon.lower())
            if m and len(m.group(1)) != a.tier:
                conflicts.append(a)
        return conflicts

    # -- khop ten ----------------------------------------------------------

    def match_name(self, text: str) -> MatchResult:
        """Khop mot chuoi (thuong la ket qua OCR) vao catalog.

        Chien luoc:
            1. Khop chinh xac sau khi normalize.
            2. Neu ra >1 ung vien, thu tie-break PHAN BIET HOA THUONG.
               Day la ly do buoc nay ton tai: "Tons of Stats!" va
               "TONS of Stats!" chi khac nhau o chu hoa. Quy tac lowercase
               bat buoc o buoc 1 xoa mat dung tin hieu duy nhat tach duoc chung.
            3. Con lai >1 -> map mo that su, tra ca hai, KHONG DOAN.
        """
        norm = normalize(text)
        candidates = list(self._by_norm_name.get(norm, []))

        if not candidates:
            return MatchResult([], False, "khong khop")

        if len(candidates) == 1:
            return MatchResult(candidates, False, "khop chinh xac")

        # Tie-break phan biet hoa thuong truoc khi chiu thua.
        exact_case = [a for a in candidates if a.name == text]
        if len(exact_case) == 1:
            return MatchResult(exact_case, False, "tie-break phan biet hoa thuong")

        return MatchResult(candidates, True, "map mo - trung ca ten lan icon")

    def match_stem(self, text: str) -> list[Augment]:
        """Khop theo phan goc (da bo token tier) - dung khi OCR mat hau to tier."""
        return list(self._by_stem.get(normalize(strip_tier_token(text)), []))


def build_catalogs(
    en_data: dict[str, Any], vi_data: dict[str, Any]
) -> tuple[AugmentCatalog, AugmentCatalog]:
    """Dung catalog cho ca hai ngon ngu (tien loi cho test va script)."""
    return AugmentCatalog(en_data), AugmentCatalog(vi_data)


def diacritic_collisions(names: Iterable[str]) -> dict[str, list[str]]:
    """Tim cac ten dung chung mot dang sau khi bo dau.

    Do duoc: 0 collision tren 36 trait va 249 ten augment tieng Viet. Day la
    ly do OCR CPU nhe la du - khong can engine nang de giu dau.
    """
    groups: dict[str, list[str]] = defaultdict(list)
    for n in set(names):
        groups[normalize(n)].append(n)
    return {k: sorted(v) for k, v in groups.items() if len(v) > 1}
