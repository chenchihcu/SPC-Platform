# Final Audit Suite（完整性 / 正確性 / 效能最終檢查）

本規格將下列 skill 與 MCP 串成單一最終稽核流程：
- Skills: `spc-code-audit`, `spc-chart-ui`, `smt-spi-self-heal`, `code-audit`, `playwright-interactive`, `playwright`
- MCP: `shell_command`, `filesystem`, `playwright`, `web`, `openai_docs`, `database`, `chart`, `figma`（依觸發條件使用）

## 1. Done State（結案條件）

同時滿足以下條件才可視為最終檢查完成：
1. baseline gate 通過：`ruff` / `mypy app` / `pytest -q`
2. 統計與圖表互動專項回歸通過（含多特徵交叉邏輯）
3. 效能基線測試通過（`tests/test_chart_performance_baseline.py`）
4. `app/` exception policy scan 無未分流之高風險項（broad/silent handler 均有結論）
5. 產出完整稽核工件於 `Outputs/final_audit/<timestamp>/`

## 2. 執行入口

完整模式（建議最終關帳使用）：

```bash
python scripts/run_final_audit_suite.py --repo-root . --profile full
```

快速模式（迭代中）：

```bash
python scripts/run_final_audit_suite.py --repo-root . --profile quick
```

發行前精簡驗證（`ruff`、`mypy app`、`tests/release_validation` 含 **P** 效能回歸）與 JSON 報告：

```bash
python scripts/release_check.py
python scripts/release_check.py --with-release-ext
```

輸出：`Outputs/release/release_report.json`（schema v3：含 v2 之 `performance_*`、可選 `--final-audit-summary`，以及 `git_commit`／`dataset_version`／`golden_scenarios`／`release_validation_plan_modules`／`release_ext_enabled`／`release_ext_paths`）。效能 baseline 記錄：`python scripts/record_performance_baseline.py`。

Golden／`tests/release_validation` 對照表：`docs/specs/release_validation_coverage.md`。`release_check` 與全庫／ext 測試之收斂說明：**`docs/open-questions.md` Watchlist #7**。

輸出：
- `Outputs/final_audit/<timestamp>/report.md`
- `Outputs/final_audit/<timestamp>/summary.json`
- 同批 gate log 檔

## 3. 階段式編排（Skill × MCP）

| 階段 | 目標 | Skill 主責 | MCP 主責 | 通關條件 |
|---|---|---|---|---|
| `baseline` | 專案完整性與可交付性底線 | `code-audit` | `shell_command` + `filesystem` | lint/type/test 通過 |
| `statistical_correctness` | SPC/SPI 統計語意正確性 | `spc-code-audit` | `shell_command` + `filesystem` + `database`(可選) | 統計 pack 通過，無規則漂移 |
| `chart_feature_cross` | 圖表契約與多特徵交叉一致性 | `spc-chart-ui` + `smt-spi-self-heal` | `shell_command` + `filesystem` + `playwright`(可選) | 圖表/互動 pack 通過 |
| `ui_runtime` | 互動與頁面狀態穩定 | `smt-spi-self-heal` + `playwright-interactive` | `playwright` | UI runtime pack 通過 |
| `performance_baseline` | 關鍵運算效能守門 | `spc-chart-ui` + `smt-spi-self-heal` | `shell_command` + `chart`(可選) | performance pack 通過 |
| `qt_policy` | PySide/Qt UI 工程衛生（建議） | `code-audit` | `shell_command` + `filesystem` | advisory：`qt_audit.py` finding 需完成分流 |
| `static_scan` | broad/silent exception 風險控管 | `spc-code-audit` + `code-audit` | `filesystem` | finding 已分流或修復 |

## 4. `run_final_audit_suite.py` 內建測試包

- 統計正確性：
  - `tests/test_spc_engine.py`
  - `tests/test_capability_engine.py`
  - `tests/test_normality_engine.py`
  - `tests/test_statistical_utils.py`
  - `tests/test_anova_engine.py`
  - `tests/test_summary_engine_defect_metrics.py`
  - `tests/test_phase1_chart_consistency.py`
  - `tests/test_phase2_normalization_policy.py`
- 圖表與多特徵交叉：
  - `tests/test_feature_interaction_logic.py`
  - `tests/test_chart_contract_alignment.py`
  - `tests/test_chart_payload_parity_matrix.py`
  - `tests/test_chart_output_matrix.py`
  - `tests/test_chart_registry_acceptance.py`
  - `tests/test_chart_render_registry.py`
  - `tests/test_chart_selector_overrides.py`
  - `tests/test_analysis_orchestrator.py`
- UI runtime：
  - `tests/test_ui_runtime_diagnostics.py`
  - `tests/test_ui_geometry_stability.py`
  - `tests/test_control_panel_layout.py`
  - `tests/test_data_setup_layout_tiers.py`
  - `tests/test_chart_visual_readability.py`
- 效能：
  - `tests/test_chart_performance_baseline.py`

## 5. 異常分流規則

若任一 gate 非 `pass`：
1. 先在同次報告確認 phase 與 failing log。
2. 依 phase 指派對應 skill 進行 root-cause 修復。
3. 修復後重新跑完整 suite（`--profile full`），不可只跑單點測試宣告結案。

`not_available`（工具未配置）不得視為 `pass`，必須在報告中保留阻斷狀態。
