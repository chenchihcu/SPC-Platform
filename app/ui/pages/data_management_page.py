# -*- coding: utf-8 -*-
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QTabWidget, QSizePolicy,
    QTreeWidget, QTreeWidgetItem, QFrame,
)
import os
import json
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from app.analytics.chart_registry import (
    CHART_CATALOG,
    CHART_ORDER,
    CHART_UI_GROUP_BY_ID,
    CHART_ROOT_CAUSE_STAGE_BY_ID,
    ROOT_CAUSE_FLOW_ORDER,
    get_chart_display_name,
    get_chart_description_sections,
)
from app.analytics.ipc_pillar_library import list_entries
from app.ui.theme.tokens import SPACING_4, SPACING_12, ANALYSIS_BADGE_MIN_W, ANALYSIS_BADGE_MIN_H
from app.ui.widgets.page_templates import page_margins_and_spacing, setup_compact_title_header, style_table
from app.ui.workflow_labels import WORKFLOW_LABEL_REFERENCE

# feature eligibility rules mirror chart_registry availability semantics.
_AT_LEAST_ONE_IDS = {
    "histogram_spec",
    "normality",
    "boxplot",
    "density",
    "anova_parttype",
    "ooc_analysis",
    "shift_detection",
    "drift_detection",
    "outlier_analysis",
    "pattern_recognition",
}
_AT_LEAST_TWO_IDS = {"scatter_spec", "correlation_matrix", "correlation_heatmap"}
_REQ_TO_BADGE = {1: ["①"], 2: ["②"], 3: ["③"]}


def _reference_badges(chart_id: str, required_count: int) -> list[str]:
    if chart_id in _AT_LEAST_ONE_IDS:
        return ["①", "②", "③"]
    if chart_id in _AT_LEAST_TWO_IDS:
        return ["②", "③"]
    return list(_REQ_TO_BADGE.get(required_count, ["①"]))


def _build_chart_ref_rows() -> list[dict[str, str | list[str]]]:
    catalog_by_id = {str(entry.get("id", "")).strip(): entry for entry in CHART_CATALOG}
    rows: list[dict[str, str | list[str]]] = []
    for chart_id in CHART_ORDER:
        entry = catalog_by_id.get(chart_id)
        if not entry:
            continue
        sections = get_chart_description_sections(chart_id)
        category = str(CHART_UI_GROUP_BY_ID.get(chart_id, "未分類"))
        required_count = int(str(entry.get("required_feature_count", 1) or 1))
        required_desc = (
            "至少 1 特徵"
            if chart_id in _AT_LEAST_ONE_IDS
            else ("至少 2 特徵" if chart_id in _AT_LEAST_TWO_IDS else f"需 {required_count} 特徵")
        )
        rows.append(
            {
                "id": chart_id,
                "content": f"{entry.get('display_name_zh', chart_id)}\n圖表分類：{category}",
                "observation": (
                    f"公式：{sections.get('formula_text', '—')}\n"
                    f"資料：{sections.get('data_source_text', '—')}"
                ),
                "risk_decision": str(sections.get("smt_interpretation_text", "—")),
                "governance": f"ID: {chart_id}\n分類：{category}\n特徵條件：{required_desc}",
                "badges": _reference_badges(chart_id, required_count),
            }
        )
    return rows

_MINDMAP_RELATION_BY_GROUP: dict[str, str] = {
    "製程監控": "即時觀察製程是否受控，優先偵測漂移與突發失控。",
    "製程能力": "評估分布是否符合規格與能力門檻，支撐放行與風險判定。",
    "異常根源": "把異常從現象連到位置與缺陷型態，支援優先排查。",
    "變數關係": "檢查特徵耦合與聯合分布，辨識單變量看不到的風險。",
    "比較分析": "跨群組/跨特徵彙整差異，支援工程決策與報告溝通。",
}

_MINDMAP_ANALYSIS_TAG_BY_GROUP: dict[str, str] = {
    "製程監控": "監控",
    "製程能力": "能力",
    "異常根源": "根因",
    "變數關係": "關聯",
    "比較分析": "分群",
}

_ROOT_STAGE_LABEL_BY_ID: dict[str, str] = {
    str(stage.get("stage_id", "")): str(stage.get("label", ""))
    for stage in ROOT_CAUSE_FLOW_ORDER
}


