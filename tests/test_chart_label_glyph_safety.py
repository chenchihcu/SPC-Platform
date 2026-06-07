from __future__ import annotations

from pathlib import Path


_BLOCKED_TOKENS = ("μ₀", "₀", "平均値", "✓", "✗", "MR̄")
_TARGET_DIRS = ("app/charts", "app/ui/tabs")


def test_chart_code_avoids_high_risk_glyph_tokens() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    violations: list[str] = []

    for rel_dir in _TARGET_DIRS:
        for path in (repo_root / rel_dir).rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for token in _BLOCKED_TOKENS:
                if token in text:
                    violations.append(f"{path.relative_to(repo_root)} contains blocked token '{token}'")

    assert not violations, "High-risk glyph token regression:\n" + "\n".join(violations)
