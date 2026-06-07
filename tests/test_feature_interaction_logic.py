import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandas as pd
from PySide6.QtWidgets import QApplication, QCheckBox

from app.data.session_store import SessionStore
from app.ui.pages.chart_analysis_page import ChartAnalysisPage
from app.ui.pages.component_select_page import ComponentSelectPage
from app.viewmodels.chart_analysis_viewmodel import compute_analysis_payload


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_toggle_feature_keeps_at_least_one_selected(qapp):
    store = SessionStore()
    store.selected_features = ["Volume"]
    page = ComponentSelectPage()

    page.toggle_feature("Volume")
    selected = page.get_selected_features()

    assert selected, "至少要保留一個特徵，不能全部取消"
    assert len(selected) == 1


def test_toggle_feature_allows_multi_select_up_to_three(qapp):
    store = SessionStore()
    store.selected_features = ["Volume"]
    page = ComponentSelectPage()

    page.toggle_feature("Area")
    page.toggle_feature("Height")
    selected = page.get_selected_features()

    assert set(selected) == {"Volume", "Area", "Height"}
    assert len(selected) == 3


def _build_df(rows: int = 24) -> pd.DataFrame:
    data = {
        "Volume": [100 + (i % 5) for i in range(rows)],
        "Area": [200 + ((i * 2) % 7) for i in range(rows)],
        "Height": [50 + ((i * 3) % 6) for i in range(rows)],
        "PartType": ["R0402" if i % 2 == 0 else "C0603" for i in range(rows)],
        "RefDes": [f"R{i % 8 + 1}" for i in range(rows)],
        "BoardNo": [f"B{i // 6 + 1}" for i in range(rows)],
        "PanelId": [f"P{i // 6 + 1}" for i in range(rows)],
        "X": [float(i % 6) for i in range(rows)],
        "Y": [float(i // 6) for i in range(rows)],
    }
    return pd.DataFrame(data)


def _spec() -> dict:
    return {
        "volume": {"usl": 130, "lsl": 70, "target": 100},
        "area": {"usl": 260, "lsl": 150, "target": 200},
        "height": {"usl": 70, "lsl": 35, "target": 50},
    }


def test_chart_analysis_page_imr_not_fallback_when_display_features_is_three(qapp):
    store = SessionStore()
    df = _build_df()
    store.meas_df = df
    store.meas_meta = {"is_valid": True}
    store.coord_meta = {"is_valid": True}

    payload, err = compute_analysis_payload(
        df,
        ["Volume"],
        usl=130,
        lsl=70,
        target=100,
        workorder_spec=_spec(),
    )
    assert err is None
    assert payload is not None

    # Provide context so selector availability isn't blocked by missing "batch" / "part_type".
    payload["_ctx_batch"] = "Board_1"
    payload["_ctx_part_type"] = "R0402"

    page = ChartAnalysisPage()

    # Avoid background threads and hint calculations during selector tests.
    page._update_details_hints = lambda _payload: None
    page.root_cause_panel.update_hints = lambda _payload: None

    class DummyWidget:
        def update_data(self, _data):
            return

    for cid in list(page._chart_widgets.keys()):
        page._chart_widgets[cid] = DummyWidget()

    page.update_all_charts(payload)

    # Initial state: single display feature -> imr should be enabled and checked by default.
    assert "imr" in page._chart_id_to_checkbox
    assert page._chart_id_to_checkbox["imr"].isEnabled() is True
    # Make the test deterministic even if selector restored a prior chart choice.
    page._chart_id_to_checkbox["imr"].setChecked(True)
    assert page._chart_id_to_checkbox["imr"].isChecked() is True

    # Toggle to 3 display features via shortcuts (without re-running analysis).
    page._on_feature_shortcut_clicked("area")
    page._on_feature_shortcut_clicked("height")

    # UI should disable single-feature imr and switch intent to imr_3f.
    assert page._chart_id_to_checkbox["imr"].isEnabled() is False
    assert page._chart_id_to_checkbox["imr"].isChecked() is False
    assert page._chart_id_to_checkbox["imr_3f"].isEnabled() is True
    page._chart_id_to_checkbox["imr_3f"].setChecked(True)
    assert page._chart_id_to_checkbox["imr_3f"].isChecked() is True

    # Data resolution must also not silently fall back to features[0] for imr.
    multi_features = page._display_features
    imr_data = page._resolve_multi_feature_data("imr", multi_features)
    assert imr_data.get("metadata", {}).get("is_valid") is False
    assert imr_data.get("metadata", {}).get("incompatible") is True

    imr_3f_data = page._resolve_multi_feature_data("imr_3f", multi_features)
    assert imr_3f_data.get("metadata", {}).get("is_valid") is True
    assert set(imr_3f_data.get("_features", [])) == {"Volume", "Area", "Height"}


def test_histogram_spec_supports_multi_feature_when_display_features_is_three(qapp):
    """
    histogram_spec payload_key is a composite ('dist', 'cap').
    ChartAnalysisPage must not silently fall back to only features[0]
    when display_features becomes 3.
    """
    store = SessionStore()
    df = _build_df()
    store.meas_df = df
    store.meas_meta = {"is_valid": True}
    store.coord_meta = {"is_valid": True}

    payload, err = compute_analysis_payload(
        df,
        ["Volume"],
        usl=130,
        lsl=70,
        target=100,
        workorder_spec=_spec(),
    )
    assert err is None
    assert payload is not None
    payload["_ctx_batch"] = "Board_1"
    payload["_ctx_part_type"] = "R0402"

    page = ChartAnalysisPage()
    page._update_details_hints = lambda _payload: None
    page.root_cause_panel.update_hints = lambda _payload: None

    class DummyWidget:
        def update_data(self, _data):
            return

    for cid in list(page._chart_widgets.keys()):
        page._chart_widgets[cid] = DummyWidget()

    page.update_all_charts(payload)

    # Toggle to 3 display features without re-running analysis.
    page._on_feature_shortcut_clicked("area")
    page._on_feature_shortcut_clicked("height")

    multi_features = page._display_features
    assert set(multi_features) == {"Volume", "Area", "Height"}

    hist_data = page._resolve_multi_feature_data("histogram_spec", multi_features)
    assert hist_data.get("_multi_feature") is True
    assert set(hist_data.get("_features", [])) == {"Volume", "Area", "Height"}


def test_chart_analysis_page_records_autoswitch_reason_when_feature_count_changes(qapp):
    store = SessionStore()
    df = _build_df()
    store.meas_df = df
    store.meas_meta = {"is_valid": True}
    store.coord_meta = {"is_valid": True}

    payload, err = compute_analysis_payload(
        df,
        ["Volume"],
        usl=130,
        lsl=70,
        target=100,
        workorder_spec=_spec(),
    )
    assert err is None
    assert payload is not None
    payload["_ctx_batch"] = "Board_1"
    payload["_ctx_part_type"] = "R0402"

    page = ChartAnalysisPage()
    page._update_details_hints = lambda _payload: None
    page.root_cause_panel.update_hints = lambda _payload: None

    class DummyWidget:
        def update_data(self, _data):
            return

    for cid in list(page._chart_widgets.keys()):
        page._chart_widgets[cid] = DummyWidget()

    page.update_all_charts(payload)
    page._chart_id_to_checkbox["imr"].setChecked(True)
    page._on_feature_shortcut_clicked("area")
    page._on_feature_shortcut_clicked("height")

    state = page.get_ui_state_snapshot()
    assert state["feature_tab_count"] == 3
    assert state["selected_chart_ids"]
    assert "imr" not in state["selected_chart_ids"]
    assert "已依顯示模式自動改選" in state["autoswitch_reason"]
    assert "目前為三特徵" in state["autoswitch_reason"]


def test_chart_analysis_page_autoswitch_hint_cleared_when_selector_rebuilds_without_new_switch(qapp):
    """Stale autoswitch text must not survive _refresh_chart_selector when no new reason applies."""
    store = SessionStore()
    df = _build_df()
    store.meas_df = df
    store.meas_meta = {"is_valid": True}
    store.coord_meta = {"is_valid": True}

    payload, err = compute_analysis_payload(
        df,
        ["Volume"],
        usl=130,
        lsl=70,
        target=100,
        workorder_spec=_spec(),
    )
    assert err is None
    assert payload is not None
    payload["_ctx_batch"] = "Board_1"
    payload["_ctx_part_type"] = "R0402"

    page = ChartAnalysisPage()
    page._update_details_hints = lambda _payload: None
    page.root_cause_panel.update_hints = lambda _payload: None

    class DummyWidget:
        def update_data(self, _data):
            return

    for cid in list(page._chart_widgets.keys()):
        page._chart_widgets[cid] = DummyWidget()

    page.update_all_charts(payload)
    page._chart_id_to_checkbox["imr"].setChecked(True)
    page._on_feature_shortcut_clicked("area")
    page._on_feature_shortcut_clicked("height")
    assert "已依顯示模式自動改選" in page.get_ui_state_snapshot()["autoswitch_reason"]

    page._set_autoswitch_reason("STALE_HINT_SHOULD_NOT_PERSIST")
    page._refresh_chart_selector(["Volume", "Area", "Height"])
    assert page.get_ui_state_snapshot()["autoswitch_reason"] == ""


def test_chart_analysis_page_feature_tabs_rebuild_selector_context(qapp):
    store = SessionStore()
    df = _build_df()
    store.meas_df = df
    store.meas_meta = {"is_valid": True}
    store.coord_meta = {"is_valid": True}

    payload, err = compute_analysis_payload(
        df,
        ["Volume"],
        usl=130,
        lsl=70,
        target=100,
        workorder_spec=_spec(),
    )
    assert err is None
    assert payload is not None
    payload["_ctx_batch"] = "Board_1"
    payload["_ctx_part_type"] = "R0402"

    page = ChartAnalysisPage()
    page._update_details_hints = lambda _payload: None
    page.root_cause_panel.update_hints = lambda _payload: None

    class DummyWidget:
        def update_data(self, _data):
            return

    for cid in list(page._chart_widgets.keys()):
        page._chart_widgets[cid] = DummyWidget()

    page.update_all_charts(payload)
    page._on_feature_shortcut_clicked("area")
    page._on_feature_shortcut_clicked("height")
    assert page._chart_id_to_checkbox["imr"].isEnabled() is False

    page._on_feature_tab_clicked(1)
    state_1f = page.get_ui_state_snapshot()
    assert state_1f["feature_tab_count"] == 1
    assert page._chart_id_to_checkbox["imr"].isEnabled() is True

    page._on_feature_tab_clicked(3)
    state_3f = page.get_ui_state_snapshot()
    assert state_3f["feature_tab_count"] == 3
    assert page._chart_id_to_checkbox["imr"].isEnabled() is False


def test_manual_chart_selection_clears_autoswitch_reason(qapp):
    store = SessionStore()
    df = _build_df()
    store.meas_df = df
    store.meas_meta = {"is_valid": True}
    store.coord_meta = {"is_valid": True}

    payload, err = compute_analysis_payload(
        df,
        ["Volume"],
        usl=130,
        lsl=70,
        target=100,
        workorder_spec=_spec(),
    )
    assert err is None
    assert payload is not None
    payload["_ctx_batch"] = "Board_1"
    payload["_ctx_part_type"] = "R0402"

    page = ChartAnalysisPage()
    page._update_details_hints = lambda _payload: None
    page.root_cause_panel.update_hints = lambda _payload: None

    class DummyWidget:
        def update_data(self, _data):
            return

    for cid in list(page._chart_widgets.keys()):
        page._chart_widgets[cid] = DummyWidget()

    page.update_all_charts(payload)
    page._chart_id_to_checkbox["imr"].setChecked(True)
    page._on_feature_shortcut_clicked("area")
    page._on_feature_shortcut_clicked("height")
    assert "已依顯示模式自動改選" in page.get_ui_state_snapshot()["autoswitch_reason"]

    page._chart_id_to_checkbox["run_chart_3f"].setChecked(True)
    assert page.get_ui_state_snapshot()["autoswitch_reason"] == ""


def test_chart_analysis_render_status_mapping(qapp):
    page = ChartAnalysisPage()
    page._chart_id_to_checkbox["imr"] = QCheckBox()
    page._chart_id_to_checkbox["imr"].setEnabled(False)
    status, reason = page._classify_render_status(
        "imr",
        {"metadata": {"is_valid": False}},
        ["Volume", "Area"],
    )
    assert status == "Incompatible"
    assert reason

    page._chart_id_to_checkbox["histogram_spec"] = QCheckBox()
    page._chart_id_to_checkbox["histogram_spec"].setEnabled(True)
    status_nodata, _ = page._classify_render_status(
        "histogram_spec",
        {"metadata": {"is_valid": False, "error": "資料不足，無法繪圖"}},
        ["Volume"],
    )
    assert status_nodata == "NoData"

    status_error, _ = page._classify_render_status(
        "histogram_spec",
        {"metadata": {"is_valid": False, "error": "renderer crashed unexpectedly"}},
        ["Volume"],
    )
    assert status_error == "Error"


def test_chart_context_strip_exposes_feature_mode_and_filters(qapp):
    page = ChartAnalysisPage()
    page._display_features = ["Volume", "Area", "Height"]
    page._selected_chart_ids = ["histogram_spec", "run_chart_3f"]
    page._active_feature_tab_count = 2
    page._normalize_multi = True
    page._last_payload = {
        "_ctx_batch": "B-01",
        "_ctx_part_type": "R0402",
        "_ctx_refdes": "",
    }

    page._sync_ui_state()

    text = page._chart_context_strip.text()
    assert "Volume / Area" in text
    assert "顯示模式: 雙特徵" in text
    assert "已選圖表: 2 張" in text
    assert "多特徵標準化: 開啟" in text
    assert "批次: B-01" in text
    assert "PartType: R0402" in text


def test_chart_context_strip_marks_normalization_as_pending_from_single_feature_mode(qapp):
    page = ChartAnalysisPage()
    page._display_features = ["Volume", "Area", "Height"]
    page._selected_chart_ids = ["imr"]
    page._active_feature_tab_count = 1
    page._normalize_multi = True

    page._sync_ui_state()

    text = page._chart_context_strip.text()
    assert "顯示模式: 單特徵" in text
    assert "多特徵標準化: 待雙/三特徵模式" in text
