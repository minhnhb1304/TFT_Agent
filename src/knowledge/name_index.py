"""Anh xa ten hien thi (ket qua OCR) -> apiName - feedback #6/#7.

QUY CHUAN BAT BUOC
    Logic noi bo CHI dung `apiName`. Ten hien thi la DU LIEU, khong bao gio
    la khoa. Module nay la ranh gioi duy nhat ma ten hien thi duoc phep di
    qua: tang vision doc ra chu tieng Viet, goi resolve(), va tu do tro di
    moi thu deu la apiName.

    Nho ranh gioi nay, scoring engine khong biet gi ve ngon ngu - va SPEC
    12.1 (do chinh xac nhan dien) do duoc doc lap voi 12.2-12.4 (chat luong
    tu van), dung nhu SPEC 9.3 yeu cau.

TRA VE DANH SACH, KHONG PHAI MOT GIA TRI
    resolve() tra `list[str]`. Do khong phai su phong thu thua:

        - Tieng Viet: 254 augment chi con 249 ten duy nhat -> 5 nhom trung.
        - Tieng Anh: 250 ten duy nhat -> 4 nhom trung.

    Ep ve mot gia tri la DOAN BUA. SPEC 3.5.4 quy dinh ro: gap cap map mo thi
    cham diem va hien THI CA HAI, gan nhan, khong doan. Xem
    research/vision-stack/augments.md.

TIE-BREAK PHAN BIET HOA THUONG
    "Tons of Stats!" va "TONS of Stats!" chi khac nhau o chu hoa. Quy tac
    "lowercase truoc moi so sanh" (ocr.md) xoa mat dung tin hieu duy nhat
    tach duoc chung, nen resolve() thu lai co phan biet hoa thuong khi buoc
    normalize cho ra nhieu hon mot ung vien. Tieng Anh cuu duoc cap nay;
    tieng Viet thi khong ("Cong Met Nghi!" giong het nhau ca hai) - do la ly
    do VI te hon EN dung mot cap.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .augment_catalog import normalize, strip_tier_token

# Ba khong gian ten duoc lap chi muc. Deu can cho tang vision: augment doc
# bang Gemini Vision (SPEC 9.3), trait doc tu panel ben trai, champion doc
# tu shop/board.
NAMESPACES = ("augments", "traits", "champions")

# Ngon ngu duoc ho tro. vi = ket qua OCR trong game tieng Viet, en = doi chieu.
LANGUAGES = ("vi", "en")


@dataclass
class NameIndex:
    """Bang tra ten -> apiName, sinh offline boi scripts/build_name_index.py.

    Attributes:
        by_norm: namespace -> lang -> ten da normalize -> [apiName].
        by_stem: namespace -> lang -> goc (da bo token tier) -> [apiName].
        exact: namespace -> lang -> ten NGUYEN VAN -> [apiName]. Chi dung de
            tie-break hoa thuong, khong phai duong tra chinh.
        display: namespace -> apiName -> lang -> ten hien thi. Chieu nguoc lai,
            de overlay hien ten tieng Viet ma van giu khoa la apiName.
        meta: provenance - nguon locale, thoi diem sinh, so luong.
    """

    by_norm: dict[str, dict[str, dict[str, list[str]]]] = field(default_factory=dict)
    by_stem: dict[str, dict[str, dict[str, list[str]]]] = field(default_factory=dict)
    exact: dict[str, dict[str, dict[str, list[str]]]] = field(default_factory=dict)
    display: dict[str, dict[str, dict[str, str]]] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)

    # -- nap ---------------------------------------------------------------

    @classmethod
    def empty(cls) -> "NameIndex":
        """Index rong - resolve() luon tra [] chu khong no."""
        return cls(meta={"note": "index rong - chua chay scripts/build_name_index.py"})

    @classmethod
    def load(cls, path: str | Path) -> "NameIndex":
        """Nap tu JSON. Thieu file KHONG phai loi: he thong van chay, chi la
        khong dich duoc ten -> apiName (tang vision chua ton tai o Track A).
        """
        p = Path(path)
        if not p.exists():
            return cls.empty()
        data = json.loads(p.read_text(encoding="utf-8"))
        return cls(
            by_norm=data.get("by_norm", {}),
            by_stem=data.get("by_stem", {}),
            exact=data.get("exact", {}),
            display=data.get("display", {}),
            meta=data.get("meta", {}),
        )

    def __len__(self) -> int:
        return sum(len(v) for v in self.display.values())

    @property
    def is_empty(self) -> bool:
        return not self.display

    # -- tra cuu -----------------------------------------------------------

    def resolve(
        self, text: str, namespace: str = "augments", lang: str = "vi"
    ) -> list[str]:
        """Ten hien thi -> danh sach apiName khop.

        Tra ve:
            []            - khong khop (OCR sai, hoac ten khong thuoc set nay)
            [1 phan tu]    - khop duy nhat
            [>1 phan tu]   - MAP MO THAT SU. Goi ben phai hien tat ca va gan
                             nhan, tuyet doi khong tu chon phan tu dau.
        """
        table = self.by_norm.get(namespace, {}).get(lang, {})
        hits = list(table.get(normalize(text), []))
        if len(hits) <= 1:
            return hits

        # Con nhieu hon mot -> thu lai co phan biet hoa thuong truoc khi chiu.
        exact = list(self.exact.get(namespace, {}).get(lang, {}).get(text, []))
        return exact if len(exact) == 1 else hits

    def resolve_stem(
        self, text: str, namespace: str = "augments", lang: str = "vi"
    ) -> list[str]:
        """Khop theo goc, sau khi bo token tier (I/II/III/+/++).

        Dung khi OCR nuot mat hau to tier. Ket qua thuong la CA CUM cung goc
        khac tier - do la thong tin dung, khong phai loi: goi ben biet la
        khong doc duoc tier chu khong tuong da doc duoc.
        """
        table = self.by_stem.get(namespace, {}).get(lang, {})
        return list(table.get(normalize(strip_tier_token(text)), []))

    def display_name(
        self, api_name: str, namespace: str = "augments", lang: str = "vi"
    ) -> str:
        """apiName -> ten hien thi. Chuoi rong neu khong biet."""
        return self.display.get(namespace, {}).get(api_name, {}).get(lang, "")

    def ambiguous_groups(
        self, namespace: str = "augments", lang: str = "vi"
    ) -> dict[str, list[str]]:
        """Cac ten ung voi nhieu hon mot apiName - gioi han du lieu, do duoc.

        Do 2026-09-01 tren locale day du: augments vi = 5 nhom, en = 4 nhom.
        Con so nay phai duoc bao cao trong do an chu khong giau di.
        """
        table = self.by_norm.get(namespace, {}).get(lang, {})
        return {k: list(v) for k, v in sorted(table.items()) if len(v) > 1}
