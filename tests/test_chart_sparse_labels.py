from app.charts.base_chart import build_sparse_tick_labels, sparse_tick_positions_labels
from app.charts.boxplot_chart import BoxplotChart
from app.charts.pareto_chart import ParetoChart


def _labels(n: int) -> list[str]:
    return [f"L{i}" for i in range(n)]


def test_boxplot_sparse_labels_keep_all_when_below_threshold():
    labels = _labels(30)
    out = BoxplotChart._build_sparse_labels(labels, threshold=30, step_small=5, step_large=10)
    assert out == labels


def test_boxplot_sparse_labels_show_first_last_and_not_all_blank():
    labels = _labels(31)
    out = BoxplotChart._build_sparse_labels(labels, threshold=30, step_small=5, step_large=10)
    assert len(out) == len(labels)
    assert out[0] == labels[0]
    assert out[-1] == labels[-1]
    assert any(v != "" for v in out)


def test_boxplot_sparse_labels_use_large_step_for_many_groups():
    labels = _labels(80)
    out = BoxplotChart._build_sparse_labels(labels, threshold=30, step_small=5, step_large=10)
    assert out[10] == labels[10]
    assert out[11] == ""
    assert out[-1] == labels[-1]


def test_pareto_sparse_labels_keep_all_when_below_threshold():
    labels = _labels(12)
    out = ParetoChart._build_sparse_labels(labels, threshold=30, step_small=5, step_large=10)
    assert out == labels


def test_pareto_sparse_labels_show_first_last_and_not_all_blank():
    labels = _labels(37)
    out = ParetoChart._build_sparse_labels(labels, threshold=30, step_small=5, step_large=10)
    assert len(out) == len(labels)
    assert out[0] == labels[0]
    assert out[-1] == labels[-1]
    assert any(v != "" for v in out)


def test_base_build_sparse_tick_labels_keeps_first_last():
    labels = _labels(41)
    out = build_sparse_tick_labels(labels, threshold=30, step_small=5, step_large=10)
    assert len(out) == len(labels)
    assert out[0] == labels[0]
    assert out[-1] == labels[-1]
    assert any(v != "" for v in out)


def test_base_sparse_tick_positions_labels_include_last():
    labels = _labels(41)
    positions, out_labels = sparse_tick_positions_labels(labels, max_ticks=20)
    assert positions[0] == 0
    assert positions[-1] == len(labels) - 1
    assert out_labels[0] == labels[0]
    assert out_labels[-1] == labels[-1]
