"""Co so du lieu doi hinh meta (SPEC 3.4).

MOT QUYET DINH QUAN TRONG: module nay KHONG di kem du lieu meta cua Set 18.

Ly do: khong co nguon so lieu meta nao da duoc xac minh cho 18.1 tai thoi diem
viet. Nhet mot bang tier list tu bia vao repo se cho ra mot he thong chay muot
va tu van sai - dung kieu hong nguy hiem nhat cua du an nay. Thay vao do:

    - file du lieu la DAU VAO (data/meta_comps.json), khong phai hang so;
    - khong co file -> database RONG, comp selector tu bao "chua co du lieu meta";
    - moi comp bat buoc mang `source` va `sample_n` de biet no den tu dau.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Iterable


@dataclass
class MetaComp:
    """Mot doi hinh meta kem provenance."""

    name: str
    tier: str = "?"                       # S / A / B ... tuy nguon
    core_units: list[str] = field(default_factory=list)
    flex_units: list[str] = field(default_factory=list)
    core_items: list[str] = field(default_factory=list)
    best_augments: list[str] = field(default_factory=list)
    traits: dict[str, int] = field(default_factory=dict)
    avg_placement: float = 4.5
    top4_rate: float = 0.5
    win_rate: float = 0.125
    play_rate: float = 0.0
    level_timing: dict[str, int] = field(default_factory=dict)
    early_game: list[str] = field(default_factory=list)
    positioning_notes: str = ""
    source: str = "unknown"
    sample_n: int = 0

    @property
    def is_evidence(self) -> bool:
        """Co du co mau de dua vao khuyen nghi khong (cung nguong voi stats)."""
        return self.sample_n >= 200

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CompDatabase:
    """Tap doi hinh meta da nap. Rong la trang thai hop le."""

    def __init__(self, comps: Iterable[MetaComp] = (), meta: dict[str, Any] | None = None) -> None:
        self.comps = list(comps)
        self.meta = meta or {}

    def __len__(self) -> int:
        return len(self.comps)

    def __iter__(self):
        return iter(self.comps)

    @property
    def is_empty(self) -> bool:
        return not self.comps

    def get(self, name: str) -> MetaComp | None:
        return next((c for c in self.comps if c.name == name), None)

    @property
    def sources(self) -> list[str]:
        """Cac nguon dang gop trong database - hien kem moi khuyen nghi."""
        return sorted({c.source for c in self.comps})

    @classmethod
    def load(cls, path: str | Path) -> "CompDatabase":
        """Nap tu JSON. File khong ton tai -> database rong, KHONG raise.

        Khong raise la co y: thieu du lieu meta lam giam chat luong khuyen nghi
        nhung khong duoc phep lam sap ca advisor - augment advisor (trong tam
        do an) van chay duoc ma khong can meta comp nao.
        """
        p = Path(path)
        if not p.exists():
            return cls([], {"note": f"khong tim thay {p} - database rong"})
        payload = json.loads(p.read_text(encoding="utf-8"))
        comps = [MetaComp(**c) for c in payload.get("comps", [])]
        return cls(comps, payload.get("meta", {}))

    def save(self, path: str | Path, meta: dict[str, Any] | None = None) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = {"meta": meta or self.meta, "comps": [c.to_dict() for c in self.comps]}
        p.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
