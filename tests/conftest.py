from __future__ import annotations

from app.bootstrap.dpi import setup_high_dpi
from app.bootstrap.runtime_env import ensure_home_env

# Some shells in this environment do not provide HOME/USERPROFILE.
# Ensure a stable home path before importing matplotlib-dependent modules.
ensure_home_env()

# Must run before any test module constructs a QApplication (Qt warns if the
# DPI policy is set after the QGuiApplication instance already exists).
setup_high_dpi()

