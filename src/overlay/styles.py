"""Theme cho overlay (SPEC 3.6).

Rang buoc thiet ke khac han mot app thong thuong: overlay nam DE LEN game, va
nguoi doc no dang bi mot dong ho dem nguoc 30 giay. Vi the:

    - Nen toi, do trong suot vua du de van thay board ben duoi.
    - Chi mot mau nhan manh. Nhieu mau nhan manh = khong con gi duoc nhan manh.
    - Co chu du lon de doc luot, khong phai de doc ky.
"""

from __future__ import annotations

# Mau dang (r, g, b, a) de dung truc tiep voi QColor.
BACKGROUND = (12, 14, 20, 205)
BACKGROUND_SOLID = (12, 14, 20, 245)
TEXT_PRIMARY = (240, 240, 245, 255)
TEXT_SECONDARY = (190, 195, 205, 255)
ACCENT = (90, 200, 140, 255)          # khuyen nghi so 1
ACCENT_BAR = (90, 200, 140, 90)
NEUTRAL_BAR = (90, 130, 200, 70)
WARNING = (255, 190, 90, 255)         # map mo / do tin cay thap
DANGER = (235, 100, 100, 255)

FONT_FAMILY = "Segoe UI"
FONT_SIZE_TITLE = 13
FONT_SIZE_BODY = 11

PANEL_PADDING = 14
ROW_SPACING = 8

QSS = """
QWidget {
    background: transparent;
    color: rgb(240, 240, 245);
    font-family: 'Segoe UI';
    font-size: 11pt;
}
QLabel#title {
    font-size: 13pt;
    font-weight: 600;
}
QLabel#warning {
    color: rgb(255, 190, 90);
}
"""
