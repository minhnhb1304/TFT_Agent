"""Phan thuan logic cua cong cu xem lai nhan playtest (moc M0).

Tach khoi scripts/review_playtest_labels.py de test duoc ma khong can HTTP:
    - doi ten hien thi <-> apiName (ke ca cap map mo: mot ten -> HAI apiName),
    - nhan payload tu trinh duyet, kiem, roi moi ghi.

QUY TAC: KHONG BAO GIO ghi de file nhan khi payload con loi. Nguoi gan nhan
sua 20 phut ma mot o sai lam hong ca file thi lan sau ho se khong dung nua.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from ..knowledge.augment_catalog import normalize
from ..knowledge.name_index import NameIndex
from .playtest_labels import PlaytestLabels, from_dict, save, validate


def augment_options(index: NameIndex) -> list[dict[str, Any]]:
    """Danh sach goi y cho o nhap ten: [{'vi': ..., 'api': [...]}], da gop cap trung ten."""
    by_name: dict[str, list[str]] = {}
    for api, langs in index.display.get("augments", {}).items():
        name = langs.get("vi") or langs.get("en") or api
        by_name.setdefault(name, []).append(api)
    return [{"vi": name, "api": sorted(apis)} for name, apis in sorted(by_name.items())]


def resolve_slot(text: str, options: Iterable[dict[str, Any]]) -> list[str]:
    """Chuoi nguoi dung go -> danh sach apiName.

    Nhan: ten hien thi (khop khong dau), apiName viet thang, hoac nhieu muc
    cach nhau bang dau phay. Ten ung voi hai apiName tra ve CA HAI - do la
    cap map mo that su, khong duoc tu chon mot.
    """
    parts = [p.strip() for p in str(text).split(",") if p.strip()]
    table = {normalize(o["vi"]): o["api"] for o in options}
    out: list[str] = []
    for part in parts:
        if part.startswith("DA_"):
            out.append(part)
            continue
        hit = table.get(normalize(part))
        if hit:
            out.extend(a for a in hit if a not in out)
    return out


def save_payload(
    payload: dict[str, Any], path: str | Path, known_augments: Iterable[str] | None = None
) -> tuple[PlaytestLabels | None, list[str]]:
    """Kiem payload roi ghi. Con loi -> KHONG ghi, tra ve danh sach loi."""
    labels = from_dict(payload)
    errors = validate(labels, known_augments)
    if errors:
        return None, errors
    save(labels, path)
    return labels, []


def capture_snapshot(video: str | Path, at_s: float, out_dir: str | Path, stem: str) -> str:
    """Trich mot khung tai giay `at_s` de nguoi gan nhan chen offer con thieu."""
    import cv2

    from ..capture.video_source import VideoFrameSource

    frame = VideoFrameSource(video).grab(at_s)
    if frame is None:
        raise ValueError(f"không lấy được khung tại {at_s:.2f}s")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"{stem}_{at_s:.2f}.jpg"
    cv2.imwrite(str(target), frame.image, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return target.as_posix()
