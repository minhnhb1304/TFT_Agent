"""Cap nhat du lieu khi co patch moi - phan logic cua scripts/refresh_data.py.

BA VIEC, TACH RIENG DE TEST DUOC KHONG CAN MANG
    1. Do patch hien tai: hoi nhieu nguon, lay patch LON NHAT (mot nguon co
       the tre, nhung khong nguon nao bao mot patch chua ra).
    2. Len ke hoach: buoc nao chay, buoc nao bo qua, buoc nao phai lam tay.
       Buoc chi chay khi mot bang no sinh ra dang stale/missing (hoac --force).
    3. Ghi lai vao config/data_sources.yaml BANG CACH SUA DONG, khong dump
       lai YAML - file do song nho phan ghi chu, dump la mat het.

CHI SCRIPT OFFLINE DUOC GOI MANG. Runtime chi doc data/patch_state.json
(xem data_freshness.py).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from .data_freshness import MISSING, STALE, Freshness, latest_patch, parse_patch

# -- 1. do patch ------------------------------------------------------------------


def collect_votes(probes: dict[str, Callable[[], str | None]]) -> dict[str, str | None]:
    """Goi tung nguon; nguon hong tra None chu khong keo ca lan do."""
    votes: dict[str, str | None] = {}
    for name, probe in probes.items():
        try:
            value = probe()
        except Exception:  # noqa: BLE001 - mot nguon chet khong duoc chan cac nguon khac
            value = None
        votes[name] = value if parse_patch(value) else None
    return votes


def build_patch_state(
    votes: dict[str, str | None],
    previous: dict[str, Any] | None,
    lolchess_patches: list[dict[str, Any]],
    now: datetime | None = None,
) -> dict[str, Any]:
    """Noi dung moi cua data/patch_state.json.

    released_at uu tien, theo thu tu:
      - `registered_at` cua dung ban do trong danh sach patch notes lolchess
      - released_at cu, neu patch khong doi
      - thoi diem do (released_at_source = "detected") - tre hon ngay ra that
    """
    current = latest_patch(list(votes.values()))
    if current is None:
        raise ValueError(f"khong nguon nao tra patch hop le: {votes}")
    now = now or datetime.now(timezone.utc)

    released_at, source = None, None
    for note in lolchess_patches:
        if note.get("version") == current and note.get("registered_at"):
            ts = datetime.fromtimestamp(note["registered_at"] / 1000, tz=timezone.utc)
            released_at, source = ts.isoformat(timespec="seconds"), "lolchess_patch_notes"
    if released_at is None and previous and previous.get("current_patch") == current:
        released_at, source = previous.get("released_at"), previous.get("released_at_source")
    if released_at is None:
        released_at, source = now.isoformat(timespec="seconds"), "detected"

    return {
        "current_patch": current,
        "released_at": released_at,
        "released_at_source": source,
        "detected_at": now.isoformat(timespec="seconds"),
        "votes": votes,
    }


# -- 2. ke hoach ------------------------------------------------------------------

RUN, SKIP, MANUAL = "run", "skip", "manual"


@dataclass(frozen=True)
class Step:
    """Mot buoc cap nhat.

    argv: tham so sau `python`; `{patch}` va `{set}` duoc thay luc chay.
    outputs: bang (ten trong data_freshness.DATASETS) ma buoc nay sinh ra.
        Rong nghia la luon chay (vi du test drift).
    source_key: duong dan cham trong data_sources.yaml; `status: dead` chua
        toi `do_not_retry_before` thi bo qua, chay xong thi cap nhat last_verified.
    manual: khac None -> khong tu chay, in huong dan nay khi output con cu.
    """

    name: str
    argv: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    source_key: str | None = None
    manual: str | None = None

    def command(self, patch: str) -> list[str]:
        major = str(parse_patch(patch)[0])
        return [a.replace("{patch}", patch).replace("{set}", major) for a in self.argv]


# Thu tu la co y: locale truoc cac bang sinh tu locale; bang tier TFT Academy
# truoc MetaTFT vi crawl_metatft_tiers doi chieu voi data/augment_tiers.json.
STEPS: tuple[Step, ...] = (
    Step("fetch_locale", ("scripts/fetch_locale.py",),
         outputs=("name_index", "champion_costs", "item_recipes"), source_key="static.cdragon"),
    Step("build_game_tables", ("scripts/build_game_tables.py",), outputs=("champion_costs", "item_recipes")),
    Step("build_name_index", ("scripts/build_name_index.py",), outputs=("name_index",)),
    Step("augment_features", outputs=("augment_features",),
         manual="python scripts/build_augment_features.py --llm --diff, xem roi --write "
                "(ghi de mat phan LLM da duyet tay nen khong tu chay)"),
    Step("crawl_tftacademy_tiers",
         ("scripts/crawl_tftacademy_tiers.py", "--set", "{set}", "--patch", "{patch}", "--overwrite"),
         outputs=("augment_tiers",)),
    Step("crawl_metatft_tiers",
         ("scripts/crawl_metatft_tiers.py", "--set", "{set}", "--patch", "{patch}", "--overwrite"),
         outputs=("augment_tiers_backup",)),
    Step("crawl_tftacademy_comps",
         ("scripts/crawl_tftacademy_comps.py", "--set", "{set}", "--patch", "{patch}", "--overwrite"),
         outputs=("meta_comps",)),
    Step("crawl_metatft_comps", ("scripts/crawl_metatft_comps.py", "--patch", "{patch}", "--overwrite"),
         outputs=("meta_comps_backup",)),
    Step("crawl_lolchess_guide", ("scripts/crawl_lolchess_guide.py",), outputs=("lolchess_guide",)),
    Step("item_stats", outputs=("item_stats",),
         manual="cap nhat SET18_PATCH trong src/knowledge/tactics_tools.py (ma patch cua "
                "tactics.tools, khong suy ra duoc tu '18.x'), roi "
                "python scripts/crawl_tactics_tools.py --rank all --overwrite"),
    Step("lolchess_drift_tests", ("-m", "pytest", "tests/test_lolchess_guide.py", "-q")),
)


@dataclass
class PlannedStep:
    step: Step
    decision: str
    reason: str


def _lookup(tree: Any, dotted: str) -> Any:
    for part in dotted.split("."):
        if not isinstance(tree, dict):
            return None
        tree = tree.get(part)
    return tree


def plan(
    steps: tuple[Step, ...],
    freshness: list[Freshness],
    current_patch: str,
    sources: dict[str, Any],
    force: bool = False,
    only: set[str] | None = None,
) -> list[PlannedStep]:
    by_name = {f.dataset: f for f in freshness}
    out: list[PlannedStep] = []
    for step in steps:
        if only is not None and step.name not in only:
            continue
        needing = [
            f"{n}={by_name[n].status}" for n in step.outputs
            if n in by_name and by_name[n].status in (STALE, MISSING)
        ]
        if step.outputs and not needing and not force:
            out.append(PlannedStep(step, SKIP, "output con moi"))
            continue
        reason = ", ".join(needing) if needing else ("--force" if step.outputs else "luon chay")

        entry = _lookup(sources, step.source_key) if step.source_key else None
        if isinstance(entry, dict) and entry.get("status") == "dead":
            retry = entry.get("do_not_retry_before")
            if not parse_patch(retry) or parse_patch(current_patch) < parse_patch(retry):
                out.append(PlannedStep(step, SKIP, f"{step.source_key} dead, do_not_retry_before={retry}"))
                continue

        if step.manual:
            out.append(PlannedStep(step, MANUAL, f"{reason} -> {step.manual}"))
        else:
            out.append(PlannedStep(step, RUN, reason))
    return out


# -- 3. ghi lai data_sources.yaml -------------------------------------------------

_KEY_LINE = re.compile(r"^(\s*)([A-Za-z_][\w-]*):(\s*)(.*)$")


def set_yaml_scalar(text: str, dotted: str, literal: str) -> str:
    """Thay gia tri vo huong tai `dotted`, giu nguyen ghi chu cuoi dong va moi dong khac.

    Chi hieu mapping long nhau bang thut dong - du cho data_sources.yaml.
    Khong tim thay khoa thi no ra KeyError: sua nham cho con te hon khong sua.
    """
    target = dotted.split(".")
    stack: list[tuple[int, str]] = []
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        m = _KEY_LINE.match(line.rstrip("\r\n"))
        if not m:
            continue
        indent, key = len(m.group(1)), m.group(2)
        while stack and stack[-1][0] >= indent:
            stack.pop()
        stack.append((indent, key))
        if [k for _, k in stack] == target:
            rest = m.group(4)
            comment = ""
            cm = re.search(r"\s+#.*$", rest)
            if cm and not rest.lstrip().startswith(("'", '"')):
                comment = cm.group(0)
            ending = line[len(line.rstrip("\r\n")):]
            lines[i] = f"{m.group(1)}{key}: {literal}{comment}{ending}"
            return "".join(lines)
    raise KeyError(dotted)


@dataclass
class YamlUpdate:
    patch: str
    today: str
    verified: list[str] = field(default_factory=list)

    def apply(self, text: str) -> str:
        text = set_yaml_scalar(text, "meta.patch", f'"{self.patch}"')
        text = set_yaml_scalar(text, "meta.updated", self.today)
        for key in self.verified:
            text = set_yaml_scalar(text, f"{key}.last_verified", self.today)
        return text
