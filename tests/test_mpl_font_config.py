from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

from app.charts.mpl_font_config import _available_cjk_fonts, setup_mpl_cjk_font


def test_setup_mpl_cjk_font_prefers_cjk_before_dejavu() -> None:
    setup_mpl_cjk_font()
    sans = list(matplotlib.rcParams.get("font.sans-serif", []))

    assert "DejaVu Sans" in sans, "Expected DejaVu Sans fallback to remain available."
    dejavu_idx = sans.index("DejaVu Sans")

    preferred_cjk = [f for f in _available_cjk_fonts() if f != "DejaVu Sans"]
    assert preferred_cjk, "Expected at least one available CJK font candidate."

    first_cjk_idx = min(sans.index(f) for f in preferred_cjk if f in sans)
    assert first_cjk_idx < dejavu_idx, (
        "CJK font must be prioritized before DejaVu Sans to avoid tofu glyphs."
    )
    assert list(matplotlib.rcParams.get("font.family", [])) == ["sans-serif"]
