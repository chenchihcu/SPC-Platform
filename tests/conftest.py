from __future__ import annotations

from app.bootstrap.runtime_env import ensure_home_env

# Some shells in this environment do not provide HOME/USERPROFILE.
# Ensure a stable home path before importing matplotlib-dependent modules.
ensure_home_env()

