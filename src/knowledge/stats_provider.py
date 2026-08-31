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
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Protocol, runtime_checkable

# Placement trung binh cua mot augment ngau nhien trong lobby 8 nguoi.
NEUTRAL_PLACEMENT = 4.5


@dataclass(frozen=True)
class AugmentStats:
    """So lieu thong ke cua mot augment, LUON kem provenance."""

    api_name: str
    avg_place: float
    top4_rate: float = 0.0
    win_rate: float = 0.0
    sample_n: int = 0
    source: str = "unknown"

    @property
    def is_evidence(self) -> bool:
        """Co du co mau de goi la bang chung khong.

        Nguong 200 tran la quy uoc cua du an nay, khong phai chuan nganh: duoi
        muc do, sai so mot placement trung binh con lon hon khoang cach giua
        mot augment tot va mot augment te.
        """
        return self.sample_n >= 200


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

    def __init__(self, path: str | Path, source: str | None = None) -> None:
        self.path = Path(path)
        self.source = source or f"csv:{self.path.name}"
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
                self._rows[api] = AugmentStats(
                    api_name=api,
                    avg_place=float(row["avg_place"]),
                    top4_rate=float(row.get("top4_rate") or 0.0),
                    win_rate=float(row.get("win_rate") or 0.0),
                    sample_n=int(float(row.get("sample_n") or 0)),
                    source=(row.get("source") or self.source).strip(),
                )

    def __len__(self) -> int:
        return len(self._rows)

    def get(self, api_name: str) -> AugmentStats | None:
        return self._rows.get(api_name)


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


def default_provider(csv_path: str | Path | None = None) -> AugmentStatsProvider:
    """Nguon mac dinh: CSV neu file ton tai, nguoc lai Null.

    Day la ham duy nhat trong du an duoc phep quyet dinh nguon nao dang dung.
    """
    if csv_path and Path(csv_path).exists():
        return CompositeProvider([CsvProvider(csv_path), NullProvider()])
    return NullProvider()
