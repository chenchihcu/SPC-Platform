# 分頁資料結構盤點與 AI 三方模擬討論（v1.0 定版）

## 1) 盤點基礎（程式與契約）
- UI 頁面來源：`app/ui/pages/data_management_page.py`
- 資料載入/驗證來源：`app/analytics/ipc_pillar_library.py`
- 主資料來源：`data/ipc_jstd_pillar_seed.json`
- 契約來源：`docs/specs/data_contract.md`
- 分頁測試依據：`tests/test_data_management_page_tabs.py`

## 2) 分頁盤點（DataManagementPage）
- `DFM`
- `錫膏與印刷/SPI`
- `BGA失效與FA`
- `J-STD材料管理`
- `SPC 圖表關聯心智圖`
- `圖表功能參考（舊版）`

## 3) 欄位盤點與映射（結構對齊）

### 3.1 UI 表格欄位（四主軸分頁）
- `主題`
- `失效模式`
- `關聯標準`
- `關鍵參數`
- `偵測訊號`
- `風險`
- `狀態`

### 3.2 對應 seed / loader 欄位
- `主題` → `topic`
- `失效模式` → `failure_mode`
- `關聯標準` → `ipc_jstd_refs`
- `關鍵參數` → `key_parameters`
- `偵測訊號` → `detection_signals`
- `風險` → `risk_level`
- `狀態` → `review_status`

### 3.3 REQUIRED_FIELDS（存在但未直接顯示於 UI 欄）
- `id`
- `pillar`
- `fa_evidence`
- `control_actions`
- `keywords`
- `revision`
- `updated_at`

## 4) 分類樹（v1.0 定版：2 層）

### A. 內容主體（What）
- 主題與失效現象：`topic`, `failure_mode`
- 關聯規範：`ipc_jstd_refs`
- 檢索語意：`keywords`（依你的決策歸入內容層）

### B. 製程觀測（How to Observe）
- 關鍵參數：`key_parameters`
- 偵測訊號：`detection_signals`
- 證據鏈：`fa_evidence`

### C. 風險與決策（How to Decide）
- 風險層級：`risk_level`
- 控制措施：`control_actions`

### D. 治理與版本（How to Govern）
- 審核狀態：`review_status`
- 版本追溯：`id`, `revision`, `updated_at`, `pillar`

## 5) AI 模擬三方討論

### 共識項目
- 分類主軸應由「畫面欄位」擴充為「資料全生命週期（定義/觀測/決策/治理）」。
- `fa_evidence` 與 `control_actions` 不應缺席，需成為正式分類節點。
- UI 目前七欄可維持精簡展示，但分類文件要保留隱含欄位映射。
- `SPC 圖表關聯心智圖` 與 `圖表功能參考（舊版）` 屬於知識導覽層，應與四主軸資料表分層管理。

### 分歧項目（已收斂）
- 分類深度：定版採 2 層。
- `keywords` 歸屬：定版歸於內容層。
- 治理欄位顯示策略：`revision`、`updated_at` 不放主表。
- `SPC 圖表關聯心智圖`：併入同一分類樹執行。

### 建議分類修訂（定版採納）
- 採 4 主域（A/B/C/D）並固定為 2 層結構。
- 主表維持既有 7 欄，治理與版本欄位維持非主表展示。
- 固定維護「UI名稱 ↔ 內部欄位 ↔ 契約欄位」三向映射。
- `SPC 圖表關聯心智圖` 併入同一分類樹脈絡，作為分類應用層節點。

### 你的最終決策（已套用）
- 決策 1：分類樹深度採 2 層。
- 決策 2：`keywords` 歸屬內容層。
- 決策 3：治理層欄位不進主表顯示。
- 決策 4：`SPC 圖表關聯心智圖` 併入同一分類樹執行。

## 6) 執行說明（v1.0）
- 本版即為可執行分類基準，後續新增欄位需先標註歸屬主域（A/B/C/D）。
- UI 主表維持 7 欄不擴充；治理欄位以非主表資訊方式呈現。
- `SPC 圖表關聯心智圖` 的節點命名與關聯敘述，應回指 A/B/C/D 主域語意。

## 7) v1.0 對應表（分頁 → 分類主域 → 欄位）

### 7.1 四主軸資料分頁（共用主表）
- 分頁：`DFM`
  - 分類主域 A 內容主體：`topic`, `failure_mode`, `ipc_jstd_refs`, `keywords`
  - 分類主域 B 製程觀測：`key_parameters`, `detection_signals`, `fa_evidence`
  - 分類主域 C 風險與決策：`risk_level`, `control_actions`
  - 分類主域 D 治理與版本：`review_status`, `id`, `revision`, `updated_at`, `pillar`
- 分頁：`錫膏與印刷/SPI`
  - 分類主域 A 內容主體：`topic`, `failure_mode`, `ipc_jstd_refs`, `keywords`
  - 分類主域 B 製程觀測：`key_parameters`, `detection_signals`, `fa_evidence`
  - 分類主域 C 風險與決策：`risk_level`, `control_actions`
  - 分類主域 D 治理與版本：`review_status`, `id`, `revision`, `updated_at`, `pillar`
