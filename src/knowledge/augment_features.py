"""Bang dac trung augment - trich offline, nap luc runtime (SPEC 3.4.1).

VI SAO MODULE NAY TON TAI
-------------------------
Da do metadata augment Set 18 cua CDragon (n = 254): `associatedTraits` chi co
20/254, `incompatibleTraits`/`composition`/`unique` rong hoan toan, `tags` bi
bam, `effects` chi resolve duoc 47% placeholder. Field DUY NHAT day du la
`desc` - van ban tu do, ca EN lan VI.

Ket luan: khong the cham diem bang rule tren field co cau truc. Dac trung
phai duoc TRICH TU VAN BAN, offline, mot lan moi set, roi cache thanh JSON
sua tay duoc. Runtime chi doc JSON -> khong co LLM tren critical path.

HAI TANG TRICH XUAT
-------------------
Tang 1 (module nay, mac dinh): quy tac tat dinh tren tu khoa. Chay duoc ngay,
khong can API key, ket qua tai lap 100%.
Tang 2 (`scripts/build_augment_features.py --llm`): Gemini tinh chinh cac
truong tang 1 khong quyet duoc. Moi entry ghi ro `extraction_method` va
`confidence` de hai tang luon phan biet duoc khi audit.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Iterable

# Chinh sach version: them TRUONG MOI (vd trait_count_reward) giu nguyen v1;
# doi GIA TRI ma luat cu sinh ra cho mot truong da co thi phai len v2 va sinh
# lai ca bang.
# v2 (2026-10-05): carry_type bo "tank" (-> frontline), them "both"; them
# categories va frontline.
EXTRACTOR_VERSION = "deterministic-v2"

# --- Dong audit tay ----------------------------------------------------------
# extraction_method = "manual-audit:<truong,...> (from <method goc>)". Chi cac
# truong PHAN DOAN duoc sua tay; truong dinh danh (trait_affinity, item_grants,
# trait_count_reward) luon sinh lai tu tang 1. Script build ap lai cac dong nay
# khi sinh lai bang, nen quyet dinh audit khong bi xoa am tham.
MANUAL_AUDIT_PREFIX = "manual-audit:"
MANUAL_AUDITABLE = ("category", "categories", "carry_type", "frontline", "tempo", "econ_value",
                    "board_condition")
RE_MANUAL_AUDIT = re.compile(r"^manual-audit:([a-z_,]+) \(from ([^()]+)\)$")


def parse_manual_audit(method: str) -> tuple[tuple[str, ...], str] | None:
    """(cac truong sua tay, method goc), hoac None neu khong phai dong audit.

    Label sai dinh dang hoac ghi truong khong duoc sua -> ValueError: dong
    audit doc khong ra thi khong duoc am tham coi nhu dong thuong.
    """
    if not method.startswith(MANUAL_AUDIT_PREFIX):
        return None
    m = RE_MANUAL_AUDIT.match(method)
    if not m:
        raise ValueError(f"label audit sai dinh dang: {method!r}")
    fields = tuple(m.group(1).split(","))
    bad = [f for f in fields if f not in MANUAL_AUDITABLE]
    if bad:
        raise ValueError(f"truong khong duoc sua tay: {bad} trong {method!r}")
    return fields, m.group(2)


CATEGORIES = ("econ", "combat", "trait", "item", "utility", "reroll")
# Toi da 3 nhan/lose (khop MetaTFT 1-3 tag). categories[0] la nhan chinh = `category`.
MAX_CATEGORIES = 3
# carry_type = huong carry SAT THUONG ma lose phuc vu. "tank" KHONG phai huong carry
# (doi nao cung can tank) - chi so chong chiu nam o `frontline`. "both" = phuc vu
# ca carry AD lan AP. Dinh nghia: docs/category-multilabel/definition.md
CARRY_TYPES = ("AD", "AP", "both", "none")
LEGACY_CARRY_TANK = "tank"     # gia tri cu, chi con trong du lieu truoc 2026-10-05
TEMPOS = ("immediate", "scaling")
# Huong thuong theo SO LUONG trait (khong gan trait cu the nao):
#   vertical - thuong theo so dong minh CHUNG trait (di sau mot trait)
#   wide     - thuong theo so trait DANG BAT (bat nhieu trait khac nhau)
# Hai huong nguoc nhau nen KHONG gop thanh mot bool.
TRAIT_COUNT_REWARDS = ("vertical", "wide")

# --- Tu vung component -----------------------------------------------------
# 8 component co ban + spatula/frying pan. Ten on dinh qua nhieu set; ban
# dich VI khong dung o day vi trich xuat luon chay tren locale EN.
COMPONENT_PATTERNS: dict[str, str] = {
    "BFSword": r"b\.?\s?f\.?\s?sword",
    "RecurveBow": r"recurve bow",
    "NeedlesslyLargeRod": r"needlessly large rod",
    "TearOfTheGoddess": r"tear of the goddess",
    "ChainVest": r"chain vest",
    "NegatronCloak": r"negatron cloak",
    "GiantsBelt": r"giant.?s belt",
    "SparringGloves": r"sparring gloves",
    "Spatula": r"spatula",
    "FryingPan": r"frying pan",
}

# Cac cach noi "cho item" ma khong goi ten component cu the.
GENERIC_ITEM_PATTERNS: dict[str, str] = {
    "AnyComponent": r"\bcomponents?\b",
    "Anvil": r"\banvil\b",
    "Emblem": r"\bemblem\b",
    "CompletedItem": r"\bcompleted item|\bfull item\b",
}

# --- Tu vung econ ----------------------------------------------------------
RE_GOLD_AMOUNT = re.compile(r"(\d+)\s*(?:@\w+@\s*)?gold", re.I)
RE_GOLD_PLACEHOLDER = re.compile(r"@[\w.*]+@\s*gold", re.I)
ECON_KEYWORDS = {
    "interest": r"\binterest\b",
    "gold": r"\bgold\b",
    "xp": r"\bxp\b|\bexperience\b",
    "reroll": r"\brerolls?\b|\brefresh(es|ed)?\b",
    "loss_streak": r"\bloss(ing)? streak\b",
    "win_streak": r"\bwin(ning)? streak\b",
}

# --- Tu vung carry type ----------------------------------------------------
# Chi huong SAT THUONG. Chi so chong chiu tach sang DURABILITY_PATTERNS.
CARRY_PATTERNS: dict[str, list[str]] = {
    "AD": [r"attack damage", r"attack speed", r"\bcrit", r"\bmarksman", r"\bad\b"],
    "AP": [r"ability power", r"\bmana\b", r"spell power", r"\bap\b", r"cast(s|ing)?\b"],
}
# Bo "tank" cua v1 - giu nguyen de extract_category khong doi nhan chinh.
LEGACY_TANK_PATTERNS = [r"\bhealth\b", r"\barmor\b", r"magic resist", r"\bshield", r"durabilit"]
# Tin hieu frontline: nhu bo v1 nhung bo mau nguoi choi ("player/Tactician
# health" la mau tuong, khong phai chi so tuong) va them hoi mau/giam sat thuong.
DURABILITY_PATTERNS = [
    # health/heal khong di kem "player"/"Tactician" (ke ca "@X@ Tactician health").
    r"(?<!player )(?<!tactician )\bhealth\b(?!@?\s+(player|tactician)\s+health)",
    r"\barmor\b", r"magic resist", r"\bshield", r"durabilit",
    r"\bheal(s|ed|ing)?\b(?!\s+(\S+\s+)?(player|tactician))", r"damage reduction",
]
# Hieu ung trong tran khong thuoc nhom chi so nao o tren.
COMBAT_EXTRA_PATTERNS = [
    r"damage amp", r"omnivamp", r"\bstun", r"true damage", r"magic damage",
    r"critical strike", r"\bprecision\b",
]
# Cau noi ve mon do (ten component, "holder", "spend/spent mana" de nhan them do)
# khong tinh la tin hieu combat: chi so do mon do tang da thuoc nhan `item`.
ITEM_SENTENCE_PATTERNS = [*COMPONENT_PATTERNS.values(), r"\bholders?\b", r"\bspen[dt]\b"]
# Thu tu uu tien nhan - cung thu tu voi extract_category.
CATEGORY_PRIORITY = ("reroll", "econ", "item", "trait", "combat", "utility")

# --- Tu vung tempo ---------------------------------------------------------
SCALING_PATTERNS = [
    r"each round", r"every round", r"per round", r"stacks?\b", r"stacking",
    r"permanently", r"grows?\b", r"\bmore\b", r"over time", r"each time",
    r"for the rest of the game", r"increases? by",
]
IMMEDIATE_PATTERNS = [r"\bimmediately\b", r"\binstantly\b", r"\bnow\b", r"\bgain a\b"]

# --- Tu vung thuong theo so luong trait ------------------------------------
# Chi bat cau mo ta PHAN THUONG tang theo so trait / so dong minh chung trait.
# Augment chi CHO emblem (Branching Out, The Trait Tree, ...) KHONG thuoc nhom
# nay: emblem la nguon trait, da nam o item_grants; gia tri cua no khong tang
# theo do sau/do rong trait tren board.
VERTICAL_TRAIT_PATTERNS = [r"\bshares? a trait with\b"]
WIDE_TRAIT_PATTERNS = [
    r"\bfor each (?:[\w-]+ )?traits?\b",   # "for each non-unique Trait", "for each Bronze-tier trait"
    r"\bfielding\b.{0,40}\btraits\b",      # Trait Ladder: "fielding N non-unique traits"
]


@dataclass
class AugmentFeature:
    """Dac trung cua mot augment - dau vao cua toan bo scoring engine.

    Moi field deu co the la None/rong: khong trich duoc thi de trong, KHONG
    bia. Scoring component nao gap None thi tu tra diem trung tinh kem ly do
    noi ro la thieu du lieu.
    """

    api_name: str
    name: str = ""
    tier: int = 0
    category: str = "utility"     # = categories[0], giu cho cac cho doc cu
    categories: list[str] = field(default_factory=list)
    carry_type: str = "none"
    frontline: bool = False       # lose chu yeu cho chi so/hieu ung chong chiu
    trait_affinity: list[str] = field(default_factory=list)
    econ_value: int = 0           # 0-3, CHI vang/XP/reroll - item nam o item_grants
    tempo: str = "immediate"
    item_grants: list[str] = field(default_factory=list)
    board_condition: str | None = None
    # None = khong thuong theo so trait. Tach khoi trait_affinity: truong do chi
    # chua trait CU THE, nen augment kieu Verticality truoc day vo hinh voi scorer.
    trait_count_reward: str | None = None
    extraction_method: str = EXTRACTOR_VERSION
    confidence: float = 0.0

    def __post_init__(self) -> None:
        # Chuyen doi du lieu cu tai MOT cho, nen load file cu va constructor kieu cu
        # (chi truyen `category`, hoac carry_type="tank") deu ra schema moi.
        if self.carry_type == LEGACY_CARRY_TANK:
            self.carry_type = "none"
            self.frontline = True
        if not self.categories:
            self.categories = [self.category]
        else:
            self.category = self.categories[0]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def check_feature(f: AugmentFeature) -> list[str]:
    """Bat bien giua categories/carry_type va cac truong cau truc. Rong = hop le.

    Nhan nao co nen du lieu thi phai KHOP voi du lieu do, de hai nguon khong
    the noi nguoc nhau. Chieu nguoc (co `econ` => econ_value > 0) khong bat
    buoc: reroll thuan co the co econ_value rieng.
    """
    errs: list[str] = []
    cats = f.categories
    if not 1 <= len(cats) <= MAX_CATEGORIES:
        errs.append(f"can 1-{MAX_CATEGORIES} nhan category, dang co {len(cats)}")
    if len(set(cats)) != len(cats):
        errs.append("categories bi trung")
    bad = [c for c in cats if c not in CATEGORIES]
    if bad:
        errs.append(f"category la: {bad}")
    if cats and f.category != cats[0]:
        errs.append("category phai bang categories[0]")
    if "utility" in cats and len(cats) > 1:
        errs.append("utility chi dung mot minh")
    if f.econ_value > 0 and "econ" not in cats:
        errs.append("econ_value > 0 nhung thieu nhan econ")
    if f.item_grants and "item" not in cats:
        errs.append("item_grants khac rong nhung thieu nhan item")
    if (f.trait_affinity or f.trait_count_reward) and "trait" not in cats:
        errs.append("co trait_affinity/trait_count_reward nhung thieu nhan trait")
    if "Emblem" in f.item_grants and "trait" not in cats:
        errs.append("lose cho Emblem nhung thieu nhan trait")
    if f.carry_type not in CARRY_TYPES:
        errs.append(f"carry_type la: {f.carry_type!r}")
    return errs


def _matches(patterns: Iterable[str], text: str) -> int:
    """Dem so pattern khop - dung lam thang do manh yeu cua tin hieu."""
    return sum(1 for p in patterns if re.search(p, text, re.I))


def extract_trait_affinity(
    desc: str, name: str, associated: Iterable[str], traits: dict[str, str]
) -> list[str]:
    """Tra ve danh sach trait_id lien quan.

    `associatedTraits` (20/254) la nguon CHUAN - lay truoc. Van ban chi dung
    de bo sung, va chi khi ten trait xuat hien nguyen ven (word boundary) de
    tranh khop nham cac tu thong dung nhu "Hunter" trong cau mo ta khac.

    Args:
        traits: map ten hien thi EN -> trait apiName, lay tu setData.
    """
    found = list(dict.fromkeys(associated))
    text = f"{name} {desc}"
    for display, api in traits.items():
        if api in found:
            continue
        if re.search(rf"\b{re.escape(display)}\b", text, re.I):
            found.append(api)
    return found


def extract_item_grants(desc: str, name: str) -> list[str]:
    """Component/item ma augment tang. Ten cu the truoc, chung chung sau."""
    text = f"{name} {desc}"
    grants = [k for k, p in COMPONENT_PATTERNS.items() if re.search(p, text, re.I)]
    for key, pat in GENERIC_ITEM_PATTERNS.items():
        if re.search(pat, text, re.I):
            grants.append(key)
    return grants


def extract_econ_value(desc: str, name: str) -> int:
    """Cho diem econ 0-3 tu tin hieu van ban.

    Thang do co chu y tho: 254 augment khong the phan biet tinh te bang regex,
    va gia vo lam duoc dieu do se de lai mot con so trong ra dang tin hon thuc
    te. Tang 2 (LLM) chinh lai cai nay - do la ly do no ton tai.

    Dinh nghia: econ_value CHI do vang, XP va reroll/gia tri shop. Item
    (component, emblem, anvil...) KHONG tinh - chung thuoc `item_grants`.
    Neu tinh ca item thi EconFit (strength = econ_value / 3) se cham augment
    chi cho item nhu loi kinh te manh nhat.

    Do lech da biet: tang 1 cham theo SO LON NHAT trong van ban (placeholder
    "@X@ gold" -> 2, nhac "interest" -> 3, khong tinh tuong), con prompt tang 2
    va audit tay cham theo TONG gia tri quy ra vang. Hai thang chua khop.
    """
    text = f"{name} {desc}"
    # Cong gate: mot augment co the la kinh te ma khong bao gio noi chu "gold"
    # (vi du chi noi ve interest hoac reroll). Bo sot chung se lam EconFit im
    # lang tra ve trung tinh cho dung nhung augment kinh te manh nhat.
    gates = ("gold", "xp", "reroll", "interest")
    if not any(re.search(ECON_KEYWORDS[k], text, re.I) for k in gates):
        return 0

    score = 1
    amounts = [int(m) for m in RE_GOLD_AMOUNT.findall(text)]
    if amounts:
        top = max(amounts)
        if top >= 20:
            score = 3
        elif top >= 8:
            score = 2
    if re.search(ECON_KEYWORDS["interest"], text, re.I):
        score = max(score, 3)   # interest gop lai theo cap so cong -> gia tri cao nhat
    if re.search(ECON_KEYWORDS["reroll"], text, re.I):
        score = max(score, 2)
    if RE_GOLD_PLACEHOLDER.search(text) and score == 1:
        score = 2               # so bi an sau placeholder, gia dinh khong tam thuong
    return min(score, 3)


def extract_frontline(desc: str, name: str, econ_context: bool = False) -> bool:
    """True khi gia tri CHU YEU la chong chiu: tin hieu chong chiu nhieu hon
    TONG tin hieu AD + AP + Damage Amp (bao thu - nua cong nua thu thi khong tinh).

    `econ_context=True` (augment econ/reroll): mot tin hieu don le la nhac den
    ngau nhien ("Gain Health whenever you level up"), can it nhat 2.
    """
    text = f"{name} {desc}"
    durability = _matches(DURABILITY_PATTERNS, text)
    if durability == 0 or (econ_context and durability < 2):
        return False
    damage = sum(_matches(v, text) for v in CARRY_PATTERNS.values())
    # Damage Amp la sat thuong khong thuoc AD/AP: khong dinh huong carry nhung
    # van la phia "cong" khi can xem augment co chu yeu chong chiu khong.
    damage += _matches([r"damage amp"], text)
    return durability > damage


def extract_carry_type(desc: str, name: str, econ_context: bool = False) -> str:
    """Huong carry SAT THUONG: AD / AP / both / none.

    Nhieu tin hieu AD hon -> AD, AP hon -> AP. Hoa AD == AP >= 1 -> both (mo
    ta cho ca chi so phia AD lan phia AP). Tin hieu chong chiu >= tin hieu sat
    thuong -> none: "tank" khong phai huong carry, no nam o extract_frontline.

    `econ_context=True` khi augment da duoc phan loai econ/reroll. Khi do MOT
    tin hieu chi so don le la nhac den ngau nhien, khong phai dinh huong carry
    - ha ve none. Do duoc o v1: quy tac nay bo 40+ nhan giat gan tren 254 augment.
    """
    text = f"{name} {desc}"
    ad = _matches(CARRY_PATTERNS["AD"], text)
    ap = _matches(CARRY_PATTERNS["AP"], text)
    best = max(ad, ap)
    if best == 0 or (econ_context and best < 2):
        return "none"
    # Tin hieu chong chiu ngang hoac hon tin hieu sat thuong -> khong ro huong
    # carry (giu nghia hoa -> none cua v1, chi doi nhan "tank" thanh none).
    if _matches(DURABILITY_PATTERNS, text) >= best:
        return "none"
    if ad == ap:
        return "both"
    return "AD" if ad > ap else "AP"


def extract_tempo(desc: str, name: str) -> str:
    """immediate hay scaling. Hoa -> immediate (gia dinh bao thu hon)."""
    text = f"{name} {desc}"
    scaling = _matches(SCALING_PATTERNS, text)
    immediate = _matches(IMMEDIATE_PATTERNS, text)
    return "scaling" if scaling > immediate else "immediate"


def extract_trait_count_reward(desc: str, name: str) -> str | None:
    """vertical / wide / None. Vertical kiem truoc: cau "ally that shares a
    trait" mo ta do sau, khong phai so trait dang bat."""
    text = f"{name} {desc}"
    if _matches(VERTICAL_TRAIT_PATTERNS, text):
        return "vertical"
    if _matches(WIDE_TRAIT_PATTERNS, text):
        return "wide"
    return None


