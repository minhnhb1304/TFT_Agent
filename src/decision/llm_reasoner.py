"""LLM Reasoner - vai tro B: lam muot cau chu, SAU khi da co ket qua (SPEC 3.5.3).

RANG BUOC KIEN TRUC, KHONG THUONG LUONG:

    LLM khong bao gio nam tren duong quyet dinh co han gio.

Man chon augment chi keo dai khoang 30 giay. Scoring engine tra loi tuc thi
bang so hoc dong tren du lieu da cache. LLM den SAU, sau mot hard timeout, va
chi duoc phep viet lai CAU GIAI THICH.

Vi sao cam doi thu hang (chu khong chi khuyen khong nen): neu LLM doi duoc ket
qua thi ablation study (SPEC 12.4) mat y nghia - khong con biet diem so nao
that su tao ra khuyen nghi. Vi the module nay chi lay ve VAN BAN va gan vao
`refined_reason`; thu hang nam ngoai tam voi cua no theo dung nghia den, va
`assert_order_preserved()` khoa dieu do lai bang mot phep kiem tra.

Vai tro A (trich dac trung augment offline) khong o day - no o
scripts/build_augment_features.py, chay mot lan moi set.
"""

from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass
from typing import Any, Callable

from ..game_state.models import GameState
from .augment_advisor import Ranking

REFINE_PROMPT = """Ban la nguoi choi TFT trinh do Challenger. Duoi day la xep hang
augment da duoc tinh bang thuat toan, kem diem tung thanh phan. Viet lai phan ly do
cho tu nhien, NGAN GON (1 cau moi augment), bang tieng Viet.

TUYET DOI KHONG doi thu tu xep hang. Chi tra ve JSON dang {"api_name": "cau ly do"}.
"""


class RankingMutationError(RuntimeError):
    """LLM (hoac bat ky ai) da lam doi thu hang - loi nghiem trong."""


@dataclass
class LlmReasoner:
    """Goi LLM de viet lai ly do, co hard timeout va kiem tra bat bien.

    Args:
        enabled: mac dinh False. Tat thi `refine()` tra ve nguyen ranking.
        timeout_s: hard timeout. Het gio -> tra nguyen ranking, khong doi.
        call: ham goi model, tiem vao de test khong cham mang.
    """

    enabled: bool = False
    model: str = "gemini-3.5-flash-lite"
    timeout_s: float = 2.0
    call: Callable[[str], str] | None = None

    def refine(self, ranking: Ranking, state: GameState) -> Ranking:
        """Gan `refined_reason` cho tung entry. Thu hang GIU NGUYEN.

        Moi duong that bai (tat, khong key, timeout, JSON hong) deu dan ve
        cung mot ket qua: ranking nguyen ven. Do la thiet ke - phan nay cua he
        thong duoc phep bien mat ma khong ai nhan ra.
        """
        order_before = list(ranking.order)
        if not self.enabled or not ranking.entries:
            return ranking

        caller = self.call or self._default_call
        prompt = self._build_prompt(ranking, state)

        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                raw = pool.submit(caller, prompt).result(timeout=self.timeout_s)
        except FutureTimeout:
            return ranking
        except Exception:
            # Bat rong co y: mot loi cua tang tuy chon khong duoc phep lam hong
            # loi khuyen da tinh xong.
            return ranking

        for entry in ranking.entries:
            text = (self._parse(raw) or {}).get(entry.api_name)
            if isinstance(text, str) and text.strip():
                entry.refined_reason = text.strip()

        assert_order_preserved(order_before, ranking)
        return ranking

    # -- noi bo ------------------------------------------------------------

    @staticmethod
    def _build_prompt(ranking: Ranking, state: GameState) -> str:
        payload = {
            "tinh_huong": {
                "stage": state.stage, "hp": state.hp, "gold": state.gold,
                "level": state.level, "traits": state.active_traits,
            },
            "xep_hang": [
                {
                    "api_name": e.api_name,
                    "ten": e.name,
                    "diem": round(e.total, 3),
                    "ly_do": e.reasons,
                }
                for e in ranking.entries
            ],
        }
        return REFINE_PROMPT + "\n" + json.dumps(payload, ensure_ascii=False, indent=2)

    @staticmethod
    def _parse(raw: str) -> dict[str, Any] | None:
        start, end = raw.find("{"), raw.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            return json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            return None

    def _default_call(self, prompt: str) -> str:
        """Goi Gemini that. Import muon de he thong chay duoc khi khong cai SDK."""
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("thieu GEMINI_API_KEY")
        from google import genai  # noqa: PLC0415

        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(model=self.model, contents=prompt)
        return getattr(resp, "text", "") or ""


def assert_order_preserved(order_before: list[str], ranking: Ranking) -> None:
    """Khoa bat bien: refinement khong duoc doi thu hang.

    Ton tai de bien mot rang buoc kien truc thanh mot phep kiem tra chay duoc,
    thay vi mot dong van trong tai lieu ma khong ai thi hanh.
    """
    if order_before != ranking.order:
        raise RankingMutationError(
            f"LLM refinement da doi thu hang: {order_before} -> {ranking.order}"
        )