- 分頁：`BGA失效與FA`
  - 分類主域 A 內容主體：`topic`, `failure_mode`, `ipc_jstd_refs`, `keywords`
  - 分類主域 B 製程觀測：`key_parameters`, `detection_signals`, `fa_evidence`
  - 分類主域 C 風險與決策：`risk_level`, `control_actions`
  - 分類主域 D 治理與版本：`review_status`, `id`, `revision`, `updated_at`, `pillar`
- 分頁：`J-STD材料管理`
  - 分類主域 A 內容主體：`topic`, `failure_mode`, `ipc_jstd_refs`, `keywords`
  - 分類主域 B 製程觀測：`key_parameters`, `detection_signals`, `fa_evidence`
  - 分類主域 C 風險與決策：`risk_level`, `control_actions`
  - 分類主域 D 治理與版本：`review_status`, `id`, `revision`, `updated_at`, `pillar`

### 7.2 分頁顯示欄位（UI 7 欄）對應主域
- `主題` → A 內容主體（`topic`）
- `失效模式` → A 內容主體（`failure_mode`）
- `關聯標準` → A 內容主體（`ipc_jstd_refs`）
- `關鍵參數` → B 製程觀測（`key_parameters`）
- `偵測訊號` → B 製程觀測（`detection_signals`）
- `風險` → C 風險與決策（`risk_level`）
- `狀態` → D 治理與版本（`review_status`）

### 7.3 非主表欄位呈現策略（依你的定版決策）
- 不進主表：`revision`, `updated_at`
- 建議呈現位置：
  - 列點詳情抽屜（row detail）
  - 滑鼠提示（tooltip）
  - 匯出報告 metadata 區塊

### 7.4 知識分頁併入同一分類樹（執行規則）
- 分頁：`SPC 圖表關聯心智圖`
  - A 內容主體：圖表名稱、圖表關聯主題（對應 `topic` 語意）
  - B 製程觀測：統計方式、訊號來源（對應 `key_parameters`/`detection_signals` 語意）
  - C 風險與決策：SPI 關聯敘述中的風險判讀與調整建議（對應 `risk_level`/`control_actions` 語意）
  - D 治理與版本：心智圖維護版本與審核狀態（對應 `review_status`/`revision`/`updated_at`）
- 分頁：`圖表功能參考（舊版）`
  - A 內容主體：`圖表名稱`, `IPC規範`
  - B 製程觀測：`SMT資料抓取統計方式`
  - C 風險與決策：`用途` 中涉及的判讀/改善語意
  - D 治理與版本：沿用主體文件的版本與審核策略（不加主表欄位）

## 8) v1.0 驗收清單（PM / 工程 / QA）

### 8.1 PM 驗收（資訊架構與範圍）
- [ ] 分頁範圍完整：六個分頁皆已納入同一分類樹語意。
- [ ] 分類結構符合定版：固定 2 層（A/B/C/D 主域 + 對應欄位）。
- [ ] 決策落地一致：`keywords` 歸內容層、治理欄位不進主表、SPC 心智圖併入同樹。
- [ ] 交付可追溯：分頁、欄位、規則均可回溯到程式/契約來源。

### 8.2 工程驗收（資料映射與顯示）
- [ ] UI 7 欄映射正確：`主題/失效模式/關聯標準/關鍵參數/偵測訊號/風險/狀態` 對應既定主域。
- [ ] seed 欄位映射正確：`topic/failure_mode/ipc_jstd_refs/key_parameters/detection_signals/risk_level/review_status` 無語意漂移。
- [ ] REQUIRED_FIELDS 無遺漏：`fa_evidence/control_actions/id/pillar/revision/updated_at/keywords` 已有明確主域歸屬。
- [ ] 主表顯示策略一致：`revision`、`updated_at` 不進主表，只走非主表呈現。
- [ ] 知識分頁規則一致：`SPC 圖表關聯心智圖` 與 `圖表功能參考（舊版）` 已套同一分類樹語意。

### 8.3 QA 驗收（可測性與一致性）
- [ ] 分頁數與命名一致：與 `tests/test_data_management_page_tabs.py` 期待一致。
- [ ] 欄位映射可驗證：任抽一筆資料可從 UI 欄位追溯到 seed 欄位與主域。
- [ ] 邊界無衝突：同一欄位不會同時落入兩個主域（除明確定義之語意映射）。
- [ ] 版本治理可追蹤：`review_status/id/revision/updated_at` 可在非主表路徑被查看。
- [ ] 變更門檻明確：新增欄位若未標註主域，視為未通過驗收。

### 8.4 驗收結論格式（建議）
- 驗收結果：`Pass` / `Conditional Pass` / `Fail`
- 缺失清單：`欄位名稱`、`問題描述`、`影響分頁`、`修正責任`
- 修正期限：`YYYY-MM-DD`
