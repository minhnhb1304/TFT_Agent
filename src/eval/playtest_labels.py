"""Nhan tay cho mot ban record playtest - nen cua moc M0 (docs/playtest-fixes/eval-dataset.md).

Mot file nhan = mot video. Moi man chon augment ghi lai:
    - HUD NGAY TRUOC khi mo man (luc thanh HUD con thay),
    - moi trang thai 3 the ON DINH (offer), gom ca sau moi lan reroll,
    - augment da chon, va (sau nay) xep hang cua chuyen gia.

HAI TRANG THAI CUA MOT MAN, KHONG DUOC TRON:

    draft     - do scripts/draft_playtest_labels.py sinh ra, CHUA ai kiem.
    verified  - nguoi choi da xem anh va sua. Chi man nay moi duoc dung lam
                su that trong scripts/eval_playtest.py.

Nhan nhap sinh bang chinh bo doc OCR. Dem no ra lam su that thi bo doc se tu
cham diem cho chinh no - vong tu xac nhan ma docs/expert-prior/evaluation-framing.md
da canh bao. Vi the `validate` kiem chat hon voi man verified.

MOT O CO THE CO NHIEU apiName: do la cap map mo (trung ca ten lan icon). Nguoi
gan nhan cung khong tach duoc, nen ghi CA HAI chu khong chon bua.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal

from .scenario_logger import GAME_ID_RE

SCHEMA_VERSION = 2
# Doc file schema 1 van chay: bon truong cap file cua schema 2 deu khuyet duoc.
# File schema 1 chi khong dung duoc cho 12.2 (thieu game_id / final_placement),
# va `missing_for_correlation` noi thang ra dieu do thay vi de no im lang.
SUPPORTED_SCHEMAS = (1, 2)
SLOTS = 3
HUD_KEYS = ("gold", "level", "xp", "xp_needed", "hp", "streak")
STAGE_RE = re.compile(r"^\d-\d$")
CAPTURE_KEYS = ("tool", "size", "lang", "fps", "original_name")
PLACEMENT_RANGE = (1, 8)

LabelStatus = Literal["draft", "verified"]


class LabelError(ValueError):
    """File nhan sai. Mang TOAN BO loi, khong dung o loi dau tien."""

    def __init__(self, path: str, errors: list[str]) -> None:
        self.errors = errors
        super().__init__(f"{path}: {len(errors)} lỗi\n  - " + "\n  - ".join(errors))


@dataclass
class Offer:
    """Mot trang thai 3 the on dinh tren man hinh."""

    at_s: float
    cards: list[list[str]]                 # 3 o; moi o la danh sach apiName
    rerolled_slot: int | None = None       # o vua bi doi de ra offer nay
    ocr_raw: list[str] = field(default_factory=list)   # goi y cua ban nhap, khong phai su that
    snapshot: str | None = None

    def slot(self, i: int) -> tuple[str, ...]:
        return tuple(self.cards[i]) if i < len(self.cards) else ()


@dataclass
class ScreenLabel:
    """Mot man chon augment."""

    stage: str
    open_s: float
    close_s: float
    offers: list[Offer]
    status: LabelStatus = "draft"
    hud: dict[str, int | None] = field(default_factory=dict)
    traits: dict[str, int] | None = None
    picked: str | None = None
    expert: dict[str, Any] | None = None
    notes: str = ""

    @property
    def verified(self) -> bool:
        return self.status == "verified"

    def offer_end(self, k: int) -> float:
        """Offer k hien tren man den luc offer k+1 xuat hien, hoac man dong."""
        return self.offers[k + 1].at_s if k + 1 < len(self.offers) else self.close_s


@dataclass
class PlaytestLabels:
    """Toan bo nhan cua mot video.

    BON TRUONG CAP FILE (schema 2, 2026-09-30) - mot lan cho ca video:

        game_id          khoa khoi cua phep hoan vi (SPEC 12.2). PHAI khop dung
                         gia tri `ScenarioLogger` ghi o runtime, neu khong thi
                         `correlation` khong join duoc va NO KHONG BAO LOI - chi
                         tra n_games = None roi coi moi quyet dinh la doc lap,
                         dung cai bay dev_log 8c da sua.
        player_id        tang khoi THU HAI. Nhieu nguoi choi thi ky nang thanh
                         confound cua 12.2, nen hoan vi phai nam TRONG tung nguoi.
        final_placement  nguoi choi TU KHAI. Khong back-fill qua Riot API
                         (bo han 2026-09-30, SPEC 12.0).
        capture_profile  chuoi capture la mot BIEN: OBS Display Capture va
                         Overwolf/Outplayed nen khac nhau co the lam so 12.1
                         lech co he thong. Khong ghi lai thi khong tach duoc
                         "OCR cua ta yeu" khoi "ban thu cua ta nhieu".
    """

    video: str
    screens: list[ScreenLabel]
    size: tuple[int, int] | None = None
    video_sha256: str | None = None
    game_id: str | None = None
    player_id: str | None = None
    final_placement: int | None = None
    capture_profile: dict[str, Any] | None = None
    schema: int = SCHEMA_VERSION

    @property
    def verified_screens(self) -> list[ScreenLabel]:
        return [s for s in self.screens if s.verified]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "video": self.video,
            "video_sha256": self.video_sha256,
            "size": list(self.size) if self.size else None,
            "game_id": self.game_id,
            "player_id": self.player_id,
            "final_placement": self.final_placement,
            "capture_profile": self.capture_profile,
            "screens": [_screen_to_dict(s) for s in self.screens],
        }


# --- doc / ghi --------------------------------------------------------------


def from_dict(data: dict[str, Any]) -> PlaytestLabels:
    screens = []
    for s in data.get("screens") or []:
        offers = [
            Offer(
                at_s=float(o["at_s"]),
                cards=[list(_as_slot(c)) for c in o.get("cards") or []],
                rerolled_slot=o.get("rerolled_slot"),
                ocr_raw=list(o.get("ocr_raw") or []),
                snapshot=o.get("snapshot"),
            )
            for o in s.get("offers") or []
        ]
        screens.append(
            ScreenLabel(
                stage=str(s.get("stage", "")),
                open_s=float(s["open_s"]),
                close_s=float(s["close_s"]),
                offers=offers,
                status=s.get("status", "draft"),
                hud=dict(s.get("hud") or {}),
                traits=s.get("traits"),
                picked=s.get("picked"),
                expert=s.get("expert"),
                notes=str(s.get("notes", "")),
            )
        )
    size = data.get("size")
    placement = data.get("final_placement")
    return PlaytestLabels(
        video=str(data.get("video", "")),
        screens=screens,
        size=(int(size[0]), int(size[1])) if size else None,
        video_sha256=data.get("video_sha256"),
        game_id=data.get("game_id"),
        player_id=data.get("player_id"),
        final_placement=int(placement) if placement is not None else None,
        capture_profile=data.get("capture_profile"),
        # Khong co khoa `schema` = file soan tay truoc schema 2. Mac dinh 1, KHONG
        # phai SCHEMA_VERSION: mac dinh vao ban moi nhat la tu nhan cho mot file cu
        # la file moi, roi bo qua dung nhung truong no thieu.
        schema=int(data.get("schema", 1)),
    )


def load(
    path: str | Path,
    known_augments: Iterable[str] | None = None,
    known_traits: Iterable[str] | None = None,
) -> PlaytestLabels:
    """Nap va kiem. Sai bat ky cho nao -> LabelError liet ke du moi loi."""
    p = Path(path)
    labels = from_dict(json.loads(p.read_text(encoding="utf-8")))
    errors = validate(labels, known_augments, known_traits)
    if errors:
        raise LabelError(str(p), errors)
    return labels


def save(labels: PlaytestLabels, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(labels.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# --- kiem -------------------------------------------------------------------


def validate(
    labels: PlaytestLabels,
    known_augments: Iterable[str] | None = None,
    known_traits: Iterable[str] | None = None,
) -> list[str]:
    """Tra ve danh sach loi. Rong = hop le."""
    errors: list[str] = []
    augments = set(known_augments) if known_augments is not None else None
    traits = set(known_traits) if known_traits is not None else None

    if labels.schema not in SUPPORTED_SCHEMAS:
        errors.append(f"schema {labels.schema} không hỗ trợ (đọc được {SUPPORTED_SCHEMAS})")
    if not labels.video:
        errors.append("thiếu 'video'")
    errors.extend(_validate_file_fields(labels))

    prev_close = -1.0
    for i, s in enumerate(labels.screens):
        where = f"màn #{i + 1} ({s.stage or '?'})"
        errors.extend(_validate_screen(s, where, augments, traits))
        if s.open_s < prev_close:
            errors.append(f"{where}: open_s {s.open_s} chồng lên màn trước (đóng lúc {prev_close})")
        prev_close = max(prev_close, s.close_s)
    return errors


def _validate_file_fields(labels: PlaytestLabels) -> list[str]:
    """Kiem bon truong cap file cua schema 2.

    KHUYET thi KHONG phai loi - file schema 1 hop le va van dung duoc cho 12.1.
    Chi kiem DINH DANG khi co mat. Thieu truong de chay 12.2 thi
    `missing_for_correlation` bao, va no bao o cho nguoi doc so nhin thay.
    """
    errors: list[str] = []
    lo, hi = PLACEMENT_RANGE

    if labels.game_id is not None and not GAME_ID_RE.match(labels.game_id):
        errors.append(
            f"game_id '{labels.game_id}' phải có dạng '<video_id>#<số ván>', ví dụ 'nam_01#1'"
        )
    if labels.player_id is not None and not str(labels.player_id).strip():
        errors.append("player_id rỗng — bỏ hẳn khoá này còn rõ hơn là để chuỗi rỗng")
    if labels.final_placement is not None and not lo <= labels.final_placement <= hi:
        errors.append(f"final_placement {labels.final_placement} ngoài khoảng {lo}-{hi}")
    if labels.capture_profile is not None:
        if not isinstance(labels.capture_profile, dict):
            errors.append("capture_profile phải là object")
        else:
            for key in labels.capture_profile:
                if key not in CAPTURE_KEYS:
                    errors.append(f"capture_profile.{key} không nằm trong {CAPTURE_KEYS}")
    return errors


def missing_for_correlation(labels: PlaytestLabels) -> list[str]:
    """Truong nao con thieu de file nay dung duoc cho SPEC 12.2 / 12.3.

    Tach khoi `validate` co chu y: mot file thieu `final_placement` van la nhan
    HOP LE va van chay duoc 12.1. Gop hai thu lam mot thi hoac chan oan bo nhan
    cu, hoac de 12.2 chay tren du lieu khong du ma khong ai biet.
    """
    gaps: list[str] = []
    if not labels.game_id:
        gaps.append("game_id (khoá khối của phép hoán vị)")
    if not labels.player_id:
        gaps.append("player_id (tầng khối thứ hai khi nhiều người chơi)")
    if labels.final_placement is None:
        gaps.append("final_placement (người chơi tự khai)")
    if not any(s.verified and s.picked for s in labels.screens):
        gaps.append("chưa màn verified nào có 'picked'")
    return gaps


def _validate_screen(
    s: ScreenLabel, where: str, augments: set[str] | None, traits: set[str] | None
) -> list[str]:
    errors: list[str] = []
    if s.status not in ("draft", "verified"):
        errors.append(f"{where}: status '{s.status}' phải là draft hoặc verified")
    if s.verified and not STAGE_RE.match(s.stage):
        errors.append(f"{where}: stage '{s.stage}' phải có dạng 'x-y'")
    if s.close_s <= s.open_s:
        errors.append(f"{where}: close_s phải lớn hơn open_s")
    if not s.offers:
        errors.append(f"{where}: không có offer nào")

    for key, value in s.hud.items():
        if key not in HUD_KEYS:
            errors.append(f"{where}: hud.{key} không nằm trong {HUD_KEYS}")
        elif value is not None and not isinstance(value, int):
            errors.append(f"{where}: hud.{key} phải là số nguyên hoặc null")

    if s.traits is not None and traits is not None:
        for name in s.traits:
            if name not in traits:
                errors.append(f"{where}: tộc/hệ '{name}' không có trong name index")

    prev_at = s.open_s - 1e-9
    for k, o in enumerate(s.offers):
        ow = f"{where} offer #{k + 1}"
        if not (s.open_s <= o.at_s <= s.close_s):
            errors.append(f"{ow}: at_s {o.at_s} nằm ngoài [{s.open_s}, {s.close_s}]")
        if o.at_s <= prev_at:
            errors.append(f"{ow}: at_s phải tăng dần")
        prev_at = o.at_s
        errors.extend(_validate_offer(s, k, ow, augments))

    if s.picked is not None and s.offers:
        last = {a for c in s.offers[-1].cards for a in c}
        if s.picked not in last:
            errors.append(f"{where}: picked '{s.picked}' không có trong offer cuối")
    if s.expert is not None and not isinstance(s.expert.get("blind"), bool):
        errors.append(f"{where}: expert.blind phải là true/false")
    return errors


def _validate_offer(s: ScreenLabel, k: int, ow: str, augments: set[str] | None) -> list[str]:
    errors: list[str] = []
    o = s.offers[k]
    if len(o.cards) != SLOTS:
        return [f"{ow}: cần đúng {SLOTS} ô, có {len(o.cards)}"]

    for i, slot in enumerate(o.cards):
        if not slot and s.verified:
            errors.append(f"{ow} ô {i + 1}: trống trong màn đã verified")
        if augments is not None:
            errors.extend(f"{ow} ô {i + 1}: '{a}' không phải apiName đã biết" for a in slot if a not in augments)

    if k == 0:
        if o.rerolled_slot is not None:
            errors.append(f"{ow}: offer đầu tiên không thể có rerolled_slot")
        return errors
    if o.rerolled_slot is None or not 0 <= o.rerolled_slot < SLOTS:
        if s.verified:
            errors.append(f"{ow}: rerolled_slot phải là 0, 1 hoặc 2")
        return errors
    if s.verified:
        prev = s.offers[k - 1]
        changed = [i for i in range(SLOTS) if set(prev.cards[i]) != set(o.cards[i])]
        if changed != [o.rerolled_slot]:
            errors.append(
                f"{ow}: rerolled_slot={o.rerolled_slot} nhưng ô thực sự đổi là {changed}"
            )
    return errors


def _as_slot(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,) if value else ()
    return tuple(str(v) for v in value if v)


def _screen_to_dict(s: ScreenLabel) -> dict[str, Any]:
    return {
        "stage": s.stage,
        "status": s.status,
        "open_s": round(s.open_s, 3),
        "close_s": round(s.close_s, 3),
        "hud": s.hud,
        "traits": s.traits,
        "offers": [
            {
                "at_s": round(o.at_s, 3),
                "cards": o.cards,
                "rerolled_slot": o.rerolled_slot,
                "ocr_raw": o.ocr_raw,
                "snapshot": o.snapshot,
            }
            for o in s.offers
        ],
        "picked": s.picked,
        "expert": s.expert,
        "notes": s.notes,
    }
