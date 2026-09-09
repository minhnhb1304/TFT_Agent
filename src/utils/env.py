"""Nap bien moi truong tu file .env - feedback Tier 1 #4/#5.

VI SAO TU VIET THAY VI DUNG python-dotenv
    Ta chi can dung mot thu: doc file KEY=VALUE roi do vao os.environ. Them
    mot dependency runtime cho viec do la khong dang, nhat la voi mot du an
    ma moi dong requirements.txt deu phai giai trinh duoc wheel cp314.

NGUYEN TAC
    - KHONG BAO GIO ghi de bien da co san trong moi truong. Bien that phai
      thang file: nguoi dung `$env:RIOT_API_KEY=...` de doi tam mot key thi
      .env khong duoc pha viec do.
    - Thieu file KHONG phai loi. Track A chay duoc ma khong can key nao.
    - KHONG BAO GIO in gia tri key ra. `describe()` chi noi CO hay KHONG.

.env DA NAM TRONG .gitignore. Dung bao gio commit no.

Dinh dang chap nhan:

    # comment
    GEMINI_API_KEY=abc123
    RIOT_API_KEY="RGAPI-..."      # nhay kep hoac don deu duoc, se bi bo
    export RIOT_API_KEY=RGAPI-... # tien to `export` cua shell cung duoc bo
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_ENV_FILE = ".env"

# Cac key du an nay biet den. Chi dung cho describe() - load_env khong loc.
KNOWN_KEYS = ("GEMINI_API_KEY", "GOOGLE_API_KEY", "RIOT_API_KEY")


def parse_env(text: str) -> dict[str, str]:
    """Doc noi dung .env thanh dict. Dong hong thi BO QUA, khong nem.

    Bo qua thay vi nem vi mot dong thua trong .env khong dang lam sap ca
    pipeline - va thong bao loi ve .env rat de vo tinh lam lo gia tri.
    """
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()

        key, _, value = line.partition("=")
        key = key.strip()
        if not key:
            continue

        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        out[key] = value
    return out


def load_env(path: str | Path = DEFAULT_ENV_FILE, override: bool = False) -> list[str]:
    """Do .env vao os.environ. Tra ve ten cac key DA NAP (khong kem gia tri).

    Args:
        override: mac dinh False - bien da co san trong moi truong thang file.

    Returns:
        Danh sach ten key vua duoc dat. Rong neu khong co file, hoac moi key
        trong file deu da co san trong moi truong.
    """
    p = Path(path)
    if not p.exists():
        return []

    loaded: list[str] = []
    for key, value in parse_env(p.read_text(encoding="utf-8")).items():
        if not override and key in os.environ:
            continue
        os.environ[key] = value
        loaded.append(key)
    return sorted(loaded)


def require(name: str, hint: str = "") -> str:
    """Doc mot bien bat buoc. Nem voi thong bao dung viec neu thieu.

    KHONG in gia tri. Thong bao chi noi phai lam gi de co no.
    """
    value = os.environ.get(name)
    if not value:
        extra = f" {hint}" if hint else ""
        raise RuntimeError(
            f"thieu {name}. Them vao file .env o thu muc goc "
            f"(`{name}=...`) hoac dat bien moi truong.{extra}"
        )
    return value


def describe(keys: tuple[str, ...] = KNOWN_KEYS) -> dict[str, bool]:
    """Key nao dang co mat. CHI tra True/False - khong bao gio tra gia tri."""
    return {k: bool(os.environ.get(k)) for k in keys}
