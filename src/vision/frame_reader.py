"""Bo doc hop nhat khung hinh (SPEC 3.1, 3.2, 3.3).

Diem hop nhat duy nhat cua ba chan thi giac:
1. HudReader: doc stage, hp, gold, level, xp va cap nhat GameStateTracker.
2. AugmentReader: doc ten the bai, toc he va sinh AugmentChoice.
3. RerollButtonReader: doc trang thai 3 nut doi the thanh RerollState.

Nguyen tac co lap loi: mot chan hong chi suy giam (degrade) vao `degraded`,
khong lam sap toan bo tien trinh doc khung hinh.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time
from typing import Any, Callable

import numpy as np

from ..capture.regions import ScreenRegions
from ..decision.augment_advisor import AugmentChoice
from ..decision.reroll_policy import RerollState
from ..game_state.models import GameState
from ..game_state.state_tracker import GameStateTracker
from ..utils.settings import Settings
from .augment_reader import AugmentReader, AugmentReading, DEFAULT_MODEL, DEFAULT_NAME_INDEX, DEFAULT_TIMEOUT_S
from .hud_reader import DEFAULT_REGIONS, HudReader, HudReading
from .reroll_buttons import DEFAULT_TEMPLATE, RerollButtonReader, RerollButtonReading


class FrameReadError(RuntimeError):
    """Loi nghiem trong khi doc khung hinh hoac cau hinh khong hop le."""


@dataclass(frozen=True)
class FrameReading:
    """Ket qua doc hop nhat tu mot khung hinh."""

    state: GameState
    choices: list[AugmentChoice]
    rerolls: RerollState | None
    degraded: list[str]
    latency_ms: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.__dict__,
            "choices": [
                {
                    "api_names": c.api_names,
                    "confidence": c.confidence,
                    "display_name": c.display_name,
                    "ambiguous": c.ambiguous,
                }
                for c in self.choices
            ],
            "rerolls": {
                "available": list(self.rerolls.available),
                "burned": list(self.rerolls.burned),
            } if self.rerolls else None,
            "degraded": list(self.degraded),
            "latency_ms": {k: round(v, 2) for k, v in self.latency_ms.items()},
        }


class FrameReader:
    """Hop nhat 3 chan thi giac va GameStateTracker vao mot loi goi duy nhat."""

    def __init__(
        self,
        hud_reader: HudReader,
        augment_reader: AugmentReader,
        reroll_reader: RerollButtonReader,
        *,
        tracker: GameStateTracker | None = None,
    ) -> None:
        self.hud_reader = hud_reader
        self.augment_reader = augment_reader
        self.reroll_reader = reroll_reader
        self.tracker = tracker or GameStateTracker()

    @classmethod
    def load(
        cls,
        regions: ScreenRegions | str | Path = DEFAULT_REGIONS,
        *,
        settings: Settings | None = None,
        template: str | Path = DEFAULT_TEMPLATE,
        names: str | Path = DEFAULT_NAME_INDEX,
        model: str | None = None,
        timeout_s: float | None = None,
        enable_gemini_vision: bool | None = None,
        hud_call: Callable[[Any], Any] | None = None,
        augment_call: Callable[[bytes], str] | None = None,
        tracker: GameStateTracker | None = None,
        vote_window: int | None = None,
        **kw: Any,
    ) -> FrameReader:
        """Khoi tao FrameReader tu cac duong dan cau hinh va mau glyph."""
        s = settings or Settings.load()
        model_val = model if model is not None else s.gemini_model
        timeout_val = timeout_s if timeout_s is not None else s.gemini_timeout_s
        window_val = vote_window if vote_window is not None else s.vote_window
        enable_vision = enable_gemini_vision if enable_gemini_vision is not None else s.enable_gemini_vision

        regs = regions if isinstance(regions, ScreenRegions) else ScreenRegions.load(regions)
        hud_r = kw.get("hud_reader") or HudReader.load(regs, call=hud_call)
        aug_r = kw.get("augment_reader") or AugmentReader.load(
            regs,
            names=names,
            model=model_val,
            timeout_s=timeout_val,
            enable_gemini_vision=enable_vision,
            call=augment_call,
        )
        reroll_r = kw.get("reroll_reader") or RerollButtonReader.load(regs, template=template)
        trk = tracker or kw.get("tracker") or GameStateTracker(window=window_val)
        return cls(hud_r, aug_r, reroll_r, tracker=trk)

    def read(
        self,
        frame: np.ndarray,
        *,
        tracker: GameStateTracker | None = None,
    ) -> FrameReading:
        """Doc dong thoi ca 3 chan thi giac tu mot khung hinh BGR."""
        if frame is None or frame.size == 0:
            raise FrameReadError("khung hình rỗng — kiểm tra lại nguồn ảnh")

        act_tracker = tracker if tracker is not None else self.tracker
        degraded: list[str] = []
        latency_ms: dict[str, float] = {}

        # 1. Chan Augment + Traits
        t_aug = time.perf_counter()
        choices: list[AugmentChoice] = []
        traits: dict[str, int] = {}
        try:
            aug_reading: AugmentReading = self.augment_reader.read(frame)
            latency_ms["augment"] = (time.perf_counter() - t_aug) * 1000.0
            traits = aug_reading.traits
            for card in aug_reading.cards:
                if card.api_names:
                    choices.append(
                        AugmentChoice(
                            api_names=list(card.api_names),
                            confidence=card.confidence,
                            display_name=card.title,
                        )
                    )
                else:
                    degraded.append(f"ô {card.slot + 1}: {card.reason}")
        except Exception as exc:
            latency_ms["augment"] = (time.perf_counter() - t_aug) * 1000.0
            degraded.append(f"augment: {exc}")

        # 2. Chan HUD -> GameState qua tracker
        t_hud = time.perf_counter()
        try:
            hud_reading: HudReading = self.hud_reader.read(frame)
            latency_ms["hud"] = (time.perf_counter() - t_hud) * 1000.0
            act_tracker.update(hud_reading)
        except Exception as exc:
            latency_ms["hud"] = (time.perf_counter() - t_hud) * 1000.0
            degraded.append(f"hud: {exc}")

        state = act_tracker.state(traits=traits)

        # Dua cac truong stale va never_seen vao degraded
        for f in act_tracker.stale:
            degraded.append(f"{f}: stale")
        for f in act_tracker.never_seen:
            degraded.append(f"{f}: never_seen")

        # 3. Chan nut Reroll
        t_reroll = time.perf_counter()
        rerolls: RerollState | None = None
        try:
            reroll_reading: RerollButtonReading = self.reroll_reader.read(frame)
            latency_ms["rerolls"] = (time.perf_counter() - t_reroll) * 1000.0
            if reroll_reading.screen_present and reroll_reading.settled:
                rerolls = reroll_reading.to_reroll_state()
            else:
                for r in reroll_reading.reads:
                    if not r.settled or r.state in ("unknown", "pressed"):
                        degraded.append(f"reroll_slot_{r.slot}: {r.reason}")
        except Exception as exc:
            latency_ms["rerolls"] = (time.perf_counter() - t_reroll) * 1000.0
            degraded.append(f"rerolls: {exc}")

        return FrameReading(
            state=state,
            choices=choices,
            rerolls=rerolls,
            degraded=degraded,
            latency_ms=latency_ms,
        )
