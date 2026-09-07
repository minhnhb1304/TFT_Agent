"""ScenarioLogger - nen mong cua ba trong bon phuong phap danh gia (SPEC 12.0).

VI SAO NO SHIP SOM CHU KHONG PHAI CUOI

SPEC 12.2 (tuong quan placement), 12.3 (dong thuan chuyen gia) va 12.4
(ablation) deu an CHUNG MOT dataset do file nay sinh ra. Neu logger ra o phase
cuoi thi den luc danh gia se khong co du lieu, va deadline do an khong tha cho
viec do. Logger chay som = dataset tu tich luy trong luc con dang code phan khac.

SCHEMA 2 - THEM `game_id` (2026-09-06)

`final_placement` la dai luong CUA MOT TRAN, khong phai cua mot quyet dinh.
Ba scenario trong cung mot van deu mang dung mot gia tri Y. Neu SPEC 12.2 coi
chung la ba quan sat doc lap thi sai so chuan bi danh gia thap va p-value tro
nen de dai (anti-conservative). Muon hoan vi theo khoi cho dung thi phai biet
scenario nao thuoc van nao - do la viec cua `game_id`.

Doc file schema 1 van chay: `game_id` khuyet thi bang None, va `correlation`
se bao ro la khong gom cum duoc thay vi im lang gia vo la doc lap.

MOI BAN GHI PHAI TU DU DE CHAM DIEM LAI

Ablation study cham diem lai toan bo dataset voi trong so khac. Muon lam duoc
the thi ban ghi phai chua DU GameState, khong phai chi ket qua. Do la ly do
`game_state` duoc ghi day du chu khong tom tat.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator

from ..game_state.models import GameState, state_from_dict

SCHEMA_VERSION = 3


@dataclass
class RecognizedAugment:
    """Mot augment doc duoc tren man chon, kem do tin cay va co map mo."""

    api_name: str
    confidence: float = 1.0
    ambiguous: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "api_name": self.api_name,
            "confidence": self.confidence,
            "ambiguous": self.ambiguous,
        }


@dataclass
class Scenario:
    """Mot ban ghi quyet dinh - don vi cua toan bo phan danh gia."""

    ts: str
    game_state: GameState
    recognized: list[RecognizedAugment] = field(default_factory=list)
    component_scores: dict[str, dict[str, float]] = field(default_factory=dict)
    ranking: list[str] = field(default_factory=list)
    weights: dict[str, float] = field(default_factory=dict)
    frame_ref: str | None = None
    player_pick: str | None = None
    final_placement: int | None = None
    game_id: str | None = None
    # Khuyen nghi doi the tai thoi diem nay (schema 3, SPEC 3.5.5). None khi
    # chinh sach reroll khong chay - moi ban ghi schema 1/2 deu nhu vay.
    reroll: dict[str, Any] | None = None
    path: Path | None = None
    schema_version: int = SCHEMA_VERSION

    @property
    def pick_rank(self) -> int | None:
        """Thu hang ma advisor gan cho augment nguoi choi DA chon (1 = cao nhat).

        Day chinh la bien doc lap cua SPEC 12.2. None khi chua biet nguoi choi
        chon gi, hoac khi lua chon do khong nam trong xep hang.
        """
        if not self.player_pick or self.player_pick not in self.ranking:
            return None
        return self.ranking.index(self.player_pick) + 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "ts": self.ts,
            "frame_ref": self.frame_ref,
            "recognized": [r.to_dict() for r in self.recognized],
            "game_state": self.game_state.to_dict(),
            "component_scores": self.component_scores,
            "ranking": self.ranking,
            "weights": self.weights,
            "player_pick": self.player_pick,
            "final_placement": self.final_placement,
            "game_id": self.game_id,
            "reroll": self.reroll,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], path: Path | None = None) -> "Scenario":
        return cls(
            ts=data.get("ts", ""),
            game_state=state_from_dict(data.get("game_state", {})),
            recognized=[RecognizedAugment(**r) for r in data.get("recognized", [])],
            component_scores=data.get("component_scores", {}),
            ranking=list(data.get("ranking", [])),
            weights=data.get("weights", {}),
            frame_ref=data.get("frame_ref"),
            player_pick=data.get("player_pick"),
            final_placement=data.get("final_placement"),
            game_id=data.get("game_id"),
            reroll=data.get("reroll"),
            path=path,
            schema_version=int(data.get("schema_version", 1)),
        )


class ScenarioLogger:
    """Ghi mot file JSON cho moi quyet dinh augment."""

    def __init__(
        self,
        directory: str | Path = "data/scenarios",
        enabled: bool = True,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.directory = Path(directory)
        self.enabled = enabled
        # Dong ho tiem vao duoc: test can ten file tat dinh, va thoi gian la
        # thu duy nhat trong ban ghi nay khong tai lap duoc.
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def log(
        self,
        ranking: Any,
        state: GameState,
        recognized: Iterable[RecognizedAugment] | None = None,
        frame_ref: str | None = None,
        player_pick: str | None = None,
        game_id: str | None = None,
        reroll: Any = None,
    ) -> Path | None:
        """Ghi mot scenario. Tra ve duong dan, hoac None khi logger dang tat."""
        if not self.enabled:
            return None

        now = self.clock()
        scenario = Scenario(
            ts=now.isoformat(timespec="milliseconds"),
            game_state=state,
            recognized=list(recognized or self._infer_recognized(ranking)),
            component_scores=ranking.component_scores(),
            ranking=list(ranking.order),
            weights=dict(getattr(ranking, "weights", {})),
            frame_ref=frame_ref,
            player_pick=player_pick,
            game_id=game_id,
            reroll=reroll.to_dict() if hasattr(reroll, "to_dict") else reroll,
        )

        self.directory.mkdir(parents=True, exist_ok=True)
        name = now.strftime("%Y%m%dT%H%M%S%f")[:-3] + ".json"
        path = self.directory / name
        path.write_text(
            json.dumps(scenario.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        scenario.path = path
        return path

    @staticmethod
    def _infer_recognized(ranking: Any) -> list[RecognizedAugment]:
        """Khi reader khong truyen vao, suy ra tu chinh xep hang."""
        return [
            RecognizedAugment(e.api_name, e.confidence, e.ambiguous)
            for e in getattr(ranking, "entries", [])
        ]

    # -- doc lai -----------------------------------------------------------

    def load_all(self) -> list[Scenario]:
        return load_scenarios(self.directory)

    def back_fill_placement(self, path: str | Path, placement: int) -> Scenario:
        """Dien ket qua that sau tran (SPEC 12.0 - lay tu tft-match-v1).

        Ghi de tai cho: mot scenario chi co dung mot placement that, va giu hai
        ban sao cua cung mot su kien la cach chac chan de sau nay dem trung.
        """
        p = Path(path)
        data = json.loads(p.read_text(encoding="utf-8"))
        data["final_placement"] = int(placement)
        p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return Scenario.from_dict(data, p)


def load_scenarios(directory: str | Path) -> list[Scenario]:
    """Nap toan bo scenario trong mot thu muc, sap theo thoi gian.

    File hong bi BO QUA co y: mot ban ghi loi khong duoc lam sap ca dot danh
    gia - nhung so luong bo qua duoc dem lai o `count_unreadable()`.
    """
    out: list[Scenario] = []
    for path in sorted(Path(directory).glob("*.json")):
        try:
            out.append(Scenario.from_dict(json.loads(path.read_text(encoding="utf-8")), path))
        except (json.JSONDecodeError, TypeError, ValueError):
            continue
    return out


def count_unreadable(directory: str | Path) -> int:
    """So file JSON khong doc duoc - phai bao cao kem moi so lieu danh gia."""
    bad = 0
    for path in Path(directory).glob("*.json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            bad += 1
    return bad


def iter_labelled(scenarios: Iterable[Scenario]) -> Iterator[Scenario]:
    """Chi cac scenario da co CA lua chon nguoi choi LAN placement that."""
    for s in scenarios:
        if s.player_pick and s.final_placement:
            yield s
