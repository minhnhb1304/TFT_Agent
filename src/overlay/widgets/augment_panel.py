"""Panel hien xep hang augment KEM LY DO (SPEC 3.5.4, Phase 4).

Module chia doi co chu y:

    PhanA - `build_rows()`: thuan tuy, khong cham Qt. Day la phan chua toan bo
            quyet dinh trinh bay (rut gon ly do, gan nhan map mo, do dai thanh
            diem) va la phan duoc TEST. Chay duoc tren may khong co man hinh.
    PhanB - `AugmentPanel`: chi ve. Import PyQt6 muon, ben trong ham, de test
            va CLI khong bi chan boi mot thu vien GUI.

Ly do tach: mot widget Qt chi kiem tra duoc khi co QApplication va mot desktop
that. Neu tron logic vao do thi logic trinh bay khong bao gio duoc test.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# So ly do toi da hien cho moi augment. Man chon augment chi keo dai ~30 giay -
# ba dong da la nhieu chu de doc.
MAX_REASONS = 3

AMBIGUOUS_LABEL = "không phân biệt được"


@dataclass
class PanelRow:
    """Mot dong tren panel - da san sang de ve, khong con tinh toan gi them."""

    rank: int
    name: str
    score: float
    reasons: list[str] = field(default_factory=list)
    ambiguous: bool = False
    low_confidence: bool = False
    badges: list[str] = field(default_factory=list)

    @property
    def bar_ratio(self) -> float:
        """Ti le do dai thanh diem, [0, 1]."""
        return max(0.0, min(1.0, self.score))


def build_rows(ranking: Any, min_confidence: float = 0.75) -> list[PanelRow]:
    """Doi mot `Ranking` thanh cac dong hien thi.

    Nhan `Any` thay vi kieu cu the de widget khong keo ca decision engine vao
    do thi import cua overlay - overlay chi biet doc thuoc tinh.

    Args:
        min_confidence: duoi nguong nay thi gan nhan canh bao nhan dang. Hien
            mot xep hang tu tin tren mot ket qua OCR yeu la kieu hong te nhat:
            nguoi choi tin, ma he thong thi dang doan.
    """
    rows: list[PanelRow] = []
    for i, entry in enumerate(getattr(ranking, "entries", ranking), start=1):
        badges: list[str] = []
        if entry.ambiguous:
            badges.append(AMBIGUOUS_LABEL)
        low_conf = entry.confidence < min_confidence
        if low_conf:
            badges.append(f"độ tin cậy {entry.confidence:.0%}")

        rows.append(
            PanelRow(
                rank=i,
                name=entry.name,
                score=entry.total,
                reasons=list(entry.reasons)[:MAX_REASONS],
                ambiguous=entry.ambiguous,
                low_confidence=low_conf,
                badges=badges,
            )
        )
    return rows


ACTION_LABELS = {"PICK": "CHỌN", "REROLL": "ĐỔI"}


def build_reroll_line(advice: Any) -> str:
    """Mot dong HANH DONG cho khuyen nghi doi the (SPEC 3.5.5).

    Dong nay dat tren cung panel vi no la thu nguoi choi can doc truoc: xep
    hang tra loi "the nao tot nhat", con dong nay tra loi "bam vao dau".

    Dau `?` xuat hien khi nen phan bo chua phai so DO DUOC. No ha giong cua
    khuyen nghi chu khong giau khuyen nghi di - phep so sanh giua the dan dau
    va pool van hop le khi ca hai cung sinh ra tu mot ham diem.
    """
    if advice is None:
        return ""
    label = ACTION_LABELS.get(advice.action, advice.action)
    mark = "" if advice.evidence == "measured" else " ?"
    gain = f"  (+{advice.expected_gain:.3f})" if advice.action == "REROLL" else ""
    keep = (
        f", giữ ô {advice.fallback_slot + 1}"
        if advice.action == "REROLL"
        else ""
    )
    return f"▶ {label} ô {advice.target_slot + 1}{keep}{gain}{mark}"


def render_text(rows: list[PanelRow], advice: Any = None) -> str:
    """Ban ve bang van ban - dung cho log, test va che do khong overlay.

    `advice` la tuy chon de moi cho goi cu khong phai doi - panel van dung
    duoc khi chua co lop nhan dang trang thai nut doi.
    """
    lines: list[str] = []
    line = build_reroll_line(advice)
    if line:
        lines.append(line)
    for row in rows:
        badge = f"  [{' · '.join(row.badges)}]" if row.badges else ""
        lines.append(f"{row.rank}. {row.name}  {row.score:.3f}{badge}")
        lines.extend(f"     - {r}" for r in row.reasons)
    return "\n".join(lines)


# --- Phan B: ve bang Qt ----------------------------------------------------


def _qt():
    """Import PyQt6 muon, bao loi ro rang neu thieu."""
    try:
        from PyQt6 import QtCore, QtGui, QtWidgets  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - chi xay ra khi thieu GUI stack
        raise RuntimeError(
            "AugmentPanel can PyQt6. Phan build_rows()/render_text() chay duoc "
            "khong can PyQt6 - dung chung neu chi muon ket xuat van ban."
        ) from exc
    return QtCore, QtGui, QtWidgets


def create_panel(parent: Any = None):
    """Tao widget panel. Goi ham nay thay vi import class o dau file."""
    QtCore, QtGui, QtWidgets = _qt()

    class AugmentPanel(QtWidgets.QWidget):
        """Panel xep hang augment - chi doc, khong nhan input.

        Khong dat WindowTransparentForInput o day: co do thuoc ve cua so chua
        no (overlay_window.py). Widget nay khong biet gi ve win32.
        """

        def __init__(self, parent=None) -> None:
            super().__init__(parent)
            self._rows: list[PanelRow] = []
            self._advice: Any = None
            self.setMinimumWidth(380)

        def set_ranking(self, ranking: Any, advice: Any = None) -> None:
            """Cap nhat noi dung. Goi tu luong chinh cua Qt."""
            self._rows = build_rows(ranking)
            self._advice = advice
            self.update()

        def set_advice(self, advice: Any) -> None:
            self._advice = advice
            self.update()

        def rows(self) -> list[PanelRow]:
            return list(self._rows)

        def paintEvent(self, event) -> None:  # noqa: N802 - ten do Qt quy dinh
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
            painter.fillRect(self.rect(), QtGui.QColor(12, 14, 20, 215))

            y = 14
            reroll_line = build_reroll_line(self._advice)
            if reroll_line:
                painter.fillRect(14, y - 2, self.width() - 28, 26, QtGui.QColor(35, 48, 65, 230))
                painter.setPen(QtGui.QColor(255, 215, 60))
                font = painter.font()
                font.setBold(True)
                painter.setFont(font)
                painter.drawText(20, y + 16, reroll_line)
                font.setBold(False)
                painter.setFont(font)
                y += 34

            for row in self._rows:
                y = self._paint_row(painter, QtGui, row, y)
            painter.end()

        def _paint_row(self, painter, QtGui, row: PanelRow, y: int) -> int:
            width = self.width() - 28

            # Thanh diem ve TRUOC chu, de chu nam tren nen thanh.
            bar_w = int(width * row.bar_ratio)
            color = QtGui.QColor(90, 200, 140, 90) if row.rank == 1 else QtGui.QColor(90, 130, 200, 70)
            painter.fillRect(14, y - 2, bar_w, 22, color)

            painter.setPen(QtGui.QColor(240, 240, 245))
            painter.drawText(20, y + 14, f"{row.rank}. {row.name}   {row.score:.3f}")
            y += 26

            if row.badges:
                painter.setPen(QtGui.QColor(255, 190, 90))
                painter.drawText(28, y + 12, " · ".join(row.badges))
                y += 20

            painter.setPen(QtGui.QColor(190, 195, 205))
            for reason in row.reasons:
                painter.drawText(28, y + 12, f"– {reason}")
                y += 18
            return y + 8

    return AugmentPanel(parent)
