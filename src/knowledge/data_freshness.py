"""Du lieu con hop patch khong - kiem OFFLINE, luc chay.

VI SAO MODULE NAY TON TAI
    Moi bang trong data/ la anh chup cua MOT patch. Sang patch moi, file cu
    van nap binh thuong va advisor van tu van tu tin tren so da het han - khong
    co gi no ra. Module nay bien "da cu" thanh mot tin hieu nhin thay duoc.

KHONG CHAM MANG
    "Patch hien tai" doc tu data/patch_state.json, do scripts/refresh_data.py
    ghi sau khi hoi cac nguon. Runtime chi so file voi file (SPEC 3.5.3).

QUY TAC PHAN XU - theo thu tu
    1. File khong ton tai                          -> missing
    2. Bang theo SET (ten, gia tuong, cong thuc):
         meta.set khac set cua patch hien tai       -> stale
         khong co meta.set                          -> unknown
    3. Bang theo PATCH, co chuoi patch doc duoc (18.1d):
         nho hon patch hien tai                     -> stale
    4. Bang theo PATCH, khong co chuoi patch (tactics.tools dung ma so 16170):
         generated_at truoc ngay ra patch           -> stale
    5. Con lai                                      -> fresh / unknown

    "18.2" < "18.2b": ban va chu cai la ban va can bang that, doi duoc tier.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

FRESH, STALE, MISSING, UNKNOWN, UNREADABLE = "fresh", "stale", "missing", "unknown", "unreadable"

_PATCH_RE = re.compile(r"^(\d+)\.(\d+)([a-z]?)$")


def parse_patch(value: Any) -> tuple[int, int, str] | None:
    """'18.1d' -> (18, 1, 'd'). Tra None cho moi thu khong phai patch Riot."""
    if not isinstance(value, str):
        return None
    m = _PATCH_RE.match(value.strip())
    return (int(m.group(1)), int(m.group(2)), m.group(3)) if m else None


def latest_patch(values: list[Any]) -> str | None:
    """Patch lon nhat trong cac phieu. Nguon co the tre, nhung khong bao patch chua ra."""
    parsed = [(parse_patch(v), v.strip()) for v in values if parse_patch(v)]
    return max(parsed)[1] if parsed else None


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


@dataclass(frozen=True)
class PatchState:
    """Noi dung data/patch_state.json."""

    current_patch: str
    released_at: str | None = None

    @property
    def set_name(self) -> str:
        return f"TFTSet{parse_patch(self.current_patch)[0]}"

    @classmethod
    def load(cls, path: Path) -> "PatchState | None":
        """Thieu file hoac patch khong doc duoc -> None: chua biet thi khong phan xu."""
        if not path.exists():
            return None
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not parse_patch(raw.get("current_patch")):
            return None
        return cls(raw["current_patch"], raw.get("released_at"))


@dataclass(frozen=True)
class Dataset:
    """Mot bang du lieu ma runtime doc.

    settings_key: khoa trong `paths` cua settings.yaml; None thi dung `path`.
    scope: "set" (doi moi set) hoac "patch" (doi moi ban va).
    patch_field: ten truong trong `meta` chua chuoi patch.
    """

    name: str
    scope: str
    settings_key: str | None = None
    path: str | None = None
    patch_field: str = "patch"


DATASETS: tuple[Dataset, ...] = (
    Dataset("augment_features", "set", settings_key="augment_features"),
    Dataset("name_index", "set", settings_key="name_index"),
    Dataset("champion_costs", "set", settings_key="champion_costs"),
    Dataset("item_recipes", "set", settings_key="item_recipes"),
    Dataset("augment_tiers", "patch", settings_key="augment_tiers"),
    Dataset("augment_tiers_backup", "patch", settings_key="augment_tiers_backup"),
    Dataset("meta_comps", "patch", settings_key="meta_comps"),
    Dataset("meta_comps_backup", "patch", settings_key="meta_comps_backup"),
    Dataset("item_stats", "patch", settings_key="item_stats"),
    Dataset("lolchess_guide", "patch", path="data/lolchess_guide.json", patch_field="latest_patch"),
)


@dataclass(frozen=True)
class Freshness:
    dataset: str
    path: Path
    status: str
    detail: str

    def warning(self) -> str:
        return f"{self.dataset}: {self.detail} ({self.path.name})"


def judge(dataset: Dataset, path: Path, state: PatchState) -> Freshness:
    """Phan xu mot file theo QUY TAC o docstring module."""
    if not path.exists():
        return Freshness(dataset.name, path, MISSING, "khong co file")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return Freshness(dataset.name, path, UNREADABLE, f"khong doc duoc: {exc}")
    meta = payload.get("meta") if isinstance(payload, dict) else None
    meta = meta if isinstance(meta, dict) else {}

    if dataset.scope == "set":
        data_set = meta.get("set")
        if not data_set:
            return Freshness(dataset.name, path, UNKNOWN, "khong ghi set")
        if data_set != state.set_name:
            return Freshness(dataset.name, path, STALE, f"set {data_set} != {state.set_name}")
        return Freshness(dataset.name, path, FRESH, f"set {data_set}")

    data_patch = meta.get(dataset.patch_field)
    parsed = parse_patch(data_patch)
    if parsed:
        if parsed < parse_patch(state.current_patch):
            return Freshness(dataset.name, path, STALE, f"patch {data_patch} < {state.current_patch}")
        return Freshness(dataset.name, path, FRESH, f"patch {data_patch}")

    generated = _parse_time(meta.get("generated_at") or meta.get("fetched_at") or meta.get("crawled_at"))
    released = _parse_time(state.released_at)
    if generated and released:
        if generated < released:
            return Freshness(
                dataset.name, path, STALE,
                f"sinh {generated.date()} truoc khi ra patch {state.current_patch} ({released.date()})",
            )
        return Freshness(dataset.name, path, FRESH, f"sinh {generated.date()}")
    return Freshness(dataset.name, path, UNKNOWN, "khong co patch lan ngay sinh de so")


def check_all(settings: Any, datasets: tuple[Dataset, ...] = DATASETS) -> tuple[PatchState | None, list[Freshness]]:
    """Phan xu moi bang runtime doc. Chua co patch_state.json thi tra danh sach rong."""
    state = PatchState.load(settings.path("patch_state"))
    if state is None:
        return None, []
    results = []
    for ds in datasets:
        path = settings.path(ds.settings_key) if ds.settings_key else settings.root / ds.path
        results.append(judge(ds, path, state))
    return state, results


def stale_warnings(settings: Any) -> list[str]:
    """Chuoi canh bao cho AdviceBundle.stale_data - chi cac bang da CU, khong ke unknown."""
    _, results = check_all(settings)
    return [r.warning() for r in results if r.status in (STALE, UNREADABLE)]
