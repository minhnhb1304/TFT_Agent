"""Lõi dùng chung cho replay và live (docs/playtest-fixes/shared-core.md).

KHÔNG import Qt ở đây — `tests/test_live_session.py` và AST test khoá điều đó:
mọi quyết định phải chạy được headless, và hai vỏ phải dùng đúng một lõi.
"""

from .card_reader import CardReader, GeminiCardReader, OcrCardReader
from .events import AdviceReady, Cleared, Idle, LiveEvent, Status
from .screen_tracker import AugmentScreenTracker
from .session import LiveSession

__all__ = [
    "AdviceReady",
    "AugmentScreenTracker",
    "CardReader",
    "Cleared",
    "GeminiCardReader",
    "Idle",
    "LiveEvent",
    "LiveSession",
    "OcrCardReader",
    "Status",
]