def extract_category(
    econ_value: int, item_grants: list[str], trait_affinity: list[str], desc: str, name: str
) -> str:
    """Phan loai - thu tu uu tien la mot QUYET DINH, khong phai tuy tien.

    reroll > econ > item > trait > combat > utility. Augment reroll cung noi
    ve gold nhung hanh vi choi khac han (giu vang de roll), nen no phai thang
    econ. Trait dung sau item vi augment cho emblem thuong duoc doc nhu item.
    """
    text = f"{name} {desc}"
    if re.search(ECON_KEYWORDS["reroll"], text, re.I):
        return "reroll"
    if econ_value >= 2:
        return "econ"
    if item_grants:
        return "item"
    if trait_affinity:
        return "trait"
    stat_patterns = [*CARRY_PATTERNS["AD"], *CARRY_PATTERNS["AP"], *LEGACY_TANK_PATTERNS]
    if _matches(stat_patterns, text):
        return "combat"
    return "utility"


def mandatory_categories(
    econ_value: int,
    item_grants: list[str],
    trait_affinity: list[str],
    trait_count_reward: str | None,
) -> list[str]:
    """Nhan BAT BUOC theo bat bien cua check_feature, theo thu tu uu tien."""
    out = []
    if econ_value > 0:
        out.append("econ")
    if item_grants:
        out.append("item")
    # An khong cho chi so: toan bo gia tri cua no la them mot toc he.
    if trait_affinity or trait_count_reward or "Emblem" in item_grants:
        out.append("trait")
    return out


