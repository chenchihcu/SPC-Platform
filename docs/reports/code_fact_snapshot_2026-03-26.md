# 程式碼事實快照（2026-03-26）

本文件以目前主分支程式碼為準，整理「匯入 → 分析 → 圖表 → 報告」相關可驗證行為，作為文件對齊依據。

## A. 重新整理分析按鈕 loading 狀態

- 觸發點：`app/ui/main_window.py` `refresh_analysis()`
  - 將 `refresh_btn` 設為 disabled
  - 按鈕文字改為 `計算中…`
  - 設定 `state=loading`
- 還原點：`app/ui/main_window.py` `_restore_refresh_button()`
  - 恢復 enabled
  - 文字改回 `重新整理分析`
  - 清空 `state`
- 早退路徑（未選特徵、規格解析失敗、檢核失敗）均呼叫 `_restore_refresh_button()`。

## B. 分析前規格檢核（產品規格單一來源）

- `app/ui/main_window.py` `_run_refresh_analysis()`：
  - 若有 `product_name`，先呼叫 `can_run_analysis(product_name)`
  - 通過後呼叫 `resolve_workorder_spec(product_name)`
  - 成功時寫回 `SessionStore.workorder_spec`
- `app/services/spec_resolver.py`：
  - `can_run_analysis()`：產品未選、規格不存在、階梯鋼板未指定精密元件時拒絕分析
  - `resolve_workorder_spec()`：解析 `volume/area/height` 規格（字串格式）

## C. Volume/Area 與 Height 行為

- `app/data/product_spec_registry.py` 常數：
  - Volume 預設：Target=100, LSL=70, USL=150
  - Area 預設：Target=100, LSL=70, USL=150
- `app/services/spec_resolver.py`：
  - Volume/Area 由主檔 default 欄位（未填則回落預設常數）
  - 普通鋼板 Height 由 `build_height_spec(thickness_main)` 解析
  - 階梯鋼板 Phase 1 彙總仍以 main 厚度高度規格為代表
  - `resolve_height_spec_by_refdes()` 已提供 per-RefDes 規格解析能力

## D. 座標更新與階梯指派重設

- `app/ui/main_window.py` `on_load_finished()`：
  - 若座標路徑變動，呼叫 `clear_by_product(product_name)`
  - 顯示「座標已更新，請在資料設定頁重新指定階梯鋼板精密元件。」
  - 之後重新解析並同步 `workorder_spec`

## E. Worker 關閉生命週期

- `app/ui/main_window.py` `closeEvent()`：
  - 若 `_analysis_worker` 或 `worker` 仍在跑，先 `cancel()` 再 `wait(...)`
  - 完成後呼叫 `super().closeEvent(event)`

## F. 可直接觀察到的文件失配點

- 多份文件仍引用不存在路徑：
  - `.cursor/rules/docs/reference/platform_overview.md`
  - `.cursor/plans/docs/reference/platform_overview.md`
- 實際存在的索引檔為：
  - `.cursor/rules/README.md`
  - `.cursor/plans/README.md`
