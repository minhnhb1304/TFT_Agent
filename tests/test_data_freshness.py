"""Do tuoi du lieu + ke hoach cap nhat khi co patch moi. Khong goi mang."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from src.knowledge.data_freshness import (
    FRESH,
    MISSING,
    STALE,
    UNKNOWN,
    Dataset,
    PatchState,
    judge,
    latest_patch,
    parse_patch,
    stale_warnings,
)
from src.knowledge.data_refresh import (
    MANUAL,
    RUN,
    SKIP,
    STEPS,
    Step,
    YamlUpdate,
    build_patch_state,
    collect_votes,
    plan,
    set_yaml_scalar,
)
from src.utils.settings import Settings

ROOT = Path(__file__).resolve().parent.parent
STATE = PatchState("18.2", released_at="2026-09-10T00:00:00+00:00")


def _write(path: Path, meta: dict) -> Path:
    path.write_text(json.dumps({"meta": meta}), encoding="utf-8")
    return path


# --- patch ---------------------------------------------------------------------


def test_letter_patch_is_newer_than_base() -> None:
    assert parse_patch("18.1d") < parse_patch("18.2") < parse_patch("18.2b")
    assert parse_patch(16170) is None and parse_patch("latest") is None


def test_latest_patch_ignores_dead_sources() -> None:
    assert latest_patch(["18.2", None, "18.1d"]) == "18.2"
    assert latest_patch([None, "?"]) is None


# --- phan xu -------------------------------------------------------------------


def test_patch_scoped_file_behind_current_is_stale(tmp_path) -> None:
    ds = Dataset("augment_tiers", "patch")
    assert judge(ds, _write(tmp_path / "a.json", {"patch": "18.1d"}), STATE).status == STALE
    assert judge(ds, _write(tmp_path / "b.json", {"patch": "18.2"}), STATE).status == FRESH


def test_numeric_patch_code_falls_back_to_generation_date(tmp_path) -> None:
    """tactics.tools ghi ma 16170 - khong so duoc, phai so ngay sinh voi ngay ra patch."""
    ds = Dataset("item_stats", "patch")
    old = _write(tmp_path / "old.json", {"patch": 16170, "generated_at": "2026-09-01T17:50:20+00:00"})
    new = _write(tmp_path / "new.json", {"patch": 16171, "generated_at": "2026-09-12T00:00:00+00:00"})
    assert judge(ds, old, STATE).status == STALE
    assert judge(ds, new, STATE).status == FRESH


def test_set_scoped_file_only_goes_stale_on_new_set(tmp_path) -> None:
    ds = Dataset("name_index", "set")
    assert judge(ds, _write(tmp_path / "a.json", {"set": "TFTSet18"}), STATE).status == FRESH
    assert judge(ds, _write(tmp_path / "b.json", {"set": "TFTSet17"}), STATE).status == STALE
    assert judge(ds, _write(tmp_path / "c.json", {}), STATE).status == UNKNOWN
    assert judge(ds, tmp_path / "nope.json", STATE).status == MISSING


def test_no_patch_state_means_no_warnings(tmp_path) -> None:
    """Chua do patch lan nao thi khong phan xu - khong bia canh bao."""
    settings = Settings.load(ROOT / "config" / "settings.yaml")
    settings.data["paths"]["patch_state"] = str(tmp_path / "missing.json")
    assert stale_warnings(settings) == []


def test_advisor_surfaces_stale_data_separately_from_degraded(tmp_path) -> None:
    from src.decision.advisor import Advisor
    from src.eval.scenario_logger import ScenarioLogger
    from src.game_state.models import GameState

    settings = Settings.load(ROOT / "config" / "settings.yaml")
    (tmp_path / "state.json").write_text(json.dumps({"current_patch": "18.2"}), encoding="utf-8")
    _write(tmp_path / "tiers.json", {"patch": "18.1d"})
    settings.data["paths"]["patch_state"] = str(tmp_path / "state.json")
    settings.data["paths"]["augment_tiers"] = str(tmp_path / "tiers.json")

    bundle = Advisor(settings=settings, logger=ScenarioLogger(tmp_path / "s")).advise(GameState())
    assert any(w.startswith("augment_tiers: patch 18.1d < 18.2") for w in bundle.stale_data)
    assert not any("augment_tiers" in d for d in bundle.degraded)
    assert "stale_data" in bundle.to_dict()


# --- do patch ------------------------------------------------------------------


def test_a_crashing_probe_does_not_block_the_others() -> None:
    def boom() -> str:
        raise RuntimeError("WAF")

    assert collect_votes({"a": lambda: "18.2", "b": boom, "c": lambda: "garbage"}) == {
        "a": "18.2", "b": None, "c": None,
    }


def test_release_date_prefers_lolchess_then_previous_then_now() -> None:
    now = datetime(2026, 9, 15, tzinfo=timezone.utc)
    notes = [{"version": "18.2", "registered_at": 1789023600000}]
    s = build_patch_state({"m": "18.2"}, None, notes, now)
    assert s["released_at_source"] == "lolchess_patch_notes" and s["released_at"].startswith("2026-09-")

    prev = {"current_patch": "18.2", "released_at": "2026-09-10T00:00:00+00:00", "released_at_source": "x"}
    assert build_patch_state({"m": "18.2"}, prev, [], now)["released_at"] == prev["released_at"]

    s = build_patch_state({"m": "18.2b"}, prev, notes, now)
    assert s["released_at_source"] == "detected" and s["released_at"] == now.isoformat(timespec="seconds")


def test_no_votes_fails_loudly() -> None:
    with pytest.raises(ValueError):
        build_patch_state({"m": None}, None, [])


# --- ke hoach ------------------------------------------------------------------


def _fresh(name: str, status: str):
    from src.knowledge.data_freshness import Freshness

    return Freshness(name, Path(name), status, "")


def test_plan_runs_only_steps_with_stale_outputs() -> None:
    steps = (
        Step("crawl", ("x.py",), outputs=("tiers",)),
        Step("idle", ("y.py",), outputs=("comps",)),
        Step("hand", outputs=("stats",), manual="do it"),
        Step("tests", ("-m", "pytest")),
    )
    fresh = [_fresh("tiers", STALE), _fresh("comps", FRESH), _fresh("stats", STALE)]
    decisions = {p.step.name: p.decision for p in plan(steps, fresh, "18.2", {})}
    assert decisions == {"crawl": RUN, "idle": SKIP, "hand": MANUAL, "tests": RUN}
    assert {p.step.name: p.decision for p in plan(steps, fresh, "18.2", {}, force=True)}["idle"] == RUN


def test_plan_respects_dead_source_until_retry_patch() -> None:
    step = (Step("tt", ("x.py",), outputs=("stats",), source_key="placement_stats.tt"),)
    sources = {"placement_stats": {"tt": {"status": "dead", "do_not_retry_before": "18.3"}}}
    fresh = [_fresh("stats", STALE)]
    assert plan(step, fresh, "18.2", sources)[0].decision == SKIP
    assert plan(step, fresh, "18.3", sources)[0].decision == RUN


def test_step_outputs_are_known_datasets() -> None:
    from src.knowledge.data_freshness import DATASETS

    known = {d.name for d in DATASETS}
    for step in STEPS:
        assert set(step.outputs) <= known, step.name
        for arg in step.argv:
            if arg.endswith(".py"):
                assert (ROOT / arg).exists(), arg


def test_step_command_fills_patch_and_set() -> None:
    step = Step("s", ("a.py", "--set", "{set}", "--patch", "{patch}"))
    assert step.command("18.2b") == ["a.py", "--set", "18", "--patch", "18.2b"]


# --- data_sources.yaml -----------------------------------------------------------


def test_yaml_edit_keeps_comments_and_hits_the_right_nested_key() -> None:
    text = (
        "# dau file\n"
        "meta:\n"
        "  set: TFTSet18\n"
        '  patch: "18.1"\n'
        "  updated: 2026-09-07\n"
        "static:\n"
        "  cdragon:\n"
        "    url: https://x/  # ghi chu\n"
        "    last_verified: 2026-08-31\n"
        "  other:\n"
        "    last_verified: null\n"
    )
    out = YamlUpdate("18.2", "2026-09-15", ["static.cdragon"]).apply(text)
    assert "# dau file" in out and "# ghi chu" in out
    parsed = yaml.safe_load(out)
    assert parsed["meta"]["patch"] == "18.2"
    assert str(parsed["meta"]["updated"]) == "2026-09-15"
    assert str(parsed["static"]["cdragon"]["last_verified"]) == "2026-09-15"
    assert parsed["static"]["other"]["last_verified"] is None


def test_yaml_edit_unknown_key_raises() -> None:
    with pytest.raises(KeyError):
        set_yaml_scalar("a:\n  b: 1\n", "a.c", "2")


def test_real_data_sources_yaml_accepts_the_update() -> None:
    text = (ROOT / "config" / "data_sources.yaml").read_text(encoding="utf-8")
    keys = [s.source_key for s in STEPS if s.source_key]
    out = YamlUpdate("18.2", "2026-09-15", keys).apply(text)
    assert yaml.safe_load(out)["meta"]["patch"] == "18.2"
    assert out.count("\n") == text.count("\n")
