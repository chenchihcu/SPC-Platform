from __future__ import annotations

import warnings
from io import BytesIO

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from app.charts.mpl_font_config import setup_mpl_cjk_font


def test_chart_text_renders_without_glyph_missing_warning() -> None:
    setup_mpl_cjk_font()

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fig, ax = plt.subplots(figsize=(4, 3), dpi=100)
        ax.set_title("三特徵整體分布概覽 - 多特徵比較")
        ax.set_xlabel("元件或群組 (Component / Subgroup)")
        ax.set_ylabel("量測值 (Measurement)")
        ax.text(0.5, 0.5, "mu0=1.234, hσ=4.0", ha="center", va="center", transform=ax.transAxes)
        buf = BytesIO()
        fig.savefig(buf, format="png")
        plt.close(fig)

    glyph_warnings = [str(w.message) for w in caught if "Glyph" in str(w.message)]
    assert not glyph_warnings, f"Unexpected glyph-missing warning: {glyph_warnings[:3]}"
