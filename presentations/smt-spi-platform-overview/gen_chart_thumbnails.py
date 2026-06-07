"""
產生簡報用圖表示意縮圖（16:9 長方形畫布，淺色標準圖表風格，接近簡報／Sheets 示意）。
執行：python gen_chart_thumbnails.py
輸出：assets/chart_thumbs/*.png
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

OUT = Path(__file__).resolve().parent / "assets" / "chart_thumbs"
# Google 簡報風：白底、清晰座標區為長方形
FIG_W, FIG_H = 4.0, 2.25  # 16:9
DPI = 128
BG = "#FFFFFF"
PANEL = "#FFFFFF"
LINE = "#1A73E8"
CL = "#34A853"
UCL = "#EA4335"
GRID = "#DADCE0"
TEXT = "#202124"
TITLE_SZ = 8


def _frame(ax, title: str) -> None:
    ax.set_facecolor(PANEL)
    ax.set_title(title, color=TEXT, fontsize=TITLE_SZ, pad=6, fontweight="600")
    ax.tick_params(colors="#5F6368", labelsize=6)
    for s in ax.spines.values():
        s.set_visible(True)
        s.set_color(GRID)
        s.set_linewidth(0.8)


def _subplot_rect() -> tuple[plt.Figure, plt.Axes]:
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.patch.set_facecolor(BG)
    fig.subplots_adjust(left=0.1, right=0.96, top=0.82, bottom=0.18)
    return fig, ax


def _save_thumb(fig: plt.Figure, filename: str) -> None:
    fig.savefig(OUT / filename, facecolor=BG, edgecolor="none")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(42)

    # 1 I-MR
    fig, ax = _subplot_rect()
    x = np.arange(28)
    y = np.cumsum(rng.normal(0, 0.12, len(x))) + 10
    ax.plot(x, y, color=LINE, lw=1.4)
    ax.axhline(10.0, color=CL, ls="--", lw=1.0)
    ax.axhline(9.25, color=UCL, ls="--", lw=0.9)
    ax.axhline(10.75, color=UCL, ls="--", lw=0.9)
    ax.set_xticks([])
    ax.set_yticks([])
    _frame(ax, "I-MR / SPC")
    _save_thumb(fig, "thumb_imr.png")

    # 2 Run
    fig, ax = _subplot_rect()
    y2 = 100 + np.cumsum(rng.normal(0, 1.2, 35))
    ax.plot(y2, color=LINE, lw=1.2)
    ax.fill_between(np.arange(len(y2)), y2.min() - 2, y2, alpha=0.12, color=LINE)
    ax.set_xticks([])
    ax.set_yticks([])
    _frame(ax, "Run chart")
    _save_thumb(fig, "thumb_run.png")

    # 3 Histogram
    fig, ax = _subplot_rect()
    d = rng.normal(100, 4, 400)
    ax.hist(d, bins=22, color=LINE, edgecolor=BG, alpha=0.85)
    ax.axvline(92, color=UCL, ls="--", lw=1.0)
    ax.axvline(108, color=UCL, ls="--", lw=1.0)
    ax.set_xticks([])
    ax.set_yticks([])
    _frame(ax, "Histogram / Cp,Cpk")
    _save_thumb(fig, "thumb_hist.png")

    # 4 Boxplot
    fig, ax = _subplot_rect()
    data = [rng.normal(0, 1, 80) + i * 0.4 for i in range(4)]
    bp = ax.boxplot(data, patch_artist=True, widths=0.55)
    for p in bp["boxes"]:
        p.set_facecolor("#E8F0FE")
        p.set_edgecolor(LINE)
        p.set_alpha(1.0)
    ax.set_xticks([])
    ax.set_yticks([])
    _frame(ax, "Boxplot")
    _save_thumb(fig, "thumb_box.png")

    # 5 Pareto
    fig, ax = _subplot_rect()
    vals = np.array([42, 28, 15, 9, 6])
    xb = np.arange(len(vals))
    ax.bar(xb, vals, color=LINE, edgecolor=BG, width=0.65)
    ax2 = ax.twinx()
    c = np.cumsum(vals) / vals.sum() * 100
    ax2.plot(xb, c, color=CL, lw=1.3, marker="o", ms=3)
    ax2.set_ylim(0, 105)
    ax.set_xticks([])
    ax.set_yticks([])
    ax2.set_yticks([])
    for sp in ax2.spines.values():
        sp.set_visible(False)
    _frame(ax, "Pareto")
    _save_thumb(fig, "thumb_pareto.png")

    # 6 Heatmap
    fig, ax = _subplot_rect()
    h = rng.uniform(0.3, 1, (8, 12))
    ax.imshow(h, cmap="Blues", aspect="auto")
    ax.set_xticks([])
    ax.set_yticks([])
    _frame(ax, "Spatial heatmap")
    _save_thumb(fig, "thumb_heatmap.png")

    # 7 Scatter
    fig, ax = _subplot_rect()
    x = rng.normal(0, 1, 120)
    y = 0.5 * x + rng.normal(0, 0.6, 120)
    ax.scatter(x, y, c=LINE, s=12, alpha=0.65, edgecolors="none")
    ax.axhline(0, color=GRID, lw=0.7)
    ax.axvline(0, color=GRID, lw=0.7)
    ax.set_xticks([])
    ax.set_yticks([])
    _frame(ax, "Scatter / Quadrant")
    _save_thumb(fig, "thumb_scatter.png")

    # 8 EWMA
    fig, ax = _subplot_rect()
    raw = np.cumsum(rng.normal(0, 0.2, 40)) + 5
    smooth = np.convolve(raw, np.ones(5) / 5, mode="same")
    ax.plot(raw, color=GRID, lw=0.8, alpha=0.7)
    ax.plot(smooth, color=CL, lw=1.3)
    ax.set_xticks([])
    ax.set_yticks([])
    _frame(ax, "EWMA")
    _save_thumb(fig, "thumb_ewma.png")

    # 9 CUSUM
    fig, ax = _subplot_rect()
    cus = np.cumsum(rng.normal(0.05, 0.35, 45))
    ax.plot(cus, color=LINE, lw=1.2)
    ax.axhline(2.5, color=UCL, ls="--", lw=0.9)
    ax.axhline(-2.5, color=UCL, ls="--", lw=0.9)
    ax.set_xticks([])
    ax.set_yticks([])
    _frame(ax, "CUSUM chart")
    _save_thumb(fig, "thumb_cusum.png")

    # 10 Parallel
    fig, ax = _subplot_rect()
    n_lines = 25
    dims = 4
    xs = np.arange(dims)
    for _ in range(n_lines):
        ys = rng.uniform(0, 1, dims)
        ax.plot(xs, ys, color=LINE, alpha=0.28, lw=0.8)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlim(-0.1, dims - 0.9)
    _frame(ax, "Parallel coords (3F)")
    _save_thumb(fig, "thumb_parallel.png")

    print("Wrote:", OUT)


if __name__ == "__main__":
    main()
