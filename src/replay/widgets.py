"""Widget cua vo replay: dai trang thai, dai ket luan, cot the, dai thoi gian.

Widget chi VE du lieu da dung san trong `viewmodel.py`. Khong widget nao tu tinh
diem hay tu doc man hinh - de con doi giao dien ma khong dong den phan quyet dinh.

NGU PHAP TRINH BAY hoc tu CSS that cua blitz.gg (research/260918-gamer-ui-palette):

  - Bac tier la MOT token dung o nhieu cuong do: ray doc 50%, than the nhuom 8%,
    chu nhan. Khong phai mot chu cai to mau me.
  - So KHONG to hon ten va KHONG sang hon ten. Chi so chinh duoc danh dau bang
    VI TRI va mot dai cham 6 o ben canh. Ten la thu de nhan dien, so de so sanh.
  - Lua chon nen chon = nen accent 15% + chu accent + vien 2px. Blitz khong dung
    thanh ben trai, khong ngoi sao, khong do bong.
  - So dung font dang khoang - cot so khong nhay khi doi khung.

Mau lay tu `theme.py`, khong viet hex o day.
"""

from __future__ import annotations

from typing import Sequence

from PyQt6 import QtCore, QtGui, QtWidgets

from . import theme
from .viewmodel import SlotVM, StripVM, VerdictVM

# Dung cham tron thay cho dau tick: Segoe UI khong co glyph ✓/✗, se ra o vuong.
REROLL_LABELS = {
    "available": ("● còn đổi", theme.OK),
    "used": ("○ đã đổi", theme.TEXT_MUTED),
    "unknown": ("● chưa rõ", theme.WARN),
}
DOTS = 6


def _label(text: str, *, size: int, color: str, weight: int = 400, mono: bool = False,
           wrap: bool = True, spacing: float = 0.0) -> QtWidgets.QLabel:
    lbl = QtWidgets.QLabel(text)
    family = theme.MONO if mono else theme.FONT
    lbl.setStyleSheet(
        f"color: {color}; font-size: {size}px; font-weight: {weight}; font-family: {family};"
        f" letter-spacing: {spacing}px; background: transparent;"
    )
    lbl.setWordWrap(wrap)
    return lbl


def _overline(text: str) -> QtWidgets.QLabel:
    """Nhan nhom: 11px / 600 / hoa / gian chu - nhu `.type-overline` cua Blitz."""
    return _label(text.upper(), size=theme.SIZES["xs"], color=theme.TEXT_MUTED,
                  weight=600, wrap=False, spacing=0.6)


class StateStrip(QtWidgets.QFrame):
    """Stage, cấp, XP, vàng, HP, chuỗi — kèm cảnh báo và câu lý do chung."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("bar")
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        top = QtWidgets.QHBoxLayout()
        top.setSpacing(12)
        self.main = _label("", size=theme.SIZES["base"], color=theme.TEXT, weight=500,
                           mono=True, wrap=False)
        top.addWidget(self.main)
        top.addStretch()
        self.rerolls = _label("", size=theme.SIZES["md"], color=theme.TEXT_2, mono=True, wrap=False)
        top.addWidget(self.rerolls)
        layout.addLayout(top)

        self.econ = _label("", size=theme.SIZES["md"], color=theme.TEXT_2)
        layout.addWidget(self.econ)
        self.warn = _label("", size=theme.SIZES["sm"], color=theme.WARN)
        layout.addWidget(self.warn)

    def set_data(self, strip: StripVM, status: str = "") -> None:
        self.main.setText(strip.line)
        self.rerolls.setText(
            "đổi thẻ —/3" if strip.rerolls_left is None else f"đổi thẻ {strip.rerolls_left}/3"
        )
        lines = [strip.econ] + strip.shared
        self.econ.setText(" · ".join(x for x in lines if x))
        self.econ.setVisible(bool(self.econ.text()))
        warnings = list(strip.warnings) + ([status] if status else [])
        self.warn.setText(" · ".join(warnings))
        self.warn.setVisible(bool(warnings))


class VerdictBar(QtWidgets.QFrame):
    """Một câu: động từ trước, chênh lệch sau. Nền accent 15%, không thanh trái."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("verdict")
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        self.tag = _overline("khuyến nghị")
        layout.addWidget(self.tag)
        self.headline = _label("", size=theme.SIZES["xl"], color=theme.ACCENT, weight=600,
                               wrap=False)
        layout.addWidget(self.headline)
        layout.addStretch()
        self.delta = _label("", size=theme.SIZES["md"], color=theme.TEXT_2, mono=True, wrap=False)
        layout.addWidget(self.delta)
        self.restyle()

    def restyle(self) -> None:
        self.setStyleSheet(
            f"QFrame#verdict {{ background: {theme._alpha(theme.ACCENT, theme.ACCENT_SELECT)};"
            f" border: 1px solid {theme._alpha(theme.ACCENT, 0.35)};"
            f" border-radius: {theme.RADIUS}px; }}"
        )

    def set_data(self, verdict: VerdictVM) -> None:
        self.headline.setText(verdict.headline)
        self.delta.setText(verdict.delta_text)
        self.setToolTip(verdict.note)


