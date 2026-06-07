"""Step 6: golden scenario manifests expose release-validation contract fields."""

from __future__ import annotations

import json
from pathlib import Path


def _scenario_dirs(golden_root: Path) -> list[Path]:
    return sorted(p for p in golden_root.iterdir() if p.is_dir() and (p / "expected" / "manifest.json").is_file())


def test_manifest_has_core_and_determinism(golden_root: Path) -> None:
    for scenario_dir in _scenario_dirs(golden_root):
        mp = scenario_dir / "expected" / "manifest.json"
        doc = json.loads(mp.read_text(encoding="utf-8"))
        assert doc.get("scenario_id") == scenario_dir.name, scenario_dir.name
        assert doc.get("schema_version") == "1", scenario_dir.name
        assert "dataset_version" in doc, scenario_dir.name
        assert "determinism" in doc, scenario_dir.name
        det = doc["determinism"]
        assert det.get("required_seed") == 42, scenario_dir.name
        assert isinstance(det.get("engine_seed_params"), dict), scenario_dir.name
        notes = det.get("notes")
        assert isinstance(notes, str) and notes.strip(), f"{scenario_dir.name}: determinism.notes required"
