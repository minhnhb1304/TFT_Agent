"""Nap config/settings.yaml (SPEC 5).

Mot cho duy nhat doc file cau hinh. Moi module khac nhan gia tri qua tham so
constructor chu khong tu doc file - nho the test dung duoc cau hinh tong hop
ma khong phai ghi file tam, va khong module nao co the am tham bat mot co ma
cho con lai khong biet.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULT_PATH = "config/settings.yaml"

DEFAULTS: dict[str, Any] = {
    "paths": {
        "augment_features": "data/augment_features.json",
        "augment_stats_csv": "data/augment_stats.csv",
        "scoring_weights": "config/scoring_weights.yaml",
        "meta_comps": "data/meta_comps.json",
        "item_recipes": "data/item_recipes.json",
        "name_index": "data/name_index.json",
        "scenarios": "data/scenarios",
        "cdragon_cache": "data/cdragon_cache",
    },
    "locale": {"language": "vi_vn", "branch": "latest"},
    # Nguon crawl cho scripts/crawl_augment_stats.py. Chi dung OFFLINE luc
    # sinh du lieu - runtime khong bao gio goi Riot API (SPEC 3.5.3).
    "riot": {"platform": "vn2", "tiers": ["challenger", "grandmaster", "master"]},
    # Hotkey toan cuc. BAT BUOC di qua RegisterHotKey cua Win32 goi tu Qt
    # (SPEC 1.3): no la co che cap OS, KHONG cai hook WH_KEYBOARD_LL va
    # KHONG can quyen admin. Thu vien `keyboard` lam nguoc lai ca hai.
    "hotkeys": {
        "toggle_visibility": "F1",
        "toggle_click_through": "F2",
        "force_refresh": "F3",
        "toggle_detail": "F4",
        "quit": "Ctrl+Q",
    },
    "features": {
        "enable_scouting": False,
        "enable_llm_refinement": False,
        "llm_model": "gemini-3.5-flash-lite",
        "llm_hard_timeout_s": 2.0,
        "allow_unverified_roll_odds": False,
    },
    "logging": {"log_scenarios": True, "save_frames": False},
}


@dataclass
class Settings:
    """Cau hinh da nap, kem duong dan goc de resolve cac path tuong doi."""

    data: dict[str, Any] = field(default_factory=lambda: _deep_copy(DEFAULTS))
    root: Path = field(default_factory=Path)

    @classmethod
    def load(cls, path: str | Path = DEFAULT_PATH) -> "Settings":
        """Nap file, gop len tren gia tri mac dinh.

        Thieu file KHONG phai loi: toan bo mac dinh deu an toan (scouting tat,
        LLM tat, roll odds chua xac minh bi chan), nen he thong van chay dung.
        """
        p = Path(path)
        merged = _deep_copy(DEFAULTS)
        if p.exists():
            loaded = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            _deep_update(merged, loaded)
        root = p.resolve().parent.parent if p.exists() else Path.cwd()
        return cls(merged, root)

    def get(self, section: str, key: str, default: Any = None) -> Any:
        return (self.data.get(section) or {}).get(key, default)

    def path(self, key: str) -> Path:
        """Duong dan trong muc `paths`, resolve theo goc du an."""
        raw = self.get("paths", key, "")
        p = Path(raw)
        return p if p.is_absolute() else self.root / p

    # Cac co duoc truy cap nhieu nhat, de o day cho goi ngan va de grep.

    @property
    def enable_scouting(self) -> bool:
        return bool(self.get("features", "enable_scouting", False))

    @property
    def enable_llm_refinement(self) -> bool:
        return bool(self.get("features", "enable_llm_refinement", False))

    @property
    def allow_unverified_roll_odds(self) -> bool:
        return bool(self.get("features", "allow_unverified_roll_odds", False))

    @property
    def log_scenarios(self) -> bool:
        return bool(self.get("logging", "log_scenarios", True))


def _deep_copy(data: dict[str, Any]) -> dict[str, Any]:
    return {k: (_deep_copy(v) if isinstance(v, dict) else v) for k, v in data.items()}


def _deep_update(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)
        else:
            target[key] = value
