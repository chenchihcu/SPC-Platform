# 全系統圖表修復交辦包

日期: 2026-03-20  
範圍: 全系統圖表（UI + 報表輸出）  
方法: 純程式靜態稽核（未修改程式）

**規格治理**：標準化顯示、payload 合併、單位與 fallback 之文件化與變更順序，見 **`docs/specs/spec_maintenance_and_alignment.md`** §5、§6（並對照 `docs/governance/AGENTS.md` §7）。

## 1) 全圖表清冊（含責任模組）

### A. 圖表元件層（`app/charts`）
- 核心單特徵圖: `control_chart.py`, `run_chart.py`, `ewma_chart.py`, `cusum_chart.py`, `histogram_chart.py`, `boxplot_chart.py`
- 比較/空間/異常圖: `pareto_chart.py`, `heatmap_chart.py`, `scatter_spec_chart.py`, `quadrant_chart.py`, `density_chart.py`, `bivariate_outlier_chart.py`, `parallel_coord_chart.py`, `pass_fail_chart.py`, `subgroup_chart.py`, `repeated_offender_chart.py`
- 三特徵圖: `imr_3f_chart.py`, `run_chart_3f_chart.py`, `ewma_3f_chart.py`, `cusum_3f_chart.py`, `anomaly_3f_chart.py`, `consistency_3f_chart.py`
- 基礎元件: `base_chart.py`, `mpl_font_config.py`

責任建議: 圖表與視覺邏輯 owner（Charts/UI）

### B. 頁面與分頁封裝層（`app/ui`）
- 主圖表頁（dispatch 中心）: `app/ui/pages/chart_analysis_page.py`
- 分頁封裝: `app/ui/tabs/control_chart_tab.py`, `distribution_capability_tab.py`, `comparison_tab.py`, `normality_tab.py`, `spatial_tab.py`, `pareto_tab.py`, `dual_feature_tab.py`, `triple_feature_tab.py`

責任建議: 前端頁面與狀態同步 owner（UI）

### C. 計算與資料聚合層（`app/viewmodels`, `app/analytics`, `app/utils`, `app/data`）
- 聚合入口: `app/viewmodels/chart_analysis_viewmodel.py` (`compute_analysis_payload`)
- 時序判定: `app/utils/dataframe_utils.py` (`detect_order_col`, `ORDER_COL_PRIORITY`)
- 濾條件與板號範圍: `app/data/session_store.py` (`filter_analysis_df`)
- 核心引擎: `spc_engine.py`, `cusum_engine.py`, `ewma_engine.py`, `run_chart_engine.py`, `capability_engine.py`, `distribution_engine.py`（及其他圖表相關 engine）
- 圖表映射與 payload 切片: `app/analytics/chart_registry.py` (`get_payload_slice`)

責任建議: 分析正確性 owner（Analytics/ViewModel）

### D. 報表輸出路徑（`app/services`）
- 無頭渲染: `app/services/chart_render.py` (`render_chart_to_png_bytes`)
- 報表組裝: `app/services/report_service.py`

責任建議: 報表一致性 owner（Services）

## 2) 統計正確性稽核（CUSUM/EWMA/Run）

### P0-1 量綱一致性風險（高）
觀察:
- `CUSUMEngine` 以 `h_sigma = h * sigma` 判定 OOC（`app/analytics/cusum_engine.py`），理論上判定邏輯可成立。
- 但 `CUSUM 3F` 圖在 board summary 模式顯示 `C+ peak/C-peak` 與 `h` 線時，存在顯示尺度與使用者認知落差風險（`app/charts/cusum_3f_chart.py`）。
- `mu0` 有 fallback（偏離資料平均超過 10 sigma 時退回 data mean），代表現場確實有量綱不匹配情境需防護（`app/analytics/cusum_engine.py`）。

風險定義:
- 若 spec/target 單位與資料欄位不一致，雖引擎有 fallback，仍可能造成圖上解讀混淆（特別是 legend 顯示與摘要峰值）。

### P0-2 時序正確性風險（高）
觀察:
- 單特徵分析使用 `detect_order_col()` 後排序（`chart_analysis_viewmodel.py`）。
- 但 `detect_order_col` 優先順序包含 `BoardNo`，且 `session_store.filter_analysis_df` 在 first/last 板篩選用 `sorted(unique())`，若板號是字串可能發生字典序（`1,10,11,...,2`）問題（`app/utils/dataframe_utils.py`, `app/data/session_store.py`）。