def compose_categories(
    primary: str, mandatory: Iterable[str], suggested: Iterable[str] = ()
) -> list[str]:
    """Ghep nhan: chinh + bat buoc + goi y, bo trung, toi da MAX_CATEGORIES.

    Tran 3 chi cat nhan GOI Y, khong cat nhan bat buoc (neu chinh + bat buoc
    da > 3 thi tra ve het - check_feature se bao dong do).
    `utility` chi dung mot minh: chinh la utility ma co nhan bat buoc thi
    utility bi bo va nhan bat buoc dau tien thanh nhan chinh; nhan goi y khong
    bao gio la utility.
    """
    mandatory = [c for c in CATEGORY_PRIORITY if c in set(mandatory)]
    if primary == "utility":
        if not mandatory:
            return ["utility"]
        primary = mandatory[0]
    head = list(dict.fromkeys([primary, *mandatory]))
    rank = {c: i for i, c in enumerate(CATEGORY_PRIORITY)}
    extra = sorted(
        {c for c in suggested if c not in head and c != "utility"}, key=rank.__getitem__
    )
    return head + extra[: max(0, MAX_CATEGORIES - len(head))]


def _combat_signals(desc: str, name: str) -> int:
    """Dem tin hieu chi so/hieu ung trong tran, bo cac cau noi ve mon do."""
    patterns = [
        *CARRY_PATTERNS["AD"], *CARRY_PATTERNS["AP"], *DURABILITY_PATTERNS,
        *COMBAT_EXTRA_PATTERNS,
    ]
    total = 0
    for sentence in re.split(r"[.!?]", f"{name}. {desc}"):
        if _matches(ITEM_SENTENCE_PATTERNS, sentence):
            continue
        total += _matches(patterns, sentence)
    return total


