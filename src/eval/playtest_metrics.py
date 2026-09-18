"""Cham mot lan chay (run) doi chieu voi nhan playtest - moc M0.

Run la chuoi `ReadEvent`: moi lan he thong DOC XONG va CAP NHAT panel. Mot lan
doc duoc coi la con hien tren man cho toi lan doc ke tiep - dung nhu nguoi
choi nhin thay. Vi vay:

    the "dang hien" cua offer k = lan doc CUOI CUNG trong man, truoc luc offer
    k ket thuc.

Neu he thong chi doc mot lan luc mo man (hanh vi run_replay.py d537eb0), thi
sau reroll the dang hien van la the CU - va bi tinh sai. Do chinh la loi #2.

BA KET CUC CUA MOT O, KHONG GOP:

    correct       - doan dung (voi cap map mo: tra ve du ca cap cung tinh dung).
                    Tinh ca khi doc ra the cua offer KE TIEP: `at_s` trong nhan la
                    uoc luong cua nguoi gan nhan, doc nhanh hon nhan khong phai loi.
    wrong_silent  - tra ve MOT apiName khac su that, khong bao gi. Loi nang nhat:
                    nguoi choi khong co cach nao biet.
    missing       - khong doc duoc / chua doc. It nguy hiem hon vi thay duoc.

Chi man `verified` duoc cham; man `draft` bi bo qua va DEM ra de bao cao.

`lead_s`: lan doc som hon `open_s` mot chut van thuoc man do. Nhan va run lay mau
o hai nhip khac nhau, nen "man mo luc nao" lech nhau vai tram ms; loai lan doc
do di se lam mot he thong doc dung trong nhu khong doc gi.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal, Sequence

from .playtest_labels import HUD_KEYS, SLOTS, PlaytestLabels, ScreenLabel
from .recognition import percentile

SlotOutcome = Literal["correct", "wrong_silent", "missing"]


@dataclass(frozen=True)
class ReadEvent:
    """Mot lan doc da cap nhat panel."""

    t: float
    cards: tuple[tuple[str, ...], ...]          # 3 o, moi o la cac apiName
    hud: dict[str, int | None] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReadEvent":
        cards = tuple(tuple(str(a) for a in (c or ())) for c in data.get("cards") or ())
        cards = cards + ((),) * (SLOTS - len(cards))
        return cls(t=float(data["t"]), cards=cards[:SLOTS], hud=dict(data.get("hud") or {}))

    def to_dict(self) -> dict[str, Any]:
        return {"t": round(self.t, 3), "cards": [list(c) for c in self.cards], "hud": self.hud}


def load_run(path: str | Path) -> list[ReadEvent]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return sorted((ReadEvent.from_dict(json.loads(x)) for x in lines if x.strip()), key=lambda e: e.t)


def save_run(events: Iterable[ReadEvent], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(e.to_dict(), ensure_ascii=False) + "\n" for e in events), encoding="utf-8")


def slot_outcome(predicted: Sequence[str], truth: Sequence[str]) -> SlotOutcome:
    """Cham mot o. `truth` nhieu phan tu = cap map mo."""
    pred, true = set(predicted), set(truth)
    if not pred:
        return "missing"
    if len(pred) == 1:
        return "correct" if pred <= true else "wrong_silent"
    # Tra ve nhieu ung vien: trung thuc chi khi su that nam trong do.
    return "correct" if true and true <= pred else "wrong_silent"


@dataclass
class PlaytestReport:
    screens_scored: int = 0
    screens_skipped_draft: int = 0
    offers: int = 0
    slots: int = 0
    correct: int = 0
    wrong_silent: int = 0
    missing: int = 0
    early: int = 0                  # doc ra the cua offer ke tiep som hon moc nhan
    rerolls: int = 0
    rerolls_caught: int = 0
    offers_never_correct: int = 0
    latencies_s: list[float] = field(default_factory=list)
    hud_total: dict[str, int] = field(default_factory=dict)
    hud_correct: dict[str, int] = field(default_factory=dict)
    failures: list[str] = field(default_factory=list)

    @property
    def card_acc(self) -> float:
        return self.correct / self.slots if self.slots else 0.0

    @property
    def reroll_recall(self) -> float:
        return self.rerolls_caught / self.rerolls if self.rerolls else 0.0

    def hud_acc(self, key: str) -> float | None:
        total = self.hud_total.get(key, 0)
        return self.hud_correct.get(key, 0) / total if total else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "screens_scored": self.screens_scored,
            "screens_skipped_draft": self.screens_skipped_draft,
            "offers": self.offers,
            "slots": self.slots,
            "card_acc": round(self.card_acc, 4),
            "card_wrong_silent": self.wrong_silent,
            "card_missing": self.missing,
            "card_correct_early": self.early,
            "rerolls": self.rerolls,
            "reroll_recall": round(self.reroll_recall, 4),
            "offers_never_correct": self.offers_never_correct,
            "read_latency_s": {
                "p50": _round(percentile(self.latencies_s, 0.5)) if self.latencies_s else None,
                "p95": _round(percentile(self.latencies_s, 0.95)) if self.latencies_s else None,
                "n": len(self.latencies_s),
            },
            "hud_acc": {k: _round(self.hud_acc(k)) for k in HUD_KEYS if k in self.hud_total},
            "failures": self.failures,
        }


def evaluate(labels: PlaytestLabels, run: Sequence[ReadEvent], lead_s: float = 1.0) -> PlaytestReport:
    report = PlaytestReport()
    events = sorted(run, key=lambda e: e.t)
    for screen in labels.screens:
        if not screen.verified:
            report.screens_skipped_draft += 1
            continue
        report.screens_scored += 1
        _score_screen(screen, [e for e in events if screen.open_s - lead_s <= e.t <= screen.close_s], report)
    return report


def _score_screen(screen: ScreenLabel, events: list[ReadEvent], report: PlaytestReport) -> None:
    for k, offer in enumerate(screen.offers):
        end = screen.offer_end(k)
        report.offers += 1
        tag = f"{screen.stage} offer #{k + 1} @{offer.at_s:.1f}s"

        last = k == len(screen.offers) - 1
        # Offer cuoi hien toi luc man dong, nen tinh ca lan doc dung vao close_s.
        start = float("-inf") if k == 0 else offer.at_s   # offer dau: tinh ca lan doc som (da loc theo lead_s)
        in_window = [e for e in events if start <= e.t < end or (last and e.t == end)]
        before_end = [e for e in events if e.t < end or (last and e.t <= end)]
        shown = before_end[-1] if before_end else None

        nxt = screen.offers[k + 1] if not last else None
        for i in range(SLOTS):
            truth = offer.slot(i)
            outcome = slot_outcome(shown.cards[i] if shown else (), truth)
            if outcome == "wrong_silent" and nxt is not None:
                if slot_outcome(shown.cards[i], nxt.slot(i)) == "correct":
                    outcome = "correct"     # doc duoc the moi som hon moc ghi trong nhan
                    report.early += 1
            report.slots += 1
            setattr(report, outcome, getattr(report, outcome) + 1)
            if outcome != "correct":
                got = list(shown.cards[i]) if shown else None
                report.failures.append(f"{tag} ô {i + 1}: {outcome} (đọc {got}, đúng {list(offer.slot(i))})")

        first_ok = next(
            (e for e in in_window if all(slot_outcome(e.cards[i], offer.slot(i)) == "correct" for i in range(SLOTS))),
            None,
        )
        if first_ok is None:
            report.offers_never_correct += 1
        else:
            report.latencies_s.append(max(0.0, first_ok.t - offer.at_s))

        if offer.rerolled_slot is not None:
            s = offer.rerolled_slot
            report.rerolls += 1
            if any(slot_outcome(e.cards[s], offer.slot(s)) == "correct" for e in in_window):
                report.rerolls_caught += 1
            else:
                report.failures.append(f"{tag}: bỏ sót reroll ô {s + 1}")

        for key, truth in screen.hud.items():
            if truth is None:
                continue
            report.hud_total[key] = report.hud_total.get(key, 0) + 1
            if shown is not None and shown.hud.get(key) == truth:
                report.hud_correct[key] = report.hud_correct.get(key, 0) + 1


def _round(value: float | None) -> float | None:
    return None if value is None else round(value, 3)
