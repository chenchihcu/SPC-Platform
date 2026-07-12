from app.analytics.optimization_suggestions import get_optimization_suggestions
from app.analytics.root_cause_engine import infer_root_cause_hints


def _decline_payload():
    return {
        "run_chart": {
            "data": {
                "values": [120, 118, 117, 116, 114, 112, 110, 108, 106, 104, 102, 100],
            }
        }
    }


def test_root_cause_hint_contains_ipc_and_evidence():
    hints = infer_root_cause_hints(_decline_payload())
    assert hints, "預期至少一條根因提示"
    first = hints[0]
    assert "hint" in first
    assert "rule_id" in first
    assert "severity" in first
    assert "evidence" in first and isinstance(first["evidence"], dict)
    assert "confidence" in first
    assert "priority" in first
    assert "ipc_refs" in first and isinstance(first["ipc_refs"], list)
    assert first["ipc_refs"], "命中規則應有 IPC 引用"


def test_optimization_suggestions_propagates_ipc_and_evidence():
    suggestions = get_optimization_suggestions(_decline_payload())
    root_items = [s for s in suggestions if s.get("source") == "root_cause"]
    assert root_items, "預期有 root_cause 來源建議"
    first = root_items[0]
    assert "ipc_refs" in first and isinstance(first["ipc_refs"], list)
    assert "evidence" in first and isinstance(first["evidence"], dict)


