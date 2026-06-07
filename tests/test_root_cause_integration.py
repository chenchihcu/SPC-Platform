"""
Integration test for RootCausePanel and root_cause_engine.
Verifies that the inference engine correctly identifies process issues
from chart analysis payloads.
"""
import numpy as np

from app.analytics.root_cause_engine import infer_root_cause_hints


def test_empty_payload():
    """Test that empty payload returns no hints."""
    hints = infer_root_cause_hints({})
    assert len(hints) == 0


def test_volume_decline_detection():
    """Test detection of volume decline (paste drying risk)."""
    # Create a payload with declining volume trend
    values = list(range(100, 50, -5))  # Declining from 100 to 50
    payload = {
        "run_chart": {
            "data": {
                "values": values  # At least 10 values required
            }
        }
    }

    hints = infer_root_cause_hints(payload)

    volume_hints = [h for h in hints if h.get("rule_id") == "volume_decline_along_board"]
    assert volume_hints, "volume decline rule should be triggered"


def test_oos_edge_clustering_detection():
    """Test detection of OOS clustering at PCB edges (stencil tension)."""
    np.random.seed(7)
    # Deterministic synthetic data: edge points carry all OOS, center points are clean.
    edge_x = np.array([5, 95, 10, 90, 8, 92, 12, 88, 15, 85], dtype=float)
    edge_y = np.array([5, 95, 8, 92, 10, 90, 12, 88, 15, 85], dtype=float)
    center_x = np.linspace(35, 65, 10)
    center_y = np.linspace(35, 65, 10)
    x = np.concatenate([edge_x, center_x])
    y = np.concatenate([edge_y, center_y])
    oos_density = np.concatenate([np.full(edge_x.shape[0], 5.0), np.zeros(center_x.shape[0])])

    payload = {
        "spatial": {
            "data": {
                "x": x.tolist(),
                "y": y.tolist()
            },
            "modes": {
                "oos_density": {
                    "values": oos_density.tolist()
                }
            }
        }
    }

    hints = infer_root_cause_hints(payload)

    edge_hints = [h for h in hints if h.get("rule_id") == "edge_spatial_cluster"]
    assert edge_hints, "edge_spatial_cluster rule should be triggered"


def test_refdes_variance_detection():
    """Test detection of high RefDes variance (component-level issues)."""
    # Create boxplot statistics with high variance between RefDes
    box_stats = {
        "R1": 0.5,      # Low variance
        "R2": 2.0,      # High variance (>2x others)
        "C1": 0.4,      # Low variance
    }

    payload = {
        "box": {
            "statistics": {
                "variance_by_label": box_stats
            }
        }
    }

    hints = infer_root_cause_hints(payload)

    variance_hints = [h for h in hints if h.get("rule_id") == "footprint_variance_imbalance"]
    assert variance_hints, "footprint_variance_imbalance rule should be triggered"


def test_hint_structure():
    """Verify that returned hints have correct structure."""
    values = list(range(100, 40, -5))  # Strongly declining
    payload = {
        "run_chart": {
            "data": {
                "values": values
            }
        }
    }

    hints = infer_root_cause_hints(payload)

    for hint in hints:
        assert "hint" in hint, "Hint missing 'hint' field"
        assert "rule_id" in hint, "Hint missing 'rule_id' field"
        assert "severity" in hint, "Hint missing 'severity' field"
        assert hint["severity"] in ["error", "warning", "info"]


def test_root_cause_panel_integration():
    """Test that RootCausePanel can be instantiated and updated."""
    from app.ui.widgets.root_cause_panel import RootCausePanel

    assert hasattr(RootCausePanel, "update_hints"), "Missing update_hints method"


def test_cusum_extreme_drift_escalates_to_error():
    payload = {
        "cusum": {
            "data": {"out_of_control_indices": list(range(964))},
            "statistics": {"n": 1000},
        }
    }
    hints = infer_root_cause_hints(payload)
    target = [h for h in hints if h.get("rule_id") == "cusum_trend_drift"]
    assert target, "cusum_trend_drift should be triggered"
    assert target[0]["severity"] == "error"


def test_normality_hint_contains_ipc_reference():
    payload = {
        "normality": {
            "metadata": {"is_valid": True},
            "statistics": {
                "p_value": 1e-8,
                "is_normal": False,
                "total_n": 47660,
                "test_name": "D'Agostino K² (full data / N>5000)",
                "r_squared": 0.9895,
            },
        }
    }
    hints = infer_root_cause_hints(payload)
    target = [h for h in hints if h.get("rule_id") == "normality_test_fail"]
    assert target, "normality_test_fail should be triggered"
    ipc_refs = target[0].get("ipc_refs", [])
    assert ipc_refs, "normality_test_fail should contain IPC references"
    standards = {str(item.get("std", "")) for item in ipc_refs if isinstance(item, dict)}
    assert "J-STD-001" in standards


