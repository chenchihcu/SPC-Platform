import builtins
import logging

from app.services.report_actions import collect_pptx_actions


def test_collect_pptx_actions_prefers_rule_specific_failure_mode_actions() -> None:
    drying_actions = collect_pptx_actions({}, rule_id="volume_decline_along_board", limit=3)
    cpk_actions = collect_pptx_actions({}, rule_id="cpk_below_threshold", limit=3)

    assert "縮短開罐後使用時間" in drying_actions
    assert "確認設備參數穩定性" in cpk_actions
    assert "縮短開罐後使用時間" not in cpk_actions


def test_collect_pptx_actions_logs_when_failure_mode_library_missing(
    monkeypatch, caplog
) -> None:
    real_import = builtins.__import__

    def _patched_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "app.analytics.failure_mode_library":
            raise ImportError("forced-missing-for-test")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _patched_import)
    caplog.set_level(logging.WARNING, logger="app.services.report_actions")

    actions = collect_pptx_actions({}, rule_id="cpk_below_threshold", limit=3)

    assert isinstance(actions, list)
    assert any(
        "failure_mode_library unavailable; using fallback suggestions"
        in rec.message
        for rec in caplog.records
    )