def extract_categories(
    primary: str,
    econ_value: int,
    item_grants: list[str],
    trait_affinity: list[str],
    trait_count_reward: str | None,
    desc: str,
    name: str,
) -> list[str]:
    """1-3 nhan, `primary` (= extract_category) dung dau.

    Nhan phu chi them khi co co che neu ro trong mo ta:
      - bat buoc: econ (econ_value > 0), item (item_grants), trait
        (trait_affinity / trait_count_reward) - khop check_feature;
      - reroll: co tu khoa reroll (co tac dung khi nhan chinh khong phai
        reroll, vd nhan chinh do LLM/audit dat);
      - combat: co tin hieu chi so trong tran ngoai cau noi ve mon do. Nhan
        chinh econ/reroll can >= 2 tin hieu (cung ly do voi econ_context).
    """
    text = f"{name} {desc}"
    suggested = []
    if re.search(ECON_KEYWORDS["reroll"], text, re.I):
        suggested.append("reroll")
    need = 2 if primary in ("econ", "reroll") else 1
    if _combat_signals(desc, name) >= need:
        suggested.append("combat")
    mandatory = mandatory_categories(econ_value, item_grants, trait_affinity, trait_count_reward)
    return compose_categories(primary, mandatory, suggested)


def extract_deterministic(
    item: dict[str, Any], traits: dict[str, str], tier: int = 0
) -> AugmentFeature:
    """Tang 1: trich toan bo dac trung cua mot augment bang quy tac tat dinh.

    Args:
        item: mot entry augment tu locale CDragon (apiName/name/desc/...).
        traits: map ten trait EN -> apiName.
        tier: tier da giai boi AugmentCatalog (0 neu chua giai).
    """
    name = str(item.get("name", ""))
    desc = str(item.get("desc", ""))

    trait_affinity = extract_trait_affinity(
        desc, name, item.get("associatedTraits") or (), traits
    )
    item_grants = extract_item_grants(desc, name)
    econ_value = extract_econ_value(desc, name)
    # Category truoc carry_type: phan loai la NGU CANH de doc tin hieu chi so.
    category = extract_category(econ_value, item_grants, trait_affinity, desc, name)
    econ_context = category in ("econ", "reroll")
    carry_type = extract_carry_type(desc, name, econ_context=econ_context)
    frontline = extract_frontline(desc, name, econ_context=econ_context)
    tempo = extract_tempo(desc, name)
    trait_count_reward = extract_trait_count_reward(desc, name)
    categories = extract_categories(
        category, econ_value, item_grants, trait_affinity, trait_count_reward, desc, name
    )

    # Confidence = ti le tin hieu THUC SU tim thay, khong phai do tin cua ta.
    signals = [
        bool(trait_affinity), bool(item_grants), econ_value > 0,
        carry_type != "none", bool(desc),
    ]
    confidence = round(sum(signals) / len(signals), 2)

    board_condition = None
    if trait_affinity:
        board_condition = f"can unit thuoc trait: {', '.join(trait_affinity)}"

    return AugmentFeature(
        api_name=str(item.get("apiName", "")),
        name=name,
        tier=tier,
        category=categories[0],
        categories=categories,
        carry_type=carry_type,
        frontline=frontline,
        trait_affinity=trait_affinity,
        econ_value=econ_value,
        tempo=tempo,
        item_grants=item_grants,
        board_condition=board_condition,
        trait_count_reward=trait_count_reward,
        extraction_method=EXTRACTOR_VERSION,
        confidence=confidence,
    )


