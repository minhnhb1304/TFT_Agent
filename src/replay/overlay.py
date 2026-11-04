"""Overlay ve THANG len khung video - thu kieu Blitz truoc khi dua vao game.

Hai mau lay tu research/261007-blitz-overlay.md:
  1. Thong tin neo vao thu no giai thich: moi the loi mang mot huy hieu
     (bac, thu hang, diem) ngay tren canh tren cua o chu, khong gom ve panel.
  2. Mot widget kinh mo nho cho dong CHON/DOI - chi ket luan, khong danh sach.

Huy hieu dat NGAY TREN o chu (phan hinh minh hoa), khong o duoi: duoi mo ta la cho cac overlay
khac (MetaTFT trong video dat_01) da chiem.

Tach hai phan:
  - `layout()` + `frost()`: thuan Python/numpy, test duoc khong can Qt;
  - `paint()`: QPainter, chi ve theo du lieu da co (SlotVM, VerdictVM).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import cv2
import numpy as np

from ..capture.regions import ScreenRegions
from .viewmodel import SlotVM, VerdictVM

Rect = tuple[int, int, int, int]                 # left, top, right, bottom

BADGE_H = 0.034                                   # theo chieu cao khung - UI game co theo chieu cao
VERDICT_TOP = 0.055
VERDICT_H = 0.078
VERDICT_W = 0.66


@dataclass(frozen=True)
class Layout:
    """Vi tri tinh bang pixel tren khung DANG VE (da co gian)."""

    cards: tuple[Rect, ...]
    rerolls: tuple[Rect, ...]
    verdict: Rect
    badge_h: int


def layout(regions: ScreenRegions, width: int, height: int) -> Layout:
    """Vi tri overlay cho khung `width` x `height`.

    Dung chinh vung cat cua bo doc (kem diem neo) nen 16:10 khong lech: cho nao
    bo doc doc duoc thi huy hieu nam dung cho do.
    """
    cards = tuple(regions.region("augment_select", f"card_text_{i}").to_pixels(width, height)
                  for i in range(3))
    rerolls = tuple(regions.region("augment_select", f"reroll_{i}").to_pixels(width, height)
                    for i in range(3))
    w = min(int(VERDICT_W * height), width - 16)
    left = (width - w) // 2
    top = int(VERDICT_TOP * height)
    return Layout(cards, rerolls, (left, top, left + w, top + int(VERDICT_H * height)),
                  max(12, int(BADGE_H * height)))


def frost(rgb: np.ndarray, rect: Rect, darken: float = 0.45) -> None:
    """Lam mo + toi vung `rect` TAI CHO - nen 'kinh mo' cho widget ket luan."""
    left, top, right, bottom = rect
    roi = rgb[max(0, top):bottom, max(0, left):right]
    if roi.size == 0:
        return
    k = max(3, (roi.shape[0] // 3) | 1)
    roi[:] = (cv2.GaussianBlur(roi, (k, k), 0) * (1.0 - darken)).astype(rgb.dtype)


def badge_text(slot: SlotVM) -> str:
    """Chu trong huy hieu, khong ke o vuong bac."""
    if slot.unread:
        return "chưa đọc được"
    if slot.score is None:
        return "?"
    rank = f"#{slot.rank}  " if slot.rank else ""
    mark = "  ~" if slot.ambiguous or slot.low_confidence else ""
    return f"{rank}{slot.score_text}{mark}"


def paint(painter, lay: Layout, slots: Sequence[SlotVM], verdict: VerdictVM) -> None:
    """Ve huy hieu, vien o duoc khuyen, vong nut doi va widget ket luan."""
    from PyQt6 import QtCore, QtGui

    from . import theme

    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    bh = lay.badge_h
    reroll = verdict.action == "ĐỔI"
    accent = QtGui.QColor(theme.WARN if reroll else theme.ACCENT)

    def font(px: int, weight: QtGui.QFont.Weight = QtGui.QFont.Weight.DemiBold) -> QtGui.QFont:
        f = QtGui.QFont("Segoe UI")
        f.setPixelSize(max(9, px))
        f.setWeight(weight)
        return f

    for slot in slots:
        if slot.slot >= len(lay.cards):
            continue
        left, top, right, bottom = lay.cards[slot.slot]
        chosen = slot.recommended

        if chosen:                                   # vien o duoc khuyen
            pen = QtGui.QPen(accent, max(2, bh // 10))
            if reroll:
                pen.setStyle(QtCore.Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            pad = bh // 5
            painter.drawRoundedRect(QtCore.QRectF(left - pad, top - pad, right - left + 2 * pad,
                                                  bottom - top + 2 * pad), bh / 4, bh / 4)

        # Huy hieu: o bac + chu, can giua, sat tren o chu.
        text = badge_text(slot)
        painter.setFont(font(int(bh * 0.52)))
        text_w = painter.fontMetrics().horizontalAdvance(text)
        tier = (slot.tier or "").upper()
        shield = bh - 6 if tier else 0
        width = text_w + shield + int(bh * 0.7) + (6 if tier else 0)
        cx = (left + right) / 2
        box = QtCore.QRectF(cx - width / 2, top - bh * 1.2, width, bh)   # tren ten loi, khong che
        painter.setPen(QtGui.QPen(accent if chosen else QtGui.QColor(255, 255, 255, 46), 1.2))
        painter.setBrush(QtGui.QColor(12, 12, 16, 225))
        painter.drawRoundedRect(box, bh / 2, bh / 2)

        x = box.left() + bh * 0.35
        if tier:
            color = QtGui.QColor(theme.TIER_COLORS.get(tier, theme.TIER_COLORS[""]))
            sq = QtCore.QRectF(x - 2, box.top() + 3, shield, shield)
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(sq, 3, 3)
            painter.setPen(QtGui.QColor(10, 10, 12))
            painter.setFont(font(int(shield * 0.72), QtGui.QFont.Weight.Black))
            painter.drawText(sq, QtCore.Qt.AlignmentFlag.AlignCenter, tier)
            x += shield + 6
        painter.setFont(font(int(bh * 0.52)))
        painter.setPen(accent if chosen else QtGui.QColor(255, 255, 255, 220 if slot.score is not None else 140))
        painter.drawText(QtCore.QRectF(x, box.top(), text_w + 4, bh),
                         QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignLeft, text)

    if reroll and verdict.slot is not None and verdict.slot < len(lay.rerolls):
        left, top, right, bottom = lay.rerolls[verdict.slot]
        painter.setPen(QtGui.QPen(accent, max(2, bh // 8)))
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        pad = bh // 6
        painter.drawRoundedRect(QtCore.QRectF(left - pad, top - pad, right - left + 2 * pad,
                                              bottom - top + 2 * pad), bh / 4, bh / 4)
        painter.setFont(font(int(bh * 0.55), QtGui.QFont.Weight.Bold))
        painter.drawText(QtCore.QRectF(right + pad * 2, top, bh * 3, bottom - top),
                         QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignLeft, "ĐỔI")

    if not verdict.action:
        return
    left, top, right, bottom = lay.verdict
    box = QtCore.QRectF(left, top, right - left, bottom - top)
    painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 40), 1))
    painter.setBrush(QtGui.QColor(255, 255, 255, 14))
    painter.drawRoundedRect(box, 8, 8)
    painter.setPen(QtCore.Qt.PenStyle.NoPen)                 # gach mau ben trai = mau hanh dong
    painter.setBrush(accent)
    painter.drawRoundedRect(QtCore.QRectF(left + 6, top + 8, 3, box.height() - 16), 1.5, 1.5)

    pad = int(box.height() * 0.16)
    inner = box.adjusted(pad + 10, pad * 0.6, -pad, -pad * 0.6)
    half = inner.height() / 2
    painter.setFont(font(int(half * 0.78), QtGui.QFont.Weight.Bold))
    painter.setPen(accent)
    head = QtCore.QRectF(inner.left(), inner.top(), inner.width(), half)
    painter.drawText(head, QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignLeft,
                     verdict.headline)
    if verdict.delta_text:
        painter.setFont(font(int(half * 0.6), QtGui.QFont.Weight.Medium))
        painter.setPen(QtGui.QColor(255, 255, 255, 150))
        painter.drawText(head, QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignRight,
                         verdict.delta_text)

    # CHON: noi vi sao o nay dung dau. DOI: noi ly do cua chinh sach doi.
    detail = (verdict.note or verdict.edge) if reroll else (verdict.edge or verdict.note)
    if detail:
        painter.setFont(font(int(half * 0.6), QtGui.QFont.Weight.Normal))
        painter.setPen(QtGui.QColor(255, 255, 255, 190))
        line = QtCore.QRectF(inner.left(), inner.top() + half, inner.width(), half)
        elided = painter.fontMetrics().elidedText(detail, QtCore.Qt.TextElideMode.ElideRight,
                                                  int(line.width()))
        painter.drawText(line, QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignLeft,
                         elided)
