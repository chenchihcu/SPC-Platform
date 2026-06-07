from pathlib import Path


def _read(rel_path: str) -> str:
    root = Path(__file__).resolve().parents[1]
    return (root / rel_path).read_text(encoding="utf-8")


def test_temporal_charts_use_pcb_run_order_label():
    files = [
        "app/charts/run_chart.py",
        "app/charts/ewma_chart.py",
        "app/charts/control_chart.py",
        "app/charts/cusum_chart.py",
        "app/charts/run_chart_3f_chart.py",
        "app/charts/ewma_3f_chart.py",
        "app/charts/imr_3f_chart.py",
        "app/charts/cusum_3f_chart.py",
        "app/charts/pattern_recognition_chart.py",
    ]
    for rel in files:
        content = _read(rel)
        assert "樣本序 (PCB Run Order)" in content


def test_cusum_board_summary_uses_board_id_label():
    content = _read("app/charts/cusum_chart.py")
    assert "板號 (Board ID)" in content
