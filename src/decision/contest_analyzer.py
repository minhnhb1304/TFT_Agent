"""contest_score - bao nhieu doi thu dang tranh comp cua minh (SPEC 3.5.2, Phase 7).

TRANG THAI: feature-flag `enable_scouting`, MAC DINH TAT.

Vi sao viet code truoc khi bat: phan tinh toan o day khong can thi giac may
tinh gi ca - no chi can `state.opponents`. Cai chua co la phan DOC board doi
thu qua scoreboard (khoi luong CV lon, do nhieu cao, thuoc Track B). Tach hai
thu ra co nghia la khi reader san sang thi chi can bat co, khong phai viet
them thuat toan.

Vi sao mac dinh tat: SPEC 3.3 - doc board 7 nguoi khac ton nhieu cong CV va
khong duoc phep an vao thoi gian cua Augment Advisor, thu moi la trong tam
do an. Va quan trong hon: `contest_score` tinh tu du lieu nhieu, nen no PHAI
mang theo do tin cay chu khong duoc tra ve mot con so tran trui.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..game_state.models import GameState, OpponentBoard
from ..knowledge.comp_database import MetaComp

# So doi thu toi da trong mot lobby TFT (8 nguoi, tru minh).
MAX_OPPONENTS = 7

# Bao nhieu core unit trung thi coi la dang tranh cung mot huong.
CONTEST_UNIT_THRESHOLD = 2

# Duoi muc tin cay nay thi board doc duoc coi nhu khong doc duoc. Doc nham
# board doi thu roi khuyen nguoi choi doi huong la kieu sai dat gia nhat.
MIN_BOARD_CONFIDENCE = 0.5


@dataclass
class ContestResult:
    """Ket qua phan tich tranh chap cho MOT comp."""

    comp_name: str
    contesting: list[int] = field(default_factory=list)   # slot cua doi thu
    score: float = 0.0                                    # <= 0, cang am cang tranh
    confidence: float = 0.0
    reason: str = ""

    @property
    def is_contested(self) -> bool:
        return bool(self.contesting)


def usable_boards(state: GameState) -> list[OpponentBoard]:
    """Chi giu board doc du ro. Board mo -> bo, khong doan."""
    return [o for o in state.opponents if o.confidence >= MIN_BOARD_CONFIDENCE]


def analyze(comp: MetaComp, state: GameState, enabled: bool = False) -> ContestResult:
    """Tinh contest_score cho mot comp.

    Args:
        enabled: co `enable_scouting`. Khi tat -> tra ve score 0.0 va noi ro
            ly do, KHONG tra ve mot so nhu the da tinh that.

    Returns:
        ContestResult voi score trong [-1, 0]. 0 nghia la khong tranh chap
        HOAC khong biet - hai truong hop nay phan biet nhau bang `confidence`.
    """
    if not enabled:
        return ContestResult(comp.name, [], 0.0, 0.0, "Scouting đang tắt — không tính tranh chấp")

    boards = usable_boards(state)
    if not boards:
        return ContestResult(
            comp.name, [], 0.0, 0.0, "Chưa đọc được board đối thủ nào đủ rõ"
        )

    core = {u.lower() for u in comp.core_units}
    contesting: list[int] = []
    for board in boards:
        overlap = core & {u.lower() for u in board.units}
        if len(overlap) >= CONTEST_UNIT_THRESHOLD:
            contesting.append(board.slot)

    score = -len(contesting) / MAX_OPPONENTS
    confidence = sum(b.confidence for b in boards) / len(boards)

    if contesting:
        reason = (
            f"{len(contesting)} đối thủ đang tranh {comp.name} "
            f"(vị trí {', '.join(str(s) for s in contesting)})"
        )
    else:
        reason = f"Không ai tranh {comp.name} trong {len(boards)} board đọc được"

    return ContestResult(comp.name, contesting, score, confidence, reason)