風險定義:
- CUSUM/EWMA/Run 對樣本順序敏感，非時間序會直接扭曲趨勢與 OOC 判定。

### P0-3 UI 與報表 OOC 一致性風險（高）
觀察:
- 報表端走 `chart_render.render_chart_to_png_bytes -> chart_registry.get_payload_slice`。
- UI 端在 `chart_analysis_page` 內有額外 multi-feature 合併路徑（`_resolve_multi_feature_data` / `_resolve_single_feature_data`），部分 chart（如 histogram_spec）自行 merge dist/cap。

風險定義:
- 同一 chart_id 在 UI 與報表若走不同切片/合併規則，可能出現圖像一致但數據標示不一致，或反之。

### P1-1 多特徵 normalize 定義不一致（中）
觀察:
- UI 勾選提示文案是「% of median」（`chart_analysis_page.py`）。
- `run_chart_3f_chart.py` 使用 Z-score。
- `ewma_3f_chart.py` 使用相對控制界限範圍 `(value-cl)/(ucl-lcl)`。
- `cusum_3f_chart.py` 使用 `h` 正規化。

風險定義:
- 同一個「標準化顯示」開關下，不同圖採不同數學定義，造成跨圖對照誤解。

### P1-2 Payload 切片規則分散（中）
觀察:
- `chart_registry.get_payload_slice` 與 `chart_analysis_page` 都有資料拼接邏輯（尤其 `histogram_spec`, `boxplot`, 多特徵）。

風險定義:
- 同一資料來源在不同路徑被二次拼裝，容易發生欄位遺漏、覆蓋不一致。

### P2-1 視覺 downsampling 透明度不足（中）
觀察:
- `run_chart_engine.py` 大資料會均勻抽樣（`RUN_CHART_MAX_POINTS`）。

風險定義:
- 圖上可能遺漏尖峰；若未標示抽樣規則，使用者誤判風險增加。

## 3) 可直接派工的修正單（Ticket Pack）

### Ticket P0-1: CUSUM 單位一致性與顯示對齊
- 目標: 確保 CUSUM 值、`h`/`h_sigma`、legend 文案完全同尺度、同語意。
- 變更範圍:
  - `app/analytics/cusum_engine.py`
  - `app/charts/cusum_chart.py`
  - `app/charts/cusum_3f_chart.py`
- 完成條件:
  - 圖上每個控制線標籤明確標示單位（sigma 或原始單位）。
  - board summary 與 detail 模式 OOC 判定一致。
  - 當觸發 mu0 fallback 時，圖上/metadata 有可見提示（非 silent）。

### Ticket P0-2: 時序排序統一與板號排序修正
- 目標: CUSUM/EWMA/Run 一律以時間序運算，不受字串板號排序干擾。
- 變更範圍:
  - `app/utils/dataframe_utils.py`
  - `app/viewmodels/chart_analysis_viewmodel.py`
  - `app/data/session_store.py`
- 完成條件:
  - `BoardNo` 只用於群組/邊界，不作為首選時間排序欄位（除非無時間欄）。
  - `first/last board` 以自然序或明確規則處理，避免字典序誤判。

### Ticket P0-3: UI/報表切片一致化
- 目標: 同 chart_id 在 UI 與報表採同一資料切片邏輯。
- 變更範圍:
  - `app/analytics/chart_registry.py`
  - `app/ui/pages/chart_analysis_page.py`
  - `app/services/chart_render.py`
- 完成條件:
  - 建立單一切片入口（UI/報表共用）。
  - `histogram_spec`、`boxplot`、多特徵 payload 合併規則單點定義。

### Ticket P1-1: 標準化策略統一
- 目標: `標準化顯示` 在所有 3F 圖使用同一策略或明確分策略命名。
- 變更範圍:
  - `app/ui/pages/chart_analysis_page.py`
  - `app/charts/run_chart_3f_chart.py`
  - `app/charts/ewma_3f_chart.py`
  - `app/charts/cusum_3f_chart.py`
- 完成條件:
  - UI 文案與實作一致（例如統一為 Z-score；或拆分為多種開關）。
  - 圖標題/tooltip 清楚揭露公式。

