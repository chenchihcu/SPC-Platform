---
name: spc-validation-matrix
description: "SPC/SPI Platform 組合式交叉驗證矩陣：圖表類型、多參數、統計與 Exporter 的 headless 掃描。Use when 在本 repo 跑交叉驗證矩陣或 Exporter 輸出掃描。Do NOT use for production release gate（改用 validate-production-release）、單次圖表語意（改用 spc-db-chart-semantics-validator）或 app 啟動檢查（改用 run-spc）。"
metadata:
  version: "2.0.0"
  type: validation
---

# SPC Validation Matrix

組合式交叉驗證矩陣。以 **Headless Programmatic** 方式（不啟動 PySide6 UI）驗證 `compute_analysis_payload` + `chart_registry.resolve_chart_payload` + `build_pptx_report` + `export_diagnostic_summary_xlsx` 完整管線。

## 觸發時機
- 新增或修改 analytics engine 後進行全面健康驗證
- 修改 `chart_router.py` / `chart_registry.py` 後進行全圖表回歸
- 發佈 (Release) 前進行 sanity matrix sweep 避免管線 stall

## 快速驗證指令
```bash
python scripts/validate_matrix.py --fast
```

## 參考指引 (Reference Routing)
- **完整矩陣掃描規則與邊界測試**：請讀取 `references/matrix_sweep_rules.md`
