"""Nguon so lieu thong ke augment - interface cam-rut (SPEC 3.4.2).

Nguon so lieu (avg placement / top-4) SE CHOT SAU. Vi vay scoring engine
tuyet doi khong duoc biet du lieu den tu dau: no chi thay `AugmentStatsProvider`.

    Them nguon moi = them MOT file. Khong sua scoring engine.

Hai quy tac khong duoc pha:
    1. Moi so hien len overlay phai kem `source` va `sample_n`. Khong co co
       mau thi khong phai bang chung, chi la con so.
    2. Khong co so lieu la trang thai BINH THUONG, khong phai loi. NullProvider
       cho phep chay ca he thong truoc khi co bat ky nguon nao - do la thu giu
       cho Track A khong bi chan boi mot API key.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable, Protocol, runtime_checkable

# Placement trung binh cua mot augment ngau nhien trong lobby 8 nguoi.
NEUTRAL_PLACEMENT = 4.5


def is_fabricated(source: str) -> bool:
    """Nguon co chu MOCK la du lieu gia TU KHAI BAO.

    Quy uoc nay do scripts/build_mock_stats.py va build_mock_comps.py dat ra:
    so gia phai tu khai bao la gia, va no chay suot toi tan reason string tren
    overlay. `tests/test_meta_comps.py` da dung dung phep thu nay.

    Can mot ham rieng vi `AugmentStats.is_evidence` KHONG bat duoc truong hop
    nay: bo so gia lap bia san `sample_n` tren 200 nen no tra True. Voi
    BaseScorer thi vo hai - no in thang `source` ra man hinh. Nhung khi phai
    XEP HANG cac nguon voi nhau thi con so bia do se de mot cai gia thang mot
    y kien co nguoi ky ten, va do la dieu khong duoc phep xay ra.
    """
    return "MOCK" in str(source).upper()


@dataclass(frozen=True)
class AugmentStats:
    """So lieu thong ke cua mot augment, LUON kem provenance."""

    api_name: str
    avg_place: float
    top4_rate: float = 0.0
    win_rate: float = 0.0
    sample_n: int = 0
    source: str = "unknown"
    # Bac trong mot bang tier do NGUOI xep (S/A/B/C/D), rong neu khong co.
    tier: str = ""
    # True = `avg_place` SUY RA tu `tier`, khong phai so do duoc. Xem
    # ExpertTierListProvider. BaseScorer doc co nay de khong tin no nhu so do.
    is_ordinal: bool = False

    @property
    def is_evidence(self) -> bool:
        """Co du co mau de goi la bang chung khong.

        Nguong 200 tran la quy uoc cua du an nay, khong phai chuan nganh: duoi
        muc do, sai so mot placement trung binh con lon hon khoang cach giua
        mot augment tot va mot augment te.

        Bang tier cua chuyen gia KHONG BAO GIO dat nguong nay: sample_n = 0.
        Do la ket qua dung - mot y kien, du sac sao, khong phai bang chung.
        """
        return self.sample_n >= 200 and not self.is_ordinal


@runtime_checkable
class AugmentStatsProvider(Protocol):
    """Interface duy nhat ma scoring engine duoc phep biet."""

    name: str

    def get(self, api_name: str) -> AugmentStats | None:
        """Tra so lieu cua augment, hoac None neu nguon khong co."""
        ...


class NullProvider:
    """Khong co so lieu - MAC DINH. Base se la trung tinh o moi augment.

    Ton tai de tra loi cau hoi "he thong co chay duoc khi chua co du lieu
    khong": co, va no noi ro ra rang no dang khong co du lieu.
    """

    name = "null"

    def get(self, api_name: str) -> AugmentStats | None:
        return None


class CsvProvider:
    """Doc so lieu tu CSV tu chuan bi - nguon mac dinh hien tai.

    Cot bat buoc: api_name, avg_place. Cot tuy chon: top4_rate, win_rate,
    sample_n, source. Thieu cot bat buoc thi bao loi NGAY luc nap, khong de
    den luc cham diem moi phat hien.
    """

    name = "csv"

    REQUIRED = ("api_name", "avg_place")

    def __init__(
        self,
        path: str | Path,
        source: str | None = None,
        allow_fabricated: bool = True,
    ) -> None:
        """`allow_fabricated=False` bo cac dong tu khai bao la gia ngay luc nap.

        Mac dinh True vi lop nay la mot trinh DOC file trung thanh - doc gi ra
        nay. Viec quyet dinh co dung mot nguon hay khong thuoc ve
        `default_provider()`, va chinh no la cho truyen False vao.
        """
        self.path = Path(path)
        self.source = source or f"csv:{self.path.name}"
        self.allow_fabricated = allow_fabricated
        self._rows: dict[str, AugmentStats] = {}
        self._load()

    def _load(self) -> None:
        with self.path.open(encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            missing = [c for c in self.REQUIRED if c not in (reader.fieldnames or [])]
            if missing:
                raise ValueError(f"{self.path} thieu cot bat buoc: {missing}")
            for row in reader:
                api = (row.get("api_name") or "").strip()
                if not api:
                    continue
                source = (row.get("source") or self.source).strip()
                if not self.allow_fabricated and is_fabricated(source):
                    continue
                self._rows[api] = AugmentStats(
                    api_name=api,
                    avg_place=float(row["avg_place"]),
                    top4_rate=float(row.get("top4_rate") or 0.0),
                    win_rate=float(row.get("win_rate") or 0.0),
                    sample_n=int(float(row.get("sample_n") or 0)),
                    source=source,
                )

    def __len__(self) -> int:
        return len(self._rows)

    def get(self, api_name: str) -> AugmentStats | None:
        return self._rows.get(api_name)


class ExpertTierListProvider:
    """Bang tier do NGUOI xep - tin hieu THU TU, khong phai so do.

    VI SAO CAN DEN NO
        Riot da go truong `augments` khoi participant Set 18, va tactics.tools
        - trang stats lon nhat cong khai - cung tra ve rong tren 1,75 trieu
        van (do 2026-09-01). Khong con nguon DO DUOC nao. Thu con lai la y
        kien chuyen gia: datatft.com nhung bang cua Horox / 九九 / 云顶精神力
        thang vao bundle JS, tftacademy.com xep S/A/B/C theo silver-gold-
        prismatic. Ca hai deu khong kem co mau, va do khong phai thieu sot cua
        ho: ho khong dem, ho danh gia.

    BA RANG BUOC KHONG DUOC PHA
        1. `sample_n` LUON = 0. Khong bao gio bia mot co mau de tin hieu nay
           nang len - do la cach mot y kien tro thanh "so lieu" trong bao cao.
        2. `is_ordinal` = True, nen `is_evidence` LUON False. BaseScorer nhin
           co nay va ha muc tin xuong `ordinal_trust`, thay vi tin nhu so do.
        3. `avg_place` chi la MA HOA DON DIEU cua bac, khong phai placement do
           duoc. No ton tai vi BaseScorer nhan placement; `tier` moi la du
           lieu that. Reason string phai noi ro dieu do.

    MODULE NAY KHONG DI KEM DU LIEU - cung ly do voi comp_database.py: nhet
    mot bang tier tu bia vao repo cho ra mot he thong chay muot va tu van sai.
    File khong ton tai -> provider rong -> BaseScorer trung tinh.
    """

    name = "expert-tierlist"

    # Bac -> placement dai dien. KHONG PHAI SO DO. Chi can don dieu (S tot
    # nhat) va nam trong khoang [best_place, worst_place] cua BaseScorer
    # (3.5 - 5.0) de bac cao khong bi ep ve bien. Doi cac so nay khong lam
    # thay doi THU TU xep hang, chi lam thay doi do doc cua no.
    #
    # HIEU CHUAN LAI 2026-09-08 theo HINH DANG THAT cua bang TFT Academy.
    # Bo neo cu (4.05/4.30/4.50/4.70/4.90) duoc dat khi chua co bang tier that,
    # va no gia dinh nam bac trai deu nhau. Bang that thi khong:
    #     S 50/245 (20%)  A 105/245 (43%)  B 85/245 (35%)  C 5/245 (2%)
    # Hai he qua bat buoc phai sua:
    #   1. A la bac DONG DAO nhat, nen A phai roi dung 0.5 - "mot lua chon
    #      binh thuong", chu khong phai mot tin hieu duong. Neo 4.25 cho ra
    #      dung 0.5 voi ordinal_trust = 0.65.
    #   2. TFT Academy KHONG xep bac D. Chi 5 augment nam o C, va do la bac
    #      "khong nen cam" cua ho - tuc la C dang giu vai tro cua D. Neo C
    #      phai xuong san (4.90) de phat dung muc, con D lui ve 4.95 chi de
    #      giu don dieu S < A < B < C < D cho cac bang tier khac.
    # Diem w1 tuong ung (ordinal_trust = 0.65): S 0.630 > A 0.500 > B 0.370
    # > C 0.218 > D 0.197.
    TIER_PLACEMENT: dict[str, float] = {
        "S": 3.95,
        "A": 4.25,
        "B": 4.55,
        "C": 4.90,
        "D": 4.95,
    }

    # Hau to cua cac ban NANG CAP trong du lieu CDragon (X, X Plus, X PlusPlus).
    UPGRADE_SUFFIX = "Plus"

    def __init__(
        self,
        tiers: dict[str, Iterable[str]] | None = None,
        source: str | None = None,
    ) -> None:
        self.source = source or self.name
        self._rows: dict[str, AugmentStats] = {}
        for tier, api_names in (tiers or {}).items():
            key = str(tier).strip().upper()
            if key not in self.TIER_PLACEMENT:
                raise ValueError(
                    f"bac '{tier}' khong hop le. Chi chap nhan: "
                    f"{', '.join(self.TIER_PLACEMENT)}"
                )
            for api_name in api_names:
                api = str(api_name).strip()
                if api:
                    self._rows[api] = AugmentStats(
                        api_name=api,
                        avg_place=self.TIER_PLACEMENT[key],
                        sample_n=0,
                        source=self.source,
                        tier=key,
                        is_ordinal=True,
                    )

    @classmethod
    def load(cls, path: str | Path) -> "ExpertTierListProvider":
        """Nap tu JSON do scripts/import_augment_tiers.py sinh ra.

        File khong ton tai -> provider RONG, khong raise. Giong CompDatabase:
        thieu du lieu lam giam chat luong khuyen nghi nhung khong duoc phep
        lam sap advisor.
        """
        p = Path(path)
        if not p.exists():
            return cls()
        payload = json.loads(p.read_text(encoding="utf-8"))
        meta = payload.get("meta") or {}
        # Nguoi danh gia phai co ten trong provenance. Mot bang tier khong ai
        # ky ten thi khong hon gi bia ra.
        rated_by = str(meta.get("rated_by") or "khong ro nguoi danh gia")
        patch = str(meta.get("patch") or "?")
        return cls(payload.get("tiers") or {}, source=f"{cls.name}:{rated_by}/patch={patch}")

    def __len__(self) -> int:
        return len(self._rows)

    def get(self, api_name: str) -> AugmentStats | None:
        row = self._rows.get(api_name)
        if row is not None:
            return row
        return self._inherit_from_base(api_name)

    def _inherit_from_base(self, api_name: str) -> AugmentStats | None:
        """Ban Plus/PlusPlus chua duoc xep -> muon bac cua dang goc.

        VI SAO CAN
            `data/augment_features.json` lay tu CDragon nen liet ke DU moi bien
            the, con TFT Academy chi xep mot dang dai dien. Ba ban nang cap roi
            ra ngoai bang va bi cham 0.5 trung tinh - tuc la dung TREN chinh ban
            goc bac B cua no. Do la mot loi xep hang, khong phai mot khoang
            trong du lieu.

        CACH LAM
            Boc dan tung hau to `Plus`: `X PlusPlus` -> `X Plus` -> `X`, dung o
            dang DAU TIEN co trong bang. Mot ban nang cap khong bao gio te hon
            ban goc, nen day la suy dien BAO THU: no chi keo diem ve dung bang
            ban goc, khong bao gio doan cao hon.

        RANG BUOC
            `source` phai noi ro bac nay di muon tu dau. Mot bac ke thua van la
            mot suy dien, va suy dien do phai chay den tan reason string tren
            overlay - giong het cach `is_ordinal` khong cho mot y kien di qua
            duoi lop mot so do.
        """
        name = str(api_name).strip()
        while name.endswith(self.UPGRADE_SUFFIX):
            name = name[: -len(self.UPGRADE_SUFFIX)]
            base = self._rows.get(name)
            if base is not None:
                return replace(
                    base,
                    api_name=api_name,
                    source=f"{base.source} (bậc kế thừa từ {name})",
                )
        return None


class CompositeProvider:
    """Gop nhieu nguon theo thu tu uu tien, GIU NGUYEN provenance.

    Nguon dau tien tra ve ket qua se thang. Khong trung binh cong giua cac
    nguon: trung binh lam mat provenance, ma provenance la thu hoi dong cham
    do an se hoi den dau tien.
    """

    name = "composite"

    def __init__(self, providers: Iterable[AugmentStatsProvider]) -> None:
        self.providers = list(providers)

    def get(self, api_name: str) -> AugmentStats | None:
        for provider in self.providers:
            stats = provider.get(api_name)
            if stats is not None:
                return stats
        return None


class RiotApiProvider:
    """So lieu tu chinh minh crawl tft-match-v1 - bao ve tot nhat truoc hoi dong.

    Moi nguon khac deu la hop den: OP.GG khong cong bo cach tinh, cac trang
    stats khong cong bo co mau. Nguon nay thi tung con so truy nguoc duoc den
    mot tap match_id cu the, luu trong data/augment_stats.meta.json.

    ⚠️ KHONG goi mang trong `get()`. Provider nay doc mot AGGREGATE da tinh
    san, do scripts/crawl_augment_stats.py sinh ra offline. Dat mot request
    HTTP len duong quyet dinh 30 giay la vi pham SPEC 3.5.3 - va lam ablation
    study mat tinh tai lap.

    Duong dung o runtime van la CsvProvider doc file da crawl. Lop nay ton tai
    de tang crawl co mot implementation dung Protocol, va de test tong hop
    duoc ma khong qua CSV.
    """

    name = "riot-api"

    def __init__(self, stats: dict[str, AugmentStats] | None = None) -> None:
        self._rows = dict(stats or {})

    @classmethod
    def from_aggregator(cls, aggregator: Any, source: str) -> "RiotApiProvider":
        """Dung tu AugmentAggregator sau mot dot crawl.

        Import muon de stats_provider khong keo theo `requests` - Track A phai
        import duoc ma khong can tang mang.
        """
        rows = {
            row["api_name"]: AugmentStats(
                api_name=str(row["api_name"]),
                avg_place=float(row["avg_place"]),
                top4_rate=float(row["top4_rate"]),
                win_rate=float(row["win_rate"]),
                sample_n=int(row["sample_n"]),
                source=str(row["source"]),
            )
            for row in aggregator.rows(source)
        }
        return cls(rows)

    def __len__(self) -> int:
        return len(self._rows)

    def get(self, api_name: str) -> AugmentStats | None:
        return self._rows.get(api_name)


class OpggMcpProvider:
    """Lay so lieu qua MCP cua OP.GG - nhanh nhung la hop den.

    Chua trien khai co chu y. Xem research/prior-art.md: ToS cua OP.GG han che
    thu thap tu dong va khong co dieu khoan mien tru cho MCP. Rui ro thap voi
    mot cong cu ca nhan khong phat hanh, nhung provenance thi khong kiem chung
    duoc - do la ly do no khong phai mac dinh.
    """

    name = "opgg-mcp"

    def get(self, api_name: str) -> AugmentStats | None:
        raise NotImplementedError(
            "OpggMcpProvider chua trien khai - xem research/prior-art.md ve ToS."
        )


def default_provider(
    csv_path: str | Path | None = None,
    tiers_path: str | Path | None = None,
    backup_tiers_path: str | Path | None = None,
    allow_fabricated: bool = False,
) -> AugmentStatsProvider:
    """Nguon mac dinh, theo THU TU UU TIEN: CSV -> bang tier (TFT Academy) -> du phong (MetaTFT) -> Null.

    Thu tu nay la mot phat bieu ve gia tri bang chung, khong phai tien lop:
    mot so DO DUOC luon thang mot y kien, du y kien do den tu nguoi choi gioi
    hon. Bang tier chi duoc dung o nhung augment ma CSV khong co. MetaTFT chi duoc
    dung o nhung augment ma ca CSV lan TFT Academy deu khong co.

    NHUNG MOT SO GIA THI KHONG THANG GI CA (sua 2026-09-07). `AugmentStats.
    is_evidence` chi nhin `sample_n`, ma bo so gia lap bia san sample_n tren
    200. Hau qua: `data/augment_stats.csv` phu du 254 augment nen no CHE HET
    bang tier - tha mot bang tier that vao repo cung khong doi duoc gi, va
    khong co gi bao ca. Vi the mac dinh `allow_fabricated=False`: dong nao tu
    khai bao la gia thi bi bo ngay luc nap, va neu ca file deu gia thi nguon
    do khong duoc tinh la mot nguon.

    Day la ham duy nhat trong du an duoc phep quyet dinh nguon nao dang dung.
    """
    if isinstance(backup_tiers_path, bool):
        allow_fabricated = backup_tiers_path
        backup_tiers_path = None

    providers: list[AugmentStatsProvider] = []
    if csv_path and Path(csv_path).exists():
        csv_provider = CsvProvider(csv_path, allow_fabricated=allow_fabricated)
        if len(csv_provider):
            providers.append(csv_provider)
    if tiers_path and Path(tiers_path).exists():
        tiers = ExpertTierListProvider.load(tiers_path)
        if len(tiers):
            providers.append(tiers)
    if backup_tiers_path and Path(backup_tiers_path).exists():
        backup_tiers = ExpertTierListProvider.load(backup_tiers_path)
        if len(backup_tiers):
            providers.append(backup_tiers)
    if not providers:
        return NullProvider()
    return CompositeProvider(providers + [NullProvider()])