### Ticket P1-2: Payload 合併職責去重
- 目標: 移除重複 merge 路徑，避免 UI 與 registry 各自維護。
- 變更範圍:
  - `app/analytics/chart_registry.py`
  - `app/ui/pages/chart_analysis_page.py`
- 完成條件:
  - 任何 chart payload 合併規則有單一來源。
  - 既有 public interface 不破壞（遵守 AGENTS 規範）。

### Ticket P2-1: Downsampling 風險揭露
- 目標: 大資料抽樣時，圖上清楚揭露「已抽樣」與抽樣比率。
- 變更範圍:
  - `app/analytics/run_chart_engine.py`
  - `app/charts/run_chart.py`
  - `app/charts/run_chart_3f_chart.py`
- 完成條件:
  - metadata 提供原始點數、顯示點數、抽樣步距。
  - UI/報表都可看到抽樣狀態。

## 4) 分階段修復路線（含可驗證交付）

### Phase 1（P0）統計正確性
- 交付:
  - CUSUM/EWMA/Run 的排序與 OOC 一致性修正
  - UI 與報表共用切片
- 驗收:
  - 同資料集、同參數下，UI 與報表 OOC 結果一致。
  - 時序調換實驗能穩定重現「排序改變 -> 結果改變」。

### Phase 2（P1）跨圖一致性
- 交付:
  - 多特徵標準化策略統一
  - payload 合併職責單點化
- 驗收:
  - 勾選「標準化顯示」時，所有 3F 圖公式可解釋且文案一致。

### Phase 3（P2）可讀性與風險揭露
- 交付:
  - downsampling 透明化
  - CUSUM fallback/重置規則可見化
- 驗收:
  - 使用者可從圖例/tooltip 判斷圖是否抽樣、是否 fallback。

## 4.1 階段完成狀態（實作更新）

- Phase 1（已完成）
  - 時序排序優先改為時間欄位，板號排序改為 natural sort。
  - 單特徵切片改為共用函式，降低 UI/報表分岔。
  - CUSUM 圖例明確標示 `hσ`，並顯示 `mu0 fallback`。
- Phase 2（已完成）
  - Run/EWMA/CUSUM 3F 的標準化策略統一為 Z-score（跨圖一致）。
  - 多特徵切片新增 `get_multi_feature_payload_slice()` 作為單一來源，`chart_analysis_page` 改為呼叫共用函式。
- Phase 3（已完成）
  - Run chart engine 新增 downsampling metadata（原始點數、顯示點數、步距、是否抽樣）。
  - Run 圖（單特徵與 3F）新增抽樣提示註記，降低誤讀風險。

## 5) 測試與驗收建議（實作階段必做）

- 單元測試:
  - 排序欄位選擇與 first/last 板邏輯（含 `Board_2`, `Board_10` 案例）
  - CUSUM `h/h_sigma` 判定與 board boundary reset
  - payload slicing（UI 與報表）一致性
- 回歸測試:
  - 單特徵（Height/Area/Volume）切換警示數值同步更新
  - 報表輸出與 UI 截圖結果的關鍵統計值比對
- 規範約束:
  - 不改公開介面（Engine/ViewModel/ReportService）
  - 不改 SPC 常數與公式定義（依 `docs/governance/SPC_RULES.md`）

## 6) 規則落地對照索引（AGENTS + Cursor Rules）

- `docs/governance/AGENTS.md` 新增「Chart Statistical Integrity Rules」：
  - 時間優先排序（Run/EWMA/CUSUM）
  - Board 決策自然排序
  - 單一來源切片/合併
  - 標準化語意一致
  - 控制界線語意顯示（`hσ`）
  - fallback 可見化
  - downsampling 透明化
  - 例外流程（TODO + 測試 + owner 核准）

- `.cursor/rules/spc-chart-ordering-and-slicing.mdc`：
  - 約束排序、首末件、切片與 UI/報表共用邏輯

- `.cursor/rules/spc-chart-normalization-and-semantics.mdc`：
  - 約束標準化公式一致、圖例語意、fallback 顯示

- `.cursor/rules/spc-chart-sampling-and-verification.mdc`：
  - 約束抽樣 metadata、使用者可見提示、回歸測試門檻