class DotScale(QtWidgets.QWidget):
    """Dải 6 chấm cạnh con số — cách Blitz đánh dấu chỉ số chính mà không phóng to nó."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(4)
        self.setMinimumWidth(DOTS * 8)
        self._value = 0.0
        self._color = theme.TEXT_2

    def set_data(self, value: float | None, color: str) -> None:
        self._value = max(0.0, min(1.0, value or 0.0))
        self._color = color
        self.update()

    def paintEvent(self, _event) -> None:                    # noqa: N802
        if self.width() <= 0 or self.height() <= 0:
            return
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        gap = 2
        width = max(2.0, (self.width() - gap * (DOTS - 1)) / DOTS)
        lit = round(self._value * DOTS)
        for i in range(DOTS):
            rect = QtCore.QRectF(i * (width + gap), 0, width, self.height())
            painter.setBrush(QtGui.QColor(self._color) if i < lit else QtGui.QColor(theme.SURFACE_3))
            painter.drawRoundedRect(rect, 1, 1)


class IconTile(QtWidgets.QWidget):
    """Ô icon 44px, viền theo độ hiếm — Blitz viền mọi icon bằng vòng độ hiếm."""

    SIZE = 44

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(self.SIZE, self.SIZE)
        self._letter = "?"
        self._ring = self._ring2 = theme.BORDER

    def set_data(self, name: str, rarity: int | None) -> None:
        self._letter = (name or "?").strip()[:1].upper()
        _, self._ring, self._ring2 = theme.rarity_style(rarity)
        self.update()

    def paintEvent(self, _event) -> None:                    # noqa: N802
        if self.width() <= 2 or self.height() <= 2:
            return
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        box = QtCore.QRectF(1, 1, self.SIZE - 2, self.SIZE - 2)

        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(QtGui.QColor(theme.SURFACE_3))
        painter.drawRoundedRect(box, 6, 6)

        gradient = QtGui.QLinearGradient(box.left(), box.top(), box.right(), box.bottom())
        gradient.setColorAt(0, QtGui.QColor(self._ring))
        gradient.setColorAt(1, QtGui.QColor(self._ring2))
        painter.setPen(QtGui.QPen(QtGui.QBrush(gradient), 1.5))
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(box, 6, 6)

        painter.setPen(QtGui.QColor(theme.TEXT_2))
        font = painter.font()
        font.setPixelSize(theme.SIZES["lg"])
        font.setWeight(QtGui.QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.drawText(box, QtCore.Qt.AlignmentFlag.AlignCenter, self._letter)


class TierRail(QtWidgets.QWidget):
    """Ray dọc màu bậc tier ở mép trái cột — token tier ở cường độ 50%."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedWidth(5)
        self._color = theme.TIER_COLORS[""]

    def set_tier(self, tier: str) -> None:
        self._color = theme.tier_style(tier).text
        self.update()

    def paintEvent(self, _event) -> None:                    # noqa: N802
        if self.height() <= 6:
            return
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        color = QtGui.QColor(self._color)
        color.setAlphaF(theme.TIER_RAIL)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawRoundedRect(QtCore.QRectF(0, 0, 4, self.height()), 2, 2)


