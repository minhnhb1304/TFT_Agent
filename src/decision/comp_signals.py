"""Tin hieu chot bai cho CompSelector - SPEC 3.5.2.

Mo hinh ra quyet dinh cua nguoi choi hang cao ma module nay ma hoa:

    1. KIEU DOI HINH quyet dinh tin hieu nao dang tin. Reroll (carry 1-3 vang)
       chot bang tuong loi ngay tu dau. Fast 8/9 thi KHONG: dau tran chi can
       mot board manh bat ky de giu mau + tich tien, roi ban ca board va mua
       doi hinh that o giai doan xoay bai. Ti le tuong loi truoc luc do bang 0
       la DUNG ke hoach, khong phai lech huong.
    2. DO noi huong bang LOAI (AP/AD), khong bang TEN: do ghep som duoc dat len
       tuong nao cam tot nhat luc do, roi chuyen sang carry khi xoay bai. Do
       tank la dieu kien can cua moi doi hinh nen khong chi huong.
    3. AN la dieu kien thuan loi khi trait cua no nam trong doi hinh VA an do
       manh theo so lieu thong ke.
    4. Xoay bai som hay muon phu thuoc kinh te: tien len cap + tien mua tuong
       tinh duoc; tien roll thi KHONG (yeu to may man) nen khong cong vao.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from ..game_state.models import RE_STAGE, GameState
from ..knowledge.comp_database import ARCHETYPES, MetaComp
from .item_advisor import ItemRecipes
from .scoring.board_fit import COMPONENT_CARRY_TYPE, trait_key
from .scoring.types import clamp01

FAST_ARCHETYPES = ("fast8", "fast9")


# -- kieu doi hinh --------------------------------------------------------------


def resolve_archetype(comp: MetaComp) -> str:
    """Kieu doi hinh CHI lay tu nhan cua nguon (TFT Academy). Khong co -> "".

    KHONG suy tu gia tuong loi. Da do tren 51 doi hinh co nhan chuyen gia: luat
    "ti le tuong 4-5 vang" chi dung 26, SAI 7, bo phieu trang 18. Ly do: board
    cuoi cua doi hinh reroll van co 2-4 tuong dat tien de tron form (VD Rengar
    Reroll: ba tuong 4 vang + mot tuong 5 vang). Gan nham reroll thanh fast 8 lam
    trong so tuong loi ve 0 - sai nang hon nhieu so voi roi ve trong so co dinh.
    """
    return comp.archetype if comp.archetype in ARCHETYPES else ""


# -- do: huong AP / AD ------------------------------------------------------------


def component_type(component: str) -> str | None:
    """`DA_Component_BFSword` / `BFSword` -> "AD". Manh khong chi huong -> None."""
    key = re.sub(r"^(DA_Component_|TFT_Item_)", "", component)
    return COMPONENT_CARRY_TYPE.get(key)


def is_emblem(item: str) -> bool:
    return "emblem" in item.lower()


@dataclass
class ItemProfile:
    """Khoi luong do tan cong theo loai. Do tank co tinh nhung khong chi huong."""

    ad: float = 0.0
    ap: float = 0.0

    @property
    def mass(self) -> float:
        return self.ad + self.ap

    @property
    def ap_share(self) -> float | None:
        return self.ap / self.mass if self.mass else None

    @property
    def lean(self) -> str:
        share = self.ap_share
        if share is None:
            return "chưa rõ"
        if share >= 0.65:
            return "AP"
        if share <= 0.35:
            return "AD"
        return "lai AP/AD"


def item_profile(
    completed: Iterable[str],
    components: Iterable[str],
    recipes: ItemRecipes,
    component_weight: float,
) -> ItemProfile:
    """Cong khoi luong AP/AD. Do da ghep = 1.0 chia deu cho hai manh cua no.

    Do khong co trong bang cong thuc thi KHONG doan loai - bo qua. An bi bo qua
    o day vi no la tin hieu trait, khong phai tin hieu loai carry.
    """
    by_item = {r.item: r.components for r in recipes.recipes}
    profile = ItemProfile()

    def add(kind: str | None, amount: float) -> None:
        if kind == "AD":
            profile.ad += amount
        elif kind == "AP":
            profile.ap += amount

    for item in completed:
        if is_emblem(item) or item not in by_item:
            continue
        parts = by_item[item]
        for part in parts:
            add(component_type(part), 1.0 / len(parts))
    for component in components:
        add(component_type(component), component_weight)
    return profile


# -- bang tra cuu sinh boi scripts/build_game_tables.py ---------------------------


def load_unit_costs(path: str | Path) -> dict[str, int]:
    """Doc data/champion_costs.json. Khong co file -> rong (tien mua tuong = 0)."""
    p = Path(path)
    if not p.exists():
        return {}
    payload = json.loads(p.read_text(encoding="utf-8"))
    return {k: int(v) for k, v in (payload.get("costs") or {}).items()}


# -- an ---------------------------------------------------------------------------


def load_item_stats(path: str | Path) -> dict[str, dict[str, Any]]:
    """Doc `items` tu data/tactics_tools_stats.json. Khong co file -> rong."""
    p = Path(path)
    if not p.exists():
        return {}
    payload = json.loads(p.read_text(encoding="utf-8"))
    return {row["api_name"]: row for row in payload.get("items", []) if row.get("api_name")}


def emblem_trait(item: str) -> str:
    """`DA_18_EmblemFae` -> khoa trait "fae"."""
    return trait_key(re.sub(r"emblem", "", item, flags=re.I))


# -- kinh te xoay bai -------------------------------------------------------------


def stage_index(stage: str) -> tuple[int, int]:
    m = RE_STAGE.match(stage)
    return (int(m.group(1)), int(m.group(2))) if m else (1, 1)


def _xp_table(economy: Mapping[str, Any]) -> dict[int, int]:
    return {int(k): int(v) for k, v in (economy.get("xp_to_next") or {}).items()}


def xp_to_level(state: GameState, target_level: int, economy: Mapping[str, Any]) -> int:
    """XP con thieu de len `target_level`.

    Cap dang dung: lay MAU SO TREN THANH XP (so cua client) neu doc duoc. Cac
    cap sau do: bang XP - man hinh chi hien cap ke tiep.
    """
    if state.level >= target_level:
        return 0
    table = _xp_table(economy)
    current = state.xp_needed if state.xp_needed else table.get(state.level, 0)
    later = sum(table.get(lvl, 0) for lvl in range(state.level + 1, target_level))
    return max(0, current - state.xp) + later


def gold_to_level(state: GameState, target_level: int, economy: Mapping[str, Any]) -> int:
    """Tien mua XP de len `target_level`. Bo qua XP tu nhien (+2 moi vong)."""
    need = xp_to_level(state, target_level, economy)
    xp_per_buy = int(economy.get("xp_per_buy", 4))
    gold_per_buy = int(economy.get("gold_per_buy", 4))
    return math.ceil(need / xp_per_buy) * gold_per_buy if need > 0 else 0


def xp_table_mismatch(state: GameState, economy: Mapping[str, Any]) -> str:
    """So mau so tren thanh XP voi bang XP. Lech -> chuoi canh bao, khop -> ""."""
    expected = _xp_table(economy).get(state.level)
    if not state.xp_needed or expected is None or expected == state.xp_needed:
        return ""
    return (
        f"Bảng XP lệch client: cấp {state.level}→{state.level + 1} trên màn hình cần "
        f"{state.xp_needed}, bảng ghi {expected} — đang dùng số trên màn hình"
    )


@dataclass
class PivotReadiness:
    """Trang thai xoay bai cua fast 8/9.

    Hai dai luong TACH RIENG co chu dich:
        pivoted - DA xoay that chua (len cap muc tieu, hoac toi han chot).
                  Chi cai nay doi trong so tuong loi.
        value   - du tien xoay bai den dau (0..1). Chi de HIEN THI thoi diem.

    Tung dung `value` de noi suy trong so va xep hang bi nguoc: comp cang thieu
    tien thi trong so tuong loi cang thap, nen cang it bi tru vi thieu tuong -
    fast 9 xa tam voi vuot len tren fast 8 sap xoay duoc.
    """

    pivoted: bool
    value: float
    reason: str


def pivot_readiness(
    archetype: str,
    state: GameState,
    missing_units: Iterable[str],
    unit_costs: Mapping[str, int],
    pivot: Mapping[str, Any],
    economy: Mapping[str, Any],
) -> PivotReadiness:
    """Tinh cho fast8/fast9. Reroll khong co khai niem xoay bai -> da xoay."""
    rule = pivot.get(archetype)
    if not rule:
        return PivotReadiness(True, 1.0, "")

    target = int(rule["target_level"])
    now = stage_index(state.stage)
    start = stage_index(str(rule["window_start"]))
    deadline = stage_index(str(rule["deadline"]))

    if state.level >= target:
        return PivotReadiness(True, 1.0, f"Đã lên cấp {target} — board phải là đội hình thật")
    if now >= deadline:
        return PivotReadiness(True, 1.0, f"Đã tới {rule['deadline']} — muộn nhất phải xoay bài")
    if now < start:
        return PivotReadiness(
            False,
            0.0,
            f"Chưa tới giai đoạn xoay bài ({rule['window_start']}) — "
            "giữ board mạnh bất kỳ để giữ máu và tích tiền",
        )

    level_gold = gold_to_level(state, target, economy)
    unit_gold = sum(unit_costs.get(u, 0) for u in missing_units)
    need = level_gold + unit_gold
    value = 1.0 if need <= 0 else clamp01(state.gold / need)
    verdict = "đủ tiền xoay bài" if value >= 1.0 else f"thiếu {need - state.gold} vàng"
    xp_source = "thanh XP" if state.xp_needed else "bảng XP"
    reason = (
        f"Trong giai đoạn xoay bài (muộn nhất {rule['deadline']}): có {state.gold}/{need} vàng, "
        f"{verdict} (lên {target}: {level_gold} theo {xp_source}, mua tướng: {unit_gold}; "
        "chưa tính tiền roll)"
    )
    mismatch = xp_table_mismatch(state, economy)
    return PivotReadiness(False, value, f"{reason}. {mismatch}" if mismatch else reason)
