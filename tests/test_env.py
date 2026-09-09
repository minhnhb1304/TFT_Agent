"""Test loader .env (feedback Tier 1 #4/#5).

Hai bat bien quan trong:

    1. KHONG BAO GIO ghi de bien da co san trong moi truong. Nguoi dung dat
       `$env:RIOT_API_KEY=...` de thu mot key khac thi .env khong duoc pha.
    2. KHONG BAO GIO in gia tri key. `describe()` chi noi co hay khong; loi
       cua `require()` chi noi phai lam gi de co key.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.utils.env import describe, load_env, parse_env, require


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Khong test nao duoc de lai rac trong os.environ cua test khac."""
    for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "RIOT_API_KEY", "TFT_TEST_KEY"):
        monkeypatch.delenv(key, raising=False)


# --- Doc dinh dang ---------------------------------------------------------


def test_parses_plain_pairs() -> None:
    assert parse_env("A=1\nB=2") == {"A": "1", "B": "2"}


def test_strips_comments_and_blank_lines() -> None:
    assert parse_env("# chu thich\n\nA=1\n   \n") == {"A": "1"}


def test_strips_surrounding_quotes() -> None:
    """Key cua Riot bat dau bang RGAPI- nen nguoi ta hay boc nhay."""
    assert parse_env('A="RGAPI-x"\nB=\'y\'') == {"A": "RGAPI-x", "B": "y"}


def test_accepts_shell_export_prefix() -> None:
    """Dan tu mot dong `export ...` trong shell la chuyen rat hay xay ra."""
    assert parse_env("export RIOT_API_KEY=abc") == {"RIOT_API_KEY": "abc"}


def test_value_may_contain_equals_signs() -> None:
    assert parse_env("A=a=b=c") == {"A": "a=b=c"}


def test_empty_value_is_kept_not_dropped() -> None:
    """`GEMINI_API_KEY=` trong .env.example phai doc ra chuoi rong."""
    assert parse_env("A=") == {"A": ""}


def test_malformed_lines_are_skipped_not_raised() -> None:
    """Mot dong thua khong dang lam sap ca pipeline crawl."""
    assert parse_env("khong co dau bang\nA=1\n=khong co ten") == {"A": "1"}


# --- Do vao os.environ -----------------------------------------------------


def test_missing_file_is_not_an_error() -> None:
    """Track A chay duoc ma khong can key nao."""
    assert load_env("khong/ton/tai/.env") == []


def test_loads_into_environ_and_reports_names_only(tmp_path: Path) -> None:
    p = tmp_path / ".env"
    p.write_text("TFT_TEST_KEY=secret-value\n", encoding="utf-8")

    loaded = load_env(p)
    assert loaded == ["TFT_TEST_KEY"]
    assert os.environ["TFT_TEST_KEY"] == "secret-value"
    # Ten key duoc tra ve, gia tri thi khong.
    assert "secret-value" not in loaded


def test_existing_environment_wins_over_the_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bat bien so 1: .env khong duoc pha bien nguoi dung dat tay."""
    monkeypatch.setenv("TFT_TEST_KEY", "tu-shell")
    p = tmp_path / ".env"
    p.write_text("TFT_TEST_KEY=tu-file\n", encoding="utf-8")

    assert load_env(p) == []
    assert os.environ["TFT_TEST_KEY"] == "tu-shell"


def test_empty_environment_variable_wins_over_the_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bien dat rong trong shell (vi du xoa key tam thoi) khong bi .env ghi de."""
    monkeypatch.setenv("TFT_TEST_KEY", "")
    p = tmp_path / ".env"
    p.write_text("TFT_TEST_KEY=tu-file\n", encoding="utf-8")

    assert load_env(p) == []
    assert os.environ["TFT_TEST_KEY"] == ""


def test_override_flag_reverses_that(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TFT_TEST_KEY", "tu-shell")
    p = tmp_path / ".env"
    p.write_text("TFT_TEST_KEY=tu-file\n", encoding="utf-8")

    assert load_env(p, override=True) == ["TFT_TEST_KEY"]
    assert os.environ["TFT_TEST_KEY"] == "tu-file"


# --- require / describe ----------------------------------------------------


def test_require_returns_the_value_when_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TFT_TEST_KEY", "abc")
    assert require("TFT_TEST_KEY") == "abc"


def test_require_error_says_what_to_do_and_leaks_nothing() -> None:
    with pytest.raises(RuntimeError) as exc:
        require("RIOT_API_KEY", "het han sau 24 gio")
    message = str(exc.value)
    assert ".env" in message
    assert "RIOT_API_KEY" in message
    assert "het han sau 24 gio" in message


def test_describe_reports_presence_never_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bat bien so 2: khong co duong nao de describe() lam lo mot key."""
    monkeypatch.setenv("GEMINI_API_KEY", "sieu-bi-mat")
    state = describe()
    assert state["GEMINI_API_KEY"] is True
    assert state["RIOT_API_KEY"] is False
    assert all(isinstance(v, bool) for v in state.values())
    assert "sieu-bi-mat" not in str(state)


# --- File mau da commit ----------------------------------------------------


def test_example_file_lists_the_keys_the_project_uses() -> None:
    """`.env.example` duoc commit; `.env` thi khong. Kiem tra no khong lech."""
    example = Path(".env.example")
    if not example.exists():
        pytest.skip("chua co .env.example")
    parsed = parse_env(example.read_text(encoding="utf-8"))
    assert set(parsed) == {"GEMINI_API_KEY", "RIOT_API_KEY"}
    # Mau phai TRONG - dien key vao roi commit la kieu ro ri kinh dien.
    assert all(v == "" for v in parsed.values())