def _mindmap_chart_tag_line(chart_id: str, required_count: int, group: str) -> str:
    feature_badges = " ".join(_reference_badges(chart_id, required_count))
    analysis_tag = _MINDMAP_ANALYSIS_TAG_BY_GROUP.get(group, "一般")
    stage_id = CHART_ROOT_CAUSE_STAGE_BY_ID.get(chart_id, "")
    stage_label = _ROOT_STAGE_LABEL_BY_ID.get(stage_id, "未定義")
    return (
        f"分類標籤：{group}｜特徵標籤：{feature_badges}｜"
        f"分析型態：{analysis_tag}｜決策階段：{stage_label}"
    )


def _build_mindmap_groups() -> list[dict[str, str | list[dict[str, str]]]]:
    catalog_by_id = {str(entry.get("id", "")).strip(): entry for entry in CHART_CATALOG}
    grouped: dict[str, list[dict[str, str]]] = {}
    for chart_id in CHART_ORDER:
        group = str(CHART_UI_GROUP_BY_ID.get(chart_id, "未分類"))
        entry = catalog_by_id.get(chart_id)
        if not entry:
            continue
        required_count = int(str(entry.get("required_feature_count", 1) or 1))
        sections = get_chart_description_sections(chart_id)
        grouped.setdefault(group, []).append(
            {
                "name": get_chart_display_name(chart_id, lang="zh_only"),
                "purpose": str(sections.get("definition_text", "—")),
                "tag_line": _mindmap_chart_tag_line(chart_id, required_count, group),
                "governance": f"治理ID：{chart_id}",
            }
        )

    ordered_groups: list[dict[str, str | list[dict[str, str]]]] = []
    for group in ["製程監控", "製程能力", "異常根源", "變數關係", "比較分析"]:
        ordered_groups.append(
            {
                "category": group,
                "relation": _MINDMAP_RELATION_BY_GROUP.get(group, "—"),
                "charts": grouped.get(group, []),
            }
        )
    return ordered_groups

_BADGE_LEVEL = {
    "①": "single",
    "②": "dual",
    "③": "triple",
}


def _make_badge(symbol: str) -> QLabel:
    lbl = QLabel(symbol)
    lbl.setObjectName("featureBadge")
    level = _BADGE_LEVEL.get(symbol, "unknown")
    lbl.setProperty("level", level)
    
    # Audit Item 111: Explain 'secret' badges via tooltips
    tip_map = {
        "①": "單一特徵分析 (Single Feature Analytics)",
        "②": "雙特徵關聯分析 (Dual Feature Correlation)",
        "③": "三特徵複合分析 (Triple Feature Composite)",
    }
    lbl.setToolTip(tip_map.get(symbol, "未知分析類型"))
    
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setMinimumSize(ANALYSIS_BADGE_MIN_W, ANALYSIS_BADGE_MIN_H)
    lbl.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
    return lbl


def _make_badge_cell(badges: list[str]) -> QWidget:
    w = QWidget()
    h = QHBoxLayout(w)
    h.setContentsMargins(SPACING_4, SPACING_4, SPACING_4, SPACING_4)
    h.setSpacing(SPACING_4)
    h.setAlignment(Qt.AlignmentFlag.AlignCenter)
    for sym in badges:
        h.addWidget(_make_badge(sym))
    return w


def _item(text: str) -> QTableWidgetItem:
    it = QTableWidgetItem(text)
    it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
    return it


