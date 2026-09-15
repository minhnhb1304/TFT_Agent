"""Cap nhat data/ khi co patch moi - mot lenh cho ca chuoi crawl.

    python scripts/refresh_data.py --check        # OFFLINE: bang nao da cu, khong goi mang
    python scripts/refresh_data.py --dry-run      # do patch, in ke hoach, khong chay gi
    python scripts/refresh_data.py                # do patch, chay cac buoc can thiet
    python scripts/refresh_data.py --force        # chay moi buoc tu dong du output con moi
    python scripts/refresh_data.py --only crawl_metatft_tiers crawl_metatft_comps

TRINH TU
    1. Hoi MetaTFT, TFT Academy, lolchess -> data/patch_state.json
    2. Buoc nao co output stale/missing thi chay (xem STEPS trong
       src/knowledge/data_refresh.py). Mot buoc hong KHONG dung ca chuoi.
    3. Kiem lai do tuoi, ghi meta.patch / last_verified vao config/data_sources.yaml.

Ma thoat 1 neu con buoc hong, buoc phai lam tay, hoac bang con cu - de CI
hay nguoi chay nhin thay ngay.

lolchess dat AWS WAF: buoc crawl_lolchess_guide thuong hong o day. Huong dan
luu trang bang trinh duyet nam trong scripts/crawl_lolchess_guide.py.
"""

from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.knowledge.data_freshness import STALE, UNREADABLE, check_all  # noqa: E402
from src.knowledge.data_refresh import (  # noqa: E402
    MANUAL,
    RUN,
    STEPS,
    YamlUpdate,
    build_patch_state,
    collect_votes,
    plan,
)
from src.utils.settings import Settings  # noqa: E402

SOURCES_YAML = ROOT / "config" / "data_sources.yaml"


def _probes() -> dict:
    from src.knowledge.lolchess_guide import LolchessClient, parse_patch_list
    from src.knowledge.metatft import MetaTFTClient
    from src.knowledge.tftacademy import TFTAcademyClient

    def lolchess() -> str | None:
        notes = parse_patch_list(LolchessClient().get("/guide/patch-notes"))
        return notes[-1]["version"] if notes else None

    return {
        "metatft": lambda: MetaTFTClient().get_patch_info().get("patch"),
        "tftacademy": lambda: TFTAcademyClient().get_patch_info().get("patch"),
        "lolchess": lolchess,
    }


def _read_json(path: Path) -> dict | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def detect(settings: Settings) -> dict:
    votes = collect_votes(_probes())
    guide = _read_json(ROOT / "data" / "lolchess_guide.json") or {}
    state_path = settings.path("patch_state")
    state = build_patch_state(votes, _read_json(state_path), guide.get("patches") or [])
    state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"patch hien tai: {state['current_patch']}  (phieu: {votes})")
    print(f"  ra ngay: {state['released_at']} [{state['released_at_source']}] -> {state_path.name}")
    return state


def report(settings: Settings) -> list:
    state, results = check_all(settings)
    if state is None:
        print("chua co data/patch_state.json - chay `python scripts/refresh_data.py --dry-run` truoc")
        return []
    print(f"\ndo tuoi du lieu so voi patch {state.current_patch}:")
    for r in results:
        print(f"  {r.status:10s} {r.dataset:22s} {r.detail}")
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="chi bao cao do tuoi, khong goi mang")
    parser.add_argument("--dry-run", action="store_true", help="do patch + in ke hoach, khong chay buoc nao")
    parser.add_argument("--force", action="store_true", help="chay ca buoc co output con moi")
    parser.add_argument("--only", nargs="+", choices=[s.name for s in STEPS], help="chi xet cac buoc nay")
    args = parser.parse_args(argv)

    settings = Settings.load(ROOT / "config" / "settings.yaml")
    if args.check:
        results = report(settings)
        return 0 if results and all(r.status not in (STALE, UNREADABLE) for r in results) else 1

    try:
        state = detect(settings)
    except ValueError as exc:
        print(f"LOI: {exc}", file=sys.stderr)
        return 1
    patch = state["current_patch"]

    sources = yaml.safe_load(SOURCES_YAML.read_text(encoding="utf-8")) or {}
    _, before = check_all(settings)
    steps = plan(STEPS, before, patch, sources, force=args.force, only=set(args.only) if args.only else None)

    print("\nke hoach:")
    for p in steps:
        print(f"  {p.decision:7s} {p.step.name:24s} {p.reason}")
    if args.dry_run:
        return 0

    failed, verified = [], []
    for p in steps:
        if p.decision != RUN:
            continue
        cmd = [sys.executable, *p.step.command(patch)]
        print(f"\n>>> {p.step.name}: {' '.join(cmd[1:])}", flush=True)
        if subprocess.run(cmd, cwd=ROOT).returncode != 0:
            failed.append(p.step.name)
        elif p.step.source_key:
            verified.append(p.step.source_key)

    after = report(settings)
    today = datetime.now(timezone.utc).date().isoformat()
    SOURCES_YAML.write_text(
        YamlUpdate(patch, today, verified).apply(SOURCES_YAML.read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    print(f"\nda ghi meta.patch={patch} vao {SOURCES_YAML.name}" + (f", last_verified: {verified}" if verified else ""))

    manual = [p for p in steps if p.decision == MANUAL]
    still_stale = [r.dataset for r in after if r.status in (STALE, UNREADABLE)]
    if failed:
        print(f"buoc hong: {failed}")
    for p in manual:
        print(f"lam tay: {p.step.name}: {p.step.manual}")
    if still_stale:
        print(f"con cu: {still_stale}")
    return 1 if failed or manual or still_stale else 0


if __name__ == "__main__":
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
