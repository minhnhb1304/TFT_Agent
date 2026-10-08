"""Catalog augment Set 18 - giai tier, chuan hoa ten, khop ket qua OCR.

Day la noi research/vision-stack/augments.md tro thanh code. Moi con so trong
module nay deu do duoc tu du lieu that ngay 2026-08-28 va duoc test khoa lai.

HAI QUY TAC QUAN TRONG NHAT
---------------------------
1. ICON CHO TIER TUYET DOI, TEN CHI CHO QUAN HE TRONG HO.
   Nguoi dung (nguoi choi that) chot ngay 2026-10-06, thay cho quy tac cu
   "ten la chinh" (Plus -> 2, PlusPlus -> 3, I/II/III -> 1/2/3):
     A. Bien the `+` / `++` la CUNG MOT augment voi ban goc, chi duoc chao o
        luot muon hon -> CUNG TIER voi ban goc. Hau to khong noi gi ve tier.
     B. So la ma la THU HANG tier trong mot ho (II cao hon I), KHONG phai tier
        tuyet doi: "I" co the da la gold, khi do "II" la prismatic.
   Vi vay tier tuyet doi lay tu duong dan icon (resolve_tier), con ten chi
   dung o buoc catalog (AugmentCatalog._apply_family_rules) de ep hai rang buoc
   A va B. Do duoc: quy tac cu gan khac icon o 30/254 augment; sau khi doi,
   quy tac A + B chi con lam 1 augment (DA_TonsOfStatsII) khac icon cua no.
     C. 7 augment co icon CDragon SAI tier va khong luat nao suy ra duoc: nguoi
        dung xac nhan tung cai, ghi trong FILE DU LIEU
        data/augment_tier_overrides.json (khong hardcode trong code), ap o
        buoc CUOI voi tier_source = "user-override".

2. CO 4 CAP KHONG THE PHAN BIET - PHAI CHAP NHAN, KHONG DUOC DOAN.
   Bon cap augment trung CA ten hien thi LAN icon. Khong phuong phap nhan dang
   nao tach duoc chung vi khong con tin hieu nao de doc. Sau khi sua tier
   (2026-10-06) ca bon cap deu CUNG TIER: thu mat la danh tinh, khong phai tier.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Iterable, Mapping

# --- Ladder giai tier: icon cho tier tuyet doi, ten cho quan he trong ho ----
RE_API_PLUS = re.compile(r"Plus(?:Plus)?(?=$|_)")  # ca DA_XPlus LAN DA_XPlus_Y
RE_API_ROMAN = re.compile(r"(I{1,3})$")
RE_NAME_ROMAN = re.compile(r"\b(I{1,3})$")
RE_PLACEHOLDER = re.compile(r"missing-t(\d)\.tex$")
RE_ICON_ROMAN = re.compile(r"[-_](i{1,3})\.tex$")  # CA underscore LAN hyphen
RE_ICON_DIGIT = re.compile(r"(\d)\.tex$")

# tier_source do buoc catalog ghi (xem AugmentCatalog._apply_family_rules).
SOURCE_VARIANT = "variant-of-base"
SOURCE_ROMAN_ORDER = "roman-order"
SOURCE_OVERRIDE = "user-override"
MAX_TIER = 3

# Tier do NGUOI DUNG xac nhan cho cac augment ma icon CDragon sai.
TIER_OVERRIDES_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "augment_tier_overrides.json"
)


def load_tier_overrides(path: Path | str = TIER_OVERRIDES_PATH) -> dict[str, int]:
    """Nap {api_name: tier} tu file override. Khong co file -> {} (khong loi).

    Raises:
        ValueError: tier ngoai [1, MAX_TIER] - file hong thi dung ngay.
    """
    path = Path(path)
    if not path.exists():
        return {}
    tiers = json.loads(path.read_text(encoding="utf-8")).get("tiers", {})
    for api, tier in tiers.items():
        if not isinstance(tier, int) or not 1 <= tier <= MAX_TIER:
            raise ValueError(f"{path}: tier khong hop le cho {api}: {tier!r}")
    return dict(tiers)

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
    """Giai tier TUYET DOI cua mot augment tu duong dan icon (ladder 3 buoc).

    api_name va name KHONG con duoc dung lam tier tuyet doi (quy tac A va B o
    docstring dau module); hai tham so duoc giu de khong doi chu ky ham. Rang
    buoc giua cac augment cung ho do AugmentCatalog ap sau, vi can ca catalog.

    Do duoc tren 254 augment Set 18 (2026-10-06), TRUOC buoc catalog:
        buoc 1 missing-tN    ->  48
        buoc 2 icon roman    -> 176
        buoc 3 icon digit    ->  30
        tong                 -> 254, khong con cai nao chua giai
        phan bo tier         -> 68 / 118 / 68

    Returns:
        (tier, ten_buoc_da_giai) - tra ca nguon de audit va debug duoc.
    """
    icon_l = str(icon).lower()

    # Buoc 1 - placeholder ma hoa tier ngay trong ten file.
    # Nghich ly: chinh cac placeholder lam template matching bat kha thi lai la
    # mot trong nhung tin hieu tier dang tin cay nhat.
    m = RE_PLACEHOLDER.search(icon_l)
    if m:
        return int(m.group(1)), "missing-tN"

    # Buoc 2 - hau to la ma trong duong dan icon. CA _ LAN - deu phai bat.
    m = RE_ICON_ROMAN.search(icon_l)
    if m:
        return len(m.group(1)), "icon roman"

    # Buoc 3 - chu so cuoi duong dan icon.
    m = RE_ICON_DIGIT.search(icon_l)
    if m:
        return int(m.group(1)), "icon digit"

    return 0, "UNRESOLVED"


def variant_base_api(api_name: str) -> str | None:
    """Tra apiName cua ban goc neu day la bien the `+`/`++`, nguoc lai None.

    Vd DA_BandOfThievesIIPlus -> DA_BandOfThievesII,
       DA_18_PrimalAugmentPlus_Sivir -> DA_18_PrimalAugment_Sivir.
    """
    m = RE_API_PLUS.search(api_name)
    if not m:
        return None
    return api_name[: m.start()] + api_name[m.end():]


def roman_family(api_name: str, name: str) -> tuple[str, int] | None:
    """Tra (khoa ho, thu hang la ma) neu augment mang so la ma, nguoc lai None.

    Uu tien so trong TEN HIEN THI: DA_InvestmentStrategy co ten "Investment
    Strategy II", DA_GlassCannon_Gold co ten "Glass Cannon II". Khi ten khong
    co so (hai "Tons of Stats!") moi dung hau to apiName.
    """
    m = RE_NAME_ROMAN.search(name.strip())
    if m:
        return "name:" + normalize(strip_tier_token(name)), len(m.group(1))
    m = RE_API_ROMAN.search(api_name)
    if m:
        return "api:" + api_name[: m.start()].rstrip("_"), len(m.group(1))
    return None


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

    def __init__(
        self,
        locale_data: dict[str, Any],
        tier_overrides: Mapping[str, int] | None = None,
    ) -> None:
        """Dung catalog tu du lieu locale CommunityDragon da nap.

        Args:
            locale_data: dict co key "items" (danh sach item cua cdragon).
            tier_overrides: {api_name: tier} do nguoi dung xac nhan, ap sau
                cung. None = nap data/augment_tier_overrides.json (khong co
                file thi coi nhu rong); {} = khong override.

        Raises:
            ValueError: override nhac toi api_name khong co trong catalog.
        """
        self.augments: list[Augment] = []
        # (api_name, ly do) cho moi augment ma quy tac A/B KHONG ap duoc.
        # Khong doan: tier giu nguyen theo icon, viec con lai la bao cao.
        self.tier_rule_gaps: list[tuple[str, str]] = []
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

        self._apply_family_rules()
        self._apply_tier_overrides(
            load_tier_overrides() if tier_overrides is None else tier_overrides
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

    def _apply_family_rules(self) -> None:
        """Ep hai rang buoc cap catalog len tier da giai tu icon.

        B truoc, A sau - de bien the `+` nhan dung tier cua ban goc sau khi ban
        goc da duoc sua theo thu tu la ma (vd DA_BandOfThievesIIPlus).

        B. Trong mot ho la ma, tier phai TANG NGAT theo so. Cho icon vi pham
           (DA_TonsOfStatsII dung chung icon _ii voi ban I) thi nang ban so cao
           len (tier ban thap + 1), ghi tier_source = "roman-order".
        A. Bien the `+`/`++` lay tier cua ban goc khi ban goc co trong catalog,
           ghi tier_source = "variant-of-base".
        Khong bao gio vuot MAX_TIER; khong ap duoc thi ghi vao tier_rule_gaps.
        """
        by_api = {a.api_name: a for a in self.augments}

        families: dict[str, list[tuple[int, str]]] = defaultdict(list)
        for a in self.augments:
            if variant_base_api(a.api_name) is not None:
                continue  # bien the theo ban goc, khong tu xep hang
            fam = roman_family(a.api_name, a.name)
            if fam:
                families[fam[0]].append((fam[1], a.api_name))
        for members in families.values():
            floor = 0  # tier cao nhat cua cac so la ma nho hon
            for rank in sorted({r for r, _ in members}):
                apis = [api for r, api in members if r == rank]
                for api in apis:
                    a = by_api[api]
                    if a.tier > floor:
                        continue
                    if floor + 1 > MAX_TIER:
                        self.tier_rule_gaps.append(
                            (api, f"roman-order: can tier > {MAX_TIER}")
                        )
                        continue
                    by_api[api] = replace(
                        a, tier=floor + 1, tier_source=SOURCE_ROMAN_ORDER
                    )
                floor = max([floor] + [by_api[api].tier for api in apis])

        for a in self.augments:
            base_api = variant_base_api(a.api_name)
            if base_api is None:
                continue
            base = by_api.get(base_api)
            if base is None:
                self.tier_rule_gaps.append(
                    (a.api_name, f"variant-of-base: khong co {base_api} trong catalog")
                )
                continue
            by_api[a.api_name] = replace(
                a, tier=base.tier, tier_source=SOURCE_VARIANT
            )

        self.augments = [by_api[a.api_name] for a in self.augments]

    def _apply_tier_overrides(self, overrides: Mapping[str, int]) -> None:
        """Buoc CUOI: ghi de tier bang gia tri nguoi dung da xac nhan.

        Override tro toi api_name khong ton tai la dau hieu file da cu (doi
        set, doi ten) -> dung ngay thay vi am tham bo qua.
        """
        known = {a.api_name for a in self.augments}
        unknown = sorted(set(overrides) - known)
        if unknown:
            raise ValueError(
                f"tier override cho api_name khong co trong catalog: {unknown}"
            )
        self.augments = [
            replace(a, tier=overrides[a.api_name], tier_source=SOURCE_OVERRIDE)
            if a.api_name in overrides
            else a
            for a in self.augments
        ]

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
        """Dem augment theo nguon tier cuoi cung. Dung cho regression test.

        So do (2026-10-06) duoc khoa o tests/test_augment_catalog.py.
        """
        counts: dict[str, int] = defaultdict(int)
        for a in self.augments:
            counts[a.tier_source] += 1
        return dict(counts)

    def icon_tier_conflicts(self) -> list[Augment]:
        """Cac augment co tier cuoi cung KHAC tier ma icon cua chinh no noi.

        Do duoc (2026-10-06): 8/254 = DA_TonsOfStatsII (icon _ii, nang len 3 vi
        ban I da la 2) + 7 augment "user-override". Quy tac cu "ten la chinh"
        cho 30/254 theo cung phep do.
        """
        return [
            a
            for a in self.augments
            if resolve_tier(a.api_name, a.name, a.icon)[0] != a.tier
        ]

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