class DataManagementPage(QWidget):
    """
    IPC/J-STD 四主軸查詢頁。
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        page_margins_and_spacing(root)

        self.header_lbl = setup_compact_title_header(root, WORKFLOW_LABEL_REFERENCE)

        self._pillars = [
            ("dfm", "DFM"),
            ("printing_spi", "錫膏/SPI"),
            ("bga_fa", "BGA失效與FA"),
            ("jstd_material", "J-STD材料"),
        ]
        self._tables: dict[str, QTableWidget] = {}
        self._detail_views: dict[QTableWidget, dict[str, QLabel]] = {}

        tabs = QTabWidget()
        tabs.setObjectName("ipcPillarTabs")
        tabs.setProperty("class", "secondaryTabs")
        tabs.tabBar().setExpanding(False)
        root.addWidget(tabs, 1)

        for pillar, label in self._pillars:
            tab, table = self._build_master_detail_tab()
            tabs.addTab(tab, label)
            self._tables[pillar] = table
        tabs.addTab(self._build_spc_mindmap_tab(), "SPC心智圖")
        tabs.addTab(self._build_chart_reference_table(), "圖表功能參考")

        self._tabs = tabs
        self._refresh_all_tables()

    def _build_master_detail_tab(self) -> tuple[QWidget, QTableWidget]:
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_12)

        table = self._build_master_table()
        layout.addWidget(table, 5)

        detail_panel = self._build_detail_panel(table)
        detail_panel.setObjectName("dataDetailPanel")
        layout.addWidget(detail_panel, 4)
        return tab, table

    def _build_master_table(self) -> QTableWidget:
        cols = ["主題", "失效模式", "風險", "狀態"]
        table = QTableWidget(0, len(cols))
        table.setObjectName("dataMasterTable")
        table.setHorizontalHeaderLabels(cols)
        style_table(table, role="reference")
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        return table

    def _build_detail_panel(self, table: QTableWidget) -> QWidget:
        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.StyledPanel)
        root = QVBoxLayout(panel)
        root.setContentsMargins(SPACING_12, SPACING_12, SPACING_12, SPACING_12)
        root.setSpacing(SPACING_4)

        title = QLabel("詳細資訊（分類樹）")
        title.setProperty("class", "subtitle")
        root.addWidget(title)

        detail_map: dict[str, QLabel] = {}
        sections = [
            ("A 內容主體", [("主題", "topic"), ("失效模式", "failure_mode"), ("關聯標準", "ipc_refs"), ("關鍵字", "keywords")]),
            ("B 製程觀測", [("關鍵參數", "key_params"), ("偵測訊號", "signals"), ("證據鏈", "fa_evidence")]),
            ("C 風險與決策", [("風險", "risk"), ("控制措施", "actions")]),
            ("D 治理與版本", [("狀態", "status"), ("識別", "entry_id"), ("主軸", "pillar"), ("版本", "revision"), ("更新日", "updated_at")]),
        ]
        for section_name, fields in sections:
            section_label = QLabel(section_name)
            section_label.setProperty("class", "caption")
            root.addWidget(section_label)
            for label_text, key in fields:
                field_label = QLabel(f"{label_text}：—")
                field_label.setWordWrap(True)
                field_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                root.addWidget(field_label)
                detail_map[key] = field_label
            root.addSpacing(SPACING_4)

        root.addStretch(1)
        self._detail_views[table] = detail_map
        table.itemSelectionChanged.connect(lambda t=table: self._sync_detail_panel(t))
        return panel

    def _load_legend_mapping(self) -> dict[str, str]:
        mapping_path = "assets/chart_legends.json"
        if os.path.exists(mapping_path):
            try:
                with open(mapping_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError):
                pass
        return {}

    def _build_chart_reference_table(self) -> QTableWidget:
        cols = ["圖例", "A 內容主體", "B 製程觀測", "C 風險決策", "D 治理版本", "特徵"]
        chart_rows = _build_chart_ref_rows()
        table = QTableWidget(len(chart_rows), len(cols))
        table.setHorizontalHeaderLabels(cols)
        table.setObjectName("chartRefTable")
        style_table(table, role="reference")
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

        mapping = self._load_legend_mapping()

        for row_idx, row in enumerate(chart_rows):
            chart_id = str(row["id"])
            filename = mapping.get(chart_id)
            img_path = f"assets/chart_legends/{filename}" if filename else ""
            img_lbl = QLabel()
            if os.path.exists(img_path):
                pixmap = QPixmap(img_path).scaled(
                    120, 80, 
                    Qt.AspectRatioMode.KeepAspectRatio, 
                    Qt.TransformationMode.SmoothTransformation
                )
                img_lbl.setPixmap(pixmap)
            else:
                img_lbl.setText("無圖例")
                img_lbl.setProperty("class", "caption")
            img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            img_lbl.setContentsMargins(4, 4, 4, 4)
            table.setCellWidget(row_idx, 0, img_lbl)

            text_cells = [
                str(row["content"]),
                str(row["observation"]),
                str(row["risk_decision"]),
                str(row["governance"]),
            ]
            for col, text in enumerate(text_cells):
                item = _item(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
                table.setItem(row_idx, col + 1, item)
            badge_widget = _make_badge_cell(list(row["badges"]))
            table.setCellWidget(row_idx, 5, badge_widget)
        table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        return table

    def _build_spc_mindmap_tab(self) -> QWidget:
        tab = QWidget()
        root = QVBoxLayout(tab)
        root.setContentsMargins(SPACING_12, SPACING_12, SPACING_12, SPACING_12)
        root.setSpacing(SPACING_12)

        intro = QLabel(
            "心智圖圖例建議：◎ 核心決策 ｜ ◉ SPC 類別 ｜ ◍ 單一圖表。"
            "本頁聚焦差異標籤；完整公式與資料來源請看「圖表功能參考」。"
        )
        intro.setWordWrap(True)
        intro.setProperty("class", "caption")
        root.addWidget(intro)

        tree = QTreeWidget()
        tree.setObjectName("spcMindmapTree")
        tree.setColumnCount(5)
        tree.setHeaderLabels(["節點", "A 內容主體", "B 製程觀測", "C 風險決策", "D 治理版本"])
        tree.setAlternatingRowColors(True)
        tree.setWordWrap(True)
        tree.setUniformRowHeights(False)
        tree.setIndentation(20)
        tree.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tree.setRootIsDecorated(True)
        tree.setExpandsOnDoubleClick(True)
        header = tree.header()
        header.setMinimumSectionSize(140)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        tree.setColumnWidth(0, 360)
        tree.setColumnWidth(1, 260)
        tree.setColumnWidth(2, 260)
        tree.setColumnWidth(3, 260)

        root_node = QTreeWidgetItem(
            [
                "◎ SPI 製程圖表決策心智圖",
                "圖表主題與分類語意。",
                "統計觀測方式與訊號來源。",
                "對應風險與製程調整決策。",
                "同一分類樹治理（版本/審核對齊）。",
            ]
        )
        tree.addTopLevelItem(root_node)

        for category in _build_mindmap_groups():
            cat_item = QTreeWidgetItem(
                [
                    f"◉ {category['category']}",
                    "同類圖表具共同決策任務，差異見子節點標籤。",
                    "本層不重複公式與資料來源，避免跨分頁重複。",
                    str(category["relation"]),
                    "沿用 A/B/C/D 語意治理。",
                ]
            )
            root_node.addChild(cat_item)

            charts = category.get("charts", [])
            if isinstance(charts, list):
                for chart in charts:
                    cat_item.addChild(
                        QTreeWidgetItem(
                            [
                                f"◍ {chart.get('name', '')}",
                                str(chart.get("purpose", "—")),
                                str(chart.get("tag_line", "—")),
                                "依差異標籤選擇判讀路徑與後續圖表。",
                                str(chart.get("governance", "納入同一分類樹維護")),
                            ]
                        )
                    )

        tree.expandItem(root_node)
        for i in range(root_node.childCount()):
            tree.expandItem(root_node.child(i))

        root.addWidget(tree, 1)
        return tab

    def _refresh_all_tables(self) -> None:
        for pillar, _ in self._pillars:
            rows = list_entries(pillar=pillar)
            self._populate_table(self._tables[pillar], rows)

    def _populate_table(self, table: QTableWidget, rows: list[dict]) -> None:
        table.clearContents()
        table.setRowCount(len(rows))
        for row_idx, entry in enumerate(rows):
            values = [
                str(entry.get("topic", "")),
                str(entry.get("failure_mode", "")),
                str(entry.get("risk_level", "")),
                str(entry.get("review_status", "")),
            ]
            for col, text in enumerate(values):
                item = _item(text)
                if col in (2, 3):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
                else:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, entry)
                table.setItem(row_idx, col, item)
        table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        if rows:
            table.selectRow(0)
        self._sync_detail_panel(table)

    def _sync_detail_panel(self, table: QTableWidget) -> None:
        detail_map = self._detail_views.get(table)
        if not detail_map:
            return
        current = table.currentItem()
        entry = current.data(Qt.ItemDataRole.UserRole) if current else None
        if not isinstance(entry, dict):
            for key, lbl in detail_map.items():
                lbl.setText(f"{lbl.text().split('：', 1)[0]}：—")
            return

        refs = " / ".join(entry.get("ipc_jstd_refs", []))
        params = "、".join(entry.get("key_parameters", []))
        signals = "、".join(entry.get("detection_signals", []))
        evidence = "、".join(entry.get("fa_evidence", []))
        actions = "、".join(entry.get("control_actions", []))
        keywords = "、".join(entry.get("keywords", []))
        values = {
            "topic": str(entry.get("topic", "—")),
            "failure_mode": str(entry.get("failure_mode", "—")),
            "ipc_refs": refs or "—",
            "keywords": keywords or "—",
            "key_params": params or "—",
            "signals": signals or "—",
            "fa_evidence": evidence or "—",
            "risk": str(entry.get("risk_level", "—")),
            "actions": actions or "—",
            "status": str(entry.get("review_status", "—")),
            "entry_id": str(entry.get("id", "—")),
            "pillar": str(entry.get("pillar", "—")),
            "revision": str(entry.get("revision", "—")),
            "updated_at": str(entry.get("updated_at", "—")),
        }
        for key, value in values.items():
            target_lbl = detail_map.get(key)
            if target_lbl is not None:
                prefix = target_lbl.text().split("：", 1)[0]
                target_lbl.setText(f"{prefix}：{value}")
