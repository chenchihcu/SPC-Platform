from __future__ import annotations

import os
from pathlib import Path


def _resolved_home_fallback() -> str:
    user_profile = (os.environ.get("USERPROFILE") or "").strip()
    if user_profile:
        return user_profile

    home = (os.environ.get("HOME") or "").strip()
    if home:
        return home

    home_drive = (os.environ.get("HOMEDRIVE") or "").strip()
    home_path = (os.environ.get("HOMEPATH") or "").strip()
    combined = f"{home_drive}{home_path}".strip()
    if combined:
        return combined

    return str(Path.cwd())


def ensure_home_env() -> str:
    """
    Ensure HOME/USERPROFILE are available for libraries that rely on Path.home().

    This guard avoids startup/test failures when shell sessions do not propagate
    Windows home-directory environment variables.
    """
    fallback = _resolved_home_fallback()

    user_profile = (os.environ.get("USERPROFILE") or "").strip()
    home = (os.environ.get("HOME") or "").strip()

    if not user_profile:
        os.environ["USERPROFILE"] = fallback
    if not home:
        os.environ["HOME"] = fallback

    return (os.environ.get("USERPROFILE") or os.environ.get("HOME") or fallback).strip()

