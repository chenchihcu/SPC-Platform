"""Shared report copy strings (PPTX / Excel / diagnostic summary); single source to avoid drift."""

REPORT_TITLE = "SMT SPI 製程統計分析報告"

# Section trust labels (report_context.section_trust values).
TRUST_DIRECT = "可信：資料直接計算"
TRUST_CHART = "可信：圖表證據"
TRUST_INFERENCE = "需複核：規則推論"
TRUST_MISSING = "未納入：資料缺失"

# Diagnostic evidence_type labels.
EVIDENCE_TYPE_STAT_RULE = "統計計算 / 規則推論"
EVIDENCE_TYPE_STAT_CHART_RULE = "統計計算 / 圖表證據 / 規則推論"

NO_CHART_TEXT = "此異常無可用圖表。"
PRINT_CHECK_ADVICE = "建議確認鋼網、刮刀、錫膏與印刷參數。"
