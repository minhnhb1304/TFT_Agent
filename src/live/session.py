"""Vong lap doc khung hinh -> loi khuyen, dung chung cho replay va live (moc M1).

KHONG Qt, KHONG chup man hinh, KHONG thread. Chi: nhan mot `Frame`, tra ve mot
`LiveEvent`. Nho vay hanh vi tren ban record BANG hanh vi trong tran - hai vo
chi khac nhau o nguon khung hinh va cach hien.

BON QUY TAC RUT RA TU BUOI TEST 2026-09-16 (docs/playtest-fixes/eval-dataset.md):

1. DOC LAI SAU MOI LAN REROLL. Doc mot lan luc mo man thi 0/16 lan reroll bat
   duoc, va 18 o hien SAI ma khong bao gi.
2. DOC HUD NGOAI MAN CHON AUGMENT. Man chon augment che mat vang/cap/XP, nen
   doc dung luc do thi khong bao gio co so that.
3. AN MAN CHON AUGMENT KHONG PHAI LA DONG MAN. Nguoi choi an ~10 s de xem ban
   co roi mo lai; coi do la man moi thi mat sach luot reroll da dung.
4. VO KHONG TU DUNG GameState. State di kem su kien, dung cai da dung de tinh.

Doc HUD ton ~1 s (5 lan OCR), nen truoc moi lan doc co mot phep kiem RE: vung
HUD co doi so voi lan doc truoc khong. Pixel y nguyen thi so cung y nguyen.
Trong tran, dieu do cat phan lon cong doc khi nguoi choi dang cho; khi tua
video no la khac biet giua 12 phut va vai phut cho mot van 36 phut.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Sequence

from ..capture.frame_source import Frame
from ..capture.regions import ScreenRegions
from ..decision.augment_advisor import AugmentChoice
from ..decision.reroll_policy import RerollState
from ..game_state.state_tracker import GameStateTracker
from ..vision.augment_reader import CardRead
from .card_reader import SLOTS, CardReader
from .events import AdviceReady, Cleared, Idle, LiveEvent, Status
from .screen_tracker import AugmentScreenTracker, thumb_diff

# O HUD dung de nhan ra "khung nay khong co gi moi de doc".
HUD_SIGNATURE_FIELDS = ("gold", "level", "xp", "hp", "stage")


@dataclass
class LiveSession:
    """May trang thai cua mot phien doc man chon augment."""

    card_reader: CardReader
    hud_reader: Any
    reroll_reader: Any
    advisor: Any
    regions: ScreenRegions
    game_tracker: GameStateTracker = field(default_factory=GameStateTracker)
    hud_every_s: float = 3.0
    grace_s: float = 30.0
    stable_frames: int = 3

    def __post_init__(self) -> None:
        self.screen_tracker = AugmentScreenTracker(self.regions, stable_frames=self.stable_frames)
        self._cards: list[CardRead | None] = [None] * SLOTS
        self._traits: dict[str, int] = {}
        self._rerolls = RerollState()
        self._in_screen = False
        self._last_present_t = float("-inf")
        self._last_hud_t = float("-inf")
        self._last_t = float("-inf")
        self._last_emit: tuple | None = None
        self._hud_signature: list | None = None

    # -- dieu khien tu vo --------------------------------------------------

    def new_game(self) -> None:
        """Van moi: quen HUD da nho va man dang theo doi."""
        self.game_tracker.reset()
        self._reset_screen()
        self._last_t = float("-inf")

    def force_refresh(self) -> None:
        """Nguoi dung bam doc lai (F3 / nut Quet lai)."""
        self.screen_tracker.force_refresh()
        self._last_emit = None

    def seek(self, t: float) -> None:
        """Replay tua. Lui ve qua khu thi coi nhu van moi; tua toi thi giu HUD da doc."""
        if t < self._last_t:
            self.new_game()
        else:
            self._reset_screen()
        self._last_t = t

    # -- vong lap ----------------------------------------------------------

    def step(self, frame: Frame) -> LiveEvent:
        t = frame.t
        self._last_t = t
        latency: dict[str, float] = {}

        t0 = time.perf_counter()
        try:
            reading = self.reroll_reader.read(frame.image)
        except Exception as exc:                      # noqa: BLE001 - loi doc nut khong duoc giet vong lap
            return Status(t, f"không đọc được nút đổi thẻ: {exc}")
        latency["gate"] = (time.perf_counter() - t0) * 1000.0

        if not reading.screen_present:
            return self._step_outside(frame, latency)

        self._last_present_t = t
        if not self._in_screen:
            self._in_screen = True
            self.screen_tracker.reset()
            self._cards = [None] * SLOTS
            self._last_emit = None
        if reading.settled:
            self._rerolls = reading.to_reroll_state(self._rerolls)

        ready = self.screen_tracker.update(frame.image, [r.state for r in reading.reads])
        if not ready:
            return Idle(t)

        t0 = time.perf_counter()
        for slot in ready:
            try:
                self._cards[slot] = self.card_reader.read_slot(frame.image, slot)
            except Exception as exc:                  # noqa: BLE001
                self._cards[slot] = CardRead(slot, "", "", (), 0.0, f"lỗi đọc thẻ: {exc}")
        self.screen_tracker.mark_read(ready)
        traits = self._read_traits(frame)
        latency["cards"] = (time.perf_counter() - t0) * 1000.0

        cards = tuple(self._cards[i] or CardRead(i, "", "", (), 0.0, "chưa đọc") for i in range(SLOTS))
        choices = [
            AugmentChoice(list(c.api_names), c.confidence, c.title) for c in cards if c.api_names
        ]
        if not choices:
            return Status(t, "đang ở màn chọn lõi nhưng chưa đọc được thẻ nào",
                          tuple(f"ô {c.slot + 1}: {c.reason}" for c in cards))

        state = self.game_tracker.state(traits=traits)
        t0 = time.perf_counter()
        bundle = self.advisor.advise(
            state=state, choices=choices, rerolls=self._rerolls, frame_ref=frame.ref
        )
        latency["advise"] = (time.perf_counter() - t0) * 1000.0

        key = self._emit_key(cards, state)
        if key == self._last_emit:
            return Idle(t)
        self._last_emit = key

        return AdviceReady(
            t=t,
            stage=state.stage,
            bundle=bundle,
            state=state,
            cards=cards,
            rerolls=self._rerolls,
            stale_fields=self.game_tracker.stale,
            never_seen=self.game_tracker.never_seen,
            latency_ms=latency,
        )

    # -- ben ngoai man chon augment ----------------------------------------

    def _step_outside(self, frame: Frame, latency: dict[str, float]) -> LiveEvent:
        t = frame.t
        left_screen = self._in_screen and t - self._last_present_t > self.grace_s
        if left_screen:
            self._reset_screen()

        if t - self._last_hud_t >= self.hud_every_s:
            self._last_hud_t = t
            if self._hud_unchanged(frame.image):
                return Cleared(t) if left_screen else Idle(t)
            t0 = time.perf_counter()
            try:
                reading = self.hud_reader.read(frame.image)
                self._detect_new_game(reading)
                self.game_tracker.update(reading)
            except Exception as exc:                  # noqa: BLE001
                return Status(t, f"không đọc được HUD: {exc}")
            latency["hud"] = (time.perf_counter() - t0) * 1000.0

        return Cleared(t) if left_screen else Idle(t)

    def _hud_unchanged(self, image: Any) -> bool:
        """Vung HUD y het lan doc truoc -> khoi OCR lai (~1 s moi lan)."""
        import cv2  # noqa: PLC0415

        signature = []
        for name in HUD_SIGNATURE_FIELDS:
            try:
                crop = self.regions.crop(image, "hud", name)
            except Exception:                         # noqa: BLE001 - ROI thieu thi bo qua toi uu
                return False
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
            signature.append(cv2.resize(gray, (16, 8), interpolation=cv2.INTER_AREA).astype("float32"))

        same = self._hud_signature is not None and all(
            thumb_diff(a, b) < 0.5 for a, b in zip(self._hud_signature, signature)
        )
        self._hud_signature = signature
        return same

    def _detect_new_game(self, reading: Any) -> None:
        """Stage tut nguoc ve 1-x = van moi. Quen HUD cua van truoc."""
        field_read = reading.find("stage") if hasattr(reading, "find") else None
        stage = getattr(field_read, "value", None)
        if not stage or not isinstance(stage, str) or "-" not in stage:
            return
        try:
            new_major = int(stage.split("-")[0])
        except ValueError:
            return
        old = self.game_tracker.state().stage
        old_major = int(old.split("-")[0]) if "-" in old and old.split("-")[0].isdigit() else 0
        if new_major == 1 and old_major >= 3:
            self.new_game()

    def _read_traits(self, frame: Frame) -> dict[str, int]:
        try:
            traits = self.card_reader.read_traits(frame.image)
        except Exception:                             # noqa: BLE001 - toc/he la phu, khong duoc lam hong chu ky
            traits = {}
        if traits:
            self._traits = traits
        return dict(self._traits)

    # -- noi bo ------------------------------------------------------------

    def _reset_screen(self) -> None:
        self._in_screen = False
        self._cards = [None] * SLOTS
        self._rerolls = RerollState()
        self.screen_tracker.reset()
        self._last_emit = None

    @staticmethod
    def _emit_key(cards: Sequence[CardRead], state: Any) -> tuple:
        return (
            tuple(tuple(c.api_names) for c in cards),
            state.gold, state.level, state.hp, state.xp, state.stage,
        )