class FeatureTable:
    """Bang dac trung da nap - thu chi doc ma scoring engine dung luc runtime."""

    def __init__(
        self, features: dict[str, AugmentFeature], meta: dict[str, Any] | None = None
    ) -> None:
        self.features = features
        self.meta = meta or {}

    def __len__(self) -> int:
        return len(self.features)

    def __contains__(self, api_name: object) -> bool:
        return api_name in self.features

    def get(self, api_name: str) -> AugmentFeature | None:
        """Tra dac trung, hoac None neu augment khong co trong bang.

        None la trang thai HOP LE: augment moi ra ma bang chua sinh lai. Moi
        scoring component phai xu ly duoc None bang diem trung tinh.
        """
        return self.features.get(api_name)

    @classmethod
    def load(cls, path: str | Path) -> "FeatureTable":
        """Nap tu data/augment_features.json."""
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        feats = {k: AugmentFeature(**v) for k, v in payload.get("augments", {}).items()}
        return cls(feats, payload.get("meta", {}))

    @classmethod
    def empty(cls) -> "FeatureTable":
        """Bang rong - cho phep chay he thong truoc khi sinh bang lan dau."""
        return cls({}, {"note": "bang rong - moi dac trung se la trung tinh"})

    def to_payload(self, meta: dict[str, Any]) -> dict[str, Any]:
        """Dung payload JSON de ghi ra dia (script sinh bang dung)."""
        return {
            "meta": meta,
            "augments": {k: v.to_dict() for k, v in sorted(self.features.items())},
        }
