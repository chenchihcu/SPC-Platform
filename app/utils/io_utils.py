# -*- coding: utf-8 -*-
import os
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _unlink_tmp_best_effort(tmp_path: str) -> None:
    if not os.path.exists(tmp_path):
        return
    try:
        os.remove(tmp_path)
    except OSError:
        pass


def atomic_save_json(path: str, data: Any, indent: int = 4) -> bool:
    """
    Atomic save to prevent data corruption (Pass 124).
    Writes to .tmp then replaces the original file.
    """
    tmp_path = f"{path}.tmp"
    try:
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())  # Ensure data is on physical disk
            
        os.replace(tmp_path, path)
        return True
    except (OSError, TypeError, ValueError, OverflowError) as e:
        logger.error(f"Atomic save failed for {path}: {e}")
        _unlink_tmp_best_effort(tmp_path)
        return False


def atomic_save_text(path: str, content: str) -> bool:
    """Atomic save for plain text."""
    tmp_path = f"{path}.tmp"
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
        return True
    except (OSError, TypeError, ValueError) as e:
        logger.error(f"Atomic save failed for {path}: {e}")
        _unlink_tmp_best_effort(tmp_path)
        return False