class SlotColumn(QtWidgets.QFrame):
    """Một ô trên màn chọn lõi. Thứ tự cột = thứ tự ô trong game."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setMinimumWidth(230)
        outer = QtWidgets.QHBoxLayout(self)
        outer.setContentsMargins(3, 2, 0, 2)     # chua 1px vien + chua ray khong bi cat
        outer.setSpacing(0)

        self.rail = TierRail(self)
        outer.addWidget(self.rail)

        body = QtWidgets.QVBoxLayout()
        body.setContentsMargins(12, 12, 12, 12)
        body.setSpacing(8)
        outer.addLayout(body)

        head = QtWidgets.QHBoxLayout()
        head.setSpacing(8)
        self.icon = IconTile(self)
        head.addWidget(self.icon, alignment=QtCore.Qt.AlignmentFlag.AlignTop)

        titles = QtWidgets.QVBoxLayout()
        titles.setSpacing(3)
        self.slot_label = _overline("ô 1")
        titles.addWidget(self.slot_label)
        self.name = _label("", size=theme.SIZES["base"], color=theme.TEXT, weight=600)
        titles.addWidget(self.name)

        metric = QtWidgets.QHBoxLayout()
        metric.setSpacing(8)
        self.score = _label("", size=theme.SIZES["md"], color=theme.TEXT_2, mono=True, wrap=False)
        metric.addWidget(self.score)
        self.dots = DotScale(self)
        metric.addWidget(self.dots, stretch=1)
        self.tier = _label("", size=theme.SIZES["xs"], color=theme.TEXT_MUTED, weight=600,
                           wrap=False, spacing=0.6)
        metric.addWidget(self.tier)
        titles.addLayout(metric)
        head.addLayout(titles, stretch=1)
        body.addLayout(head)

        self.reasons = _label("", size=theme.SIZES["sm"], color=theme.TEXT_2)
        body.addWidget(self.reasons, stretch=1)
        self.footer = _label("", size=theme.SIZES["sm"], color=theme.TEXT_MUTED, weight=500,
                             wrap=False)
        body.addWidget(self.footer)

    def set_data(self, vm: SlotVM) -> None:
        tier = theme.tier_style(vm.tier)
        self.slot_label.setText(f"Ô {vm.slot + 1}" + (f" · #{vm.rank}" if vm.rank else ""))
        self.name.setText(vm.name)
        self.name.setStyleSheet(
            f"color: {theme.ACCENT if vm.recommended else theme.TEXT}; font-weight: 600;"
            f" font-size: {theme.SIZES['base']}px; font-family: {theme.FONT};"
            " background: transparent;"
        )
        self.icon.set_data(vm.name, vm.rarity)
        self.rail.set_tier(vm.tier)
        self.rail.setVisible(bool(vm.tier))
        self.tier.setText(f"BẬC {vm.tier}" if vm.tier else "CHƯA XẾP")
        self.tier.setStyleSheet(
            f"color: {tier.text}; font-size: {theme.SIZES['xs']}px; font-weight: 600;"
            f" letter-spacing: 0.6px; font-family: {theme.FONT}; background: transparent;"
        )
        self.score.setText(vm.score_text)
        self.dots.set_data(vm.score, tier.text)

        notes = [f"· {r}" for r in vm.reasons]
        if vm.ambiguous:
            notes.append("· không phân biệt được với lõi cùng tên")
        if vm.low_confidence:
            notes.append("· đọc tên chưa chắc chắn")
        if vm.unread:
            notes = [vm.raw_text or "chưa đọc được thẻ này"]
        self.reasons.setText("\n".join(notes))
        self.reasons.setStyleSheet(
            f"color: {theme.WARN if vm.unread else theme.TEXT_2}; background: transparent;"
            f" font-size: {theme.SIZES['sm']}px; font-family: {theme.FONT};"
        )

        text, color = REROLL_LABELS[vm.reroll]
        self.footer.setText(text)
        self.footer.setStyleSheet(
            f"color: {color}; font-size: {theme.SIZES['sm']}px; font-weight: 500;"
            " background: transparent;"
        )
        self._paint_frame(vm, tier)

    def _paint_frame(self, vm: SlotVM, tier: theme.TierStyle) -> None:
        # Than the nhuom mau tier 8%; lua chon nen chon phu nen accent 15% + vien 2px.
        background = theme._alpha(tier.text, theme.TIER_BODY) if vm.tier else theme.SURFACE_2
        border, width, style = theme.BORDER, 1, "solid"
        if vm.recommended:
            background = theme._alpha(theme.ACCENT, theme.ACCENT_SELECT)
            border, width = theme.ACCENT, 2
        elif vm.unread:
            border, style = theme.WARN, "dashed"
        self.setStyleSheet(
            f"QFrame#card {{ background: {background}; border: {width}px {style} {border};"
            f" border-radius: {theme.RADIUS}px; }}"
        )


class Timeline(QtWidgets.QWidget):
    """Dải thời gian: ● vòng chọn lõi, ▲ lần reroll, ▍vị trí đang xem."""

    seek = QtCore.pyqtSignal(float)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(30)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.duration = 1.0
        self.position = 0.0
        self.rounds: list[float] = []
        self.rerolls: list[float] = []

    def set_data(self, duration: float, rounds: Sequence[float], rerolls: Sequence[float]) -> None:
        self.duration = max(1.0, duration)
        self.rounds, self.rerolls = list(rounds), list(rerolls)
        self.update()

    def set_position(self, t: float) -> None:
        self.position = t
        self.update()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:   # noqa: N802
        self.seek.emit(max(0.0, event.position().x() / max(1, self.width()) * self.duration))

    def paintEvent(self, _event) -> None:                    # noqa: N802
        if self.width() <= 0 or self.height() <= 0:
            return
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        mid = self.height() / 2

        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(QtGui.QColor(theme.SURFACE_3))
        painter.drawRoundedRect(QtCore.QRectF(0, mid - 2, self.width(), 4), 2, 2)

        for t in self.rerolls:
            self._marker(painter, t, QtGui.QColor(theme.TEXT_MUTED), triangle=True)
        for t in self.rounds:
            self._marker(painter, t, QtGui.QColor(theme.ACCENT), triangle=False)

        x = self._x(self.position)
        painter.setBrush(QtGui.QColor(theme.TEXT))
        painter.drawRoundedRect(QtCore.QRectF(x - 1, mid - 9, 2, 18), 1, 1)

    def _x(self, t: float) -> float:
        return max(0.0, min(1.0, t / self.duration)) * self.width()

    def _marker(self, painter: QtGui.QPainter, t: float, color: QtGui.QColor, *, triangle: bool) -> None:
        x, mid = self._x(t), self.height() / 2
        painter.setBrush(color)
        if triangle:
            path = QtGui.QPainterPath()
            path.moveTo(x, mid - 7)
            path.lineTo(x - 4, mid - 1)
            path.lineTo(x + 4, mid - 1)
            path.closeSubpath()
            painter.drawPath(path)
        else:
            painter.drawEllipse(QtCore.QPointF(x, mid), 4.5, 4.5)
