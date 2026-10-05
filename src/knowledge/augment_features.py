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
EXTRACTOR_VERSION = "deterministic-v1"

# --- Dong audit tay ----------------------------------------------------------
# extraction_method = "manual-audit:<truong,...> (from <method goc>)". Chi cac
# truong PHAN DOAN duoc sua tay; truong dinh danh (trait_affinity, item_grants,
# trait_count_reward) luon sinh lai tu tang 1. Script build ap lai cac dong nay
# khi sinh lai bang, nen quyet dinh audit khong bi xoa am tham.
MANUAL_AUDIT_PREFIX = "manual-audit:"
MANUAL_AUDITABLE = ("category", "carry_type", "tempo", "econ_value", "board_condition")
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
CARRY_TYPES = ("AD", "AP", "tank", "none")
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
CARRY_PATTERNS: dict[str, list[str]] = {
    "AD": [r"attack damage", r"attack speed", r"\bcrit", r"\bmarksman", r"\bad\b"],
    "AP": [r"ability power", r"\bmana\b", r"spell power", r"\bap\b", r"cast(s|ing)?\b"],
    "tank": [r"\bhealth\b", r"\barmor\b", r"magic resist", r"\bshield", r"durabilit"],
}

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
    category: str = "utility"
    carry_type: str = "none"
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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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


def extract_carry_type(desc: str, name: str, econ_context: bool = False) -> str:
    """Loai carry duoc huong loi. Chon nhom co nhieu tin hieu nhat, hoa -> none.

    `econ_context=True` khi augment da duoc phan loai econ/reroll. Khi do MOT
    tin hieu chi so don le (vi du "Gain Health whenever you level up") la nhac
    den ngau nhien, khong phai dinh huong carry - ha ve none thay vi gan nhan
    "tank" sai. Do duoc: quy tac nay bo 40+ nhan tank giat gan tren 254 augment.
    """
    text = f"{name} {desc}"
    counts = {k: _matches(v, text) for k, v in CARRY_PATTERNS.items()}
    best = max(counts.values())
    if best == 0 or (econ_context and best < 2):
        return "none"
    winners = [k for k, v in counts.items() if v == best]
    return winners[0] if len(winners) == 1 else "none"


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
    if _matches([p for ps in CARRY_PATTERNS.values() for p in ps], text):
        return "combat"
    return "utility"


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
    carry_type = extract_carry_type(desc, name, econ_context=category in ("econ", "reroll"))
    tempo = extract_tempo(desc, name)
    trait_count_reward = extract_trait_count_reward(desc, name)

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
        category=category,
        carry_type=carry_type,
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
