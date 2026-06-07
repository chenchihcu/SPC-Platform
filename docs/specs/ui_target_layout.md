# UI Target Layout (Current)

本文件描述目前 UI 版面目標（2026-05-25），供版面調整時對齊。

## 1. 目標

- 維持工程分析工作流的可預測性與高資訊密度。
- 在不同視窗尺寸與 DPI 下，避免關鍵操作不可見或內容重疊。
- 不改動統計邏輯、資料契約與 signal-slot 行為。

## 2. 主版面目標

主框架維持兩欄：

```text
Left: CollapsibleSidebar (Workflow + Filter + Feature shortcuts + Actions)
Right: Workspace (QTabWidget#workflowTabs pages, tab bar hidden)
```

左欄：
- 6 個可見流程按鈕：資料設定、資料庫、統計圖表、診斷、報告匯出、說明
- 篩選條件（分析範圍、RefDes、PartType、可選 product/time/line）
- 特徵快捷與核心操作（下一步驟、重新分析）
- 高度不足時優先收合分析條件，保留流程導覽與底部主動作可辨識

右欄：
- `QTabWidget#workflowTabs` 保留為內部頁面容器，但 tab bar 隱藏。
- 可見流程由左側流程導覽承載；`量測` 為內部頁，堆疊順序見 `docs/specs/project_architecture.md` §4。

## 3. Data Setup 版面目標

- 採「一頁式垂直區塊」語意（embedded mode）。
- 頁首為單列緊湊工具列：頁名、產品選擇、新增產品、座標/規格/量測狀態同列顯示。
- 不使用整頁垂直捲動作為預設解法。
- 若高度壓力發生，遵循 `docs/specs/table_layout_quantitative_spec.md` 的壓縮順序。

## 4. Chart Analysis 版面目標

- 使用 Dashboard + 分類選擇器，不依賴傳統單一 `QTabWidget`。
- 圖表可見性與相容性由 `chart_registry` 單一來源管理。
- 管理版/工程版切換與特徵切換需維持一致互動語意。
- 工具列、圖表分類選擇器與操作提示必須壓縮為高密度第一屏；提示文字併入圖表脈絡列，不固定佔兩行。

## 5. Report Export 版面目標

- 報告頁提供預覽與匯出入口：
  - 工程導向 PPTX（`engineering`）
- 行為文案需與實際按鈕契約一致，避免舊術語（例如 TXT/PDF-first）殘留。
- 匯出範圍摘要置於頁首；群組的全選/清除與群組標題同列，不另佔工具列。
- 圖表群組卡片需直接置於無框內容區，依內容高度靠上排列；不得用外層大卡片或拉滿高度的群組容器包住空白。

## 6. DPI 與可用性目標

必測縮放：
- 100%
- 125%
- 150%

驗收重點：
- 無關鍵欄位裁切
- 無控件重疊
- 核心按鈕可見且可操作
- 無浪費性大容器、重複狀態列或固定空白提示列；若截圖仍有明顯視覺缺陷，該 UI 任務為不合格。

## 7. 依賴規格

- UI 架構與互動：`docs/specs/ui_design_spec.md`
- 狀態語意：`docs/specs/ui_state_semantics.md`
- 量化版面規範：`docs/specs/table_layout_quantitative_spec.md`
- 規格治理：`docs/specs/spec_maintenance_and_alignment.md`

## 8. 非目標

- 不在本文件定義統計公式或門檻（由 `docs/governance/SPC_RULES.md` 管理）。
- 不在本文件定義資料欄位契約（由 `docs/specs/data_contract.md` 管理）。
