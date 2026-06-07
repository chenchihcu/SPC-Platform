# 產品鋼板規格 — Checklist 驗收報告

依需求 checklist 逐項對照程式碼之驗收結果。

---

## 一、階梯鋼板規則

### 1. 是否已明確定義：指定 precision 元件後，其餘全部自動歸 main

**結果：是**

- **定義位置**：[app/data/stencil_assignment_registry.py](../../../app/data/stencil_assignment_registry.py)
  - `save_assignments()` 文件（L101-102）：「precision_refdes 為套用「精密厚度」的 RefDes 清單；**其餘元件視為 main**。」
  - 僅儲存「勾選為精密」的 RefDes，不儲存 main 清單。
- **套用邏輯**：`get_profile_by_refdes(product_name, refdes)`（L140-152）
  - 若該 RefDes 在指派清單內且 `assigned_profile == PROFILE_PRECISION` → 回傳 `"precision"`。
  - **其餘情況（未在清單內）一律回傳 `PROFILE_MAIN`**（L152：`return PROFILE_MAIN`）。
- 結論：只儲存 precision 清單，其餘皆視為 main，行為與規格一致。

---

### 2. 是否已明確定義指派粒度為 RefDes

**結果：是**

- **資料結構**：`stencil_assignment_registry` 每筆為 `refdes` + `assigned_profile`（L114-118），以 RefDes 為單位。
- **UI**：[app/ui/widgets/stencil_spec_editor.py](../../../app/ui/widgets/stencil_spec_editor.py) 由 `coord_df["RefDes"].unique()` 取得清單，以 CheckBox 逐一勾選（L198-202）。
- **API**：`list_precision_refdes(product_name)`、`get_profile_by_refdes(product_name, refdes)` 皆以 RefDes 為鍵。
- 結論：指派粒度為 RefDes，已明確定義並實作。

---

### 3. 是否已明確定義階梯鋼板未指定精密元件時不可分析

**結果：是**

- **分析前檢查**：[app/services/spec_resolver.py](../../../app/services/spec_resolver.py)
  - `can_run_analysis(product_name)`（L157-158）：若 `stencil_type == STENCIL_STEPPED` 且 `not has_any_precision_assignment(key)` → 回傳 `(False, "階梯鋼板尚未指定精密厚度套用元件，請在資料設定頁指定。")`。
  - `resolve_workorder_spec(product_name)`（L81-82）：階梯鋼板且無精密指派時回傳 `(None, "階梯鋼板尚未指定精密厚度套用元件，請在資料設定頁指定。")`。
- **主流程阻斷**：[app/ui/main_window.py](../../../app/ui/main_window.py) `_run_refresh_analysis()`（L240-246）
  - 先呼叫 `can_run_analysis(product_name)`；若 `not ok` 則顯示 `msg`、設定錯誤狀態、`return`，**不呼叫 AnalysisWorker**。
- 結論：階梯鋼板且未指定任何精密 RefDes 時，無法進入分析，並有明確提示。

---

## 二、規格套用

### 4. 普通鋼板是否全域套用單一 Height 規格

**結果：是**

- [app/services/spec_resolver.py](../../../app/services/spec_resolver.py) `resolve_workorder_spec()`（L69-78）
  - 當 `stencil_type == STENCIL_NORMAL` 時，`height_spec = build_height_spec(thickness_main)`，單一組 target/lsl/usl。
  - 回傳之 `workorder_spec["height"]` 為該組（字串形式），供全部分析使用。
- 分析與 summary 皆使用此單一 `workorder_spec["height"]`，無 per-RefDes 分支。
- 結論：普通鋼板為單一 Height 規格全域套用。

---

### 5. 階梯鋼板是否能依 RefDes 套用不同 Height 規格

**結果：是（規格解析與資料層；彙總圖表 Phase 1 以 main 代表）**

- **Per-RefDes 規格來源**：[app/services/spec_resolver.py](../../../app/services/spec_resolver.py) `resolve_height_spec_by_refdes(product_name, refdes_list)`（L101-141）
  - 依 `get_profile_by_refdes(key, refdes)` 取得每個 RefDes 的 profile（main / precision），回傳 `Dict[refdes, {target, lsl, usl}]`。
  - 階梯鋼板時，不同 RefDes 可對應 main 或 precision 厚度推導之不同規格。
- **SessionStore**：`height_spec_by_refdes`（[app/data/session_store.py](../../../app/data/session_store.py) L39）預留給 per-RefDes 規格；目前主流程未在載入時寫入，可於 Phase 2 由 main_window 在分析前呼叫 `resolve_height_spec_by_refdes` 並寫入 store，供未來 per-RefDes 報表使用。
- **Phase 1 彙總行為**：`resolve_workorder_spec()` 階梯時回傳之 `workorder_spec["height"]` 為 **main 厚度** 之規格（L92-96 註解：「分析時整體 workorder_spec 用 main 作為代表」），summary / capability 等仍用此單一 height；即階梯鋼板在「整體彙總圖表」上以 main 為代表，細部 per-RefDes 圖表/報表為 Phase 2。
- 結論：階梯鋼板在規格解析層已能依 RefDes 套用不同 Height（`resolve_height_spec_by_refdes`）；Phase 1 彙總分析以單一 main 規格代表，符合設計文件。

---

### 6. Volume / Area 是否固定使用預設規格

**結果：是**

- [app/services/spec_resolver.py](../../../app/services/spec_resolver.py)（L59-68）
  - Volume：`default_volume_target/lsl/usl` 以 `DEFAULT_VOLUME_TARGET/LSL/USL`（100/70/150）為預設。
  - Area：`default_area_target/lsl/usl` 以 `DEFAULT_AREA_TARGET/LSL/USL`（100/70/150）為預設。
- [app/data/product_spec_registry.py](../../../app/data/product_spec_registry.py) 常數（L17-22）：Volume/Area 預設 100 / 70 / 150。
- `resolve_workorder_spec()` 產出之 `workorder_spec["volume"]`、`workorder_spec["area"]` 一律來自上述預設（或主檔內同名的 default_*，主檔亦依同常數初始化）。
- 結論：Volume / Area 固定使用預設規格（100/70/150）。

---

## 三、資料一致性

### 7. 是否將鋼板規格設為 single source of truth

**結果：是**

- **規格寫入**：僅來自產品規格主檔與解析服務。
  - [app/ui/main_window.py](../../../app/ui/main_window.py) 分析前（L238-256）：有產品時一律 `resolve_workorder_spec(product_name)` 寫入 `store.workorder_spec`，不從工單頁讀取。
  - 工單儲存（L486-499）：若 `get_product_spec(product_name)` 存在，則以 `resolve_workorder_spec(product_name)` 寫入 `store.workorder_spec`，不從工單頁欄位寫入。
- **工單頁**：[app/ui/pages/workorder_page.py](../../../app/ui/pages/workorder_page.py) 當產品有規格時 `set_spec_from_store(..., read_only=True)`，規格欄位唯讀，不可在工單頁修改。
- **編輯入口**：僅在資料設定頁之 [app/ui/widgets/stencil_spec_editor.py](../../../app/ui/widgets/stencil_spec_editor.py) 寫入 `product_spec_registry` 與 `stencil_assignment_registry`。
- 結論：鋼板規格以產品規格主檔 + 解析服務為單一來源，工單頁僅顯示/唯讀。

---

### 8. 座標更新後是否重設精密元件指派

**結果：是**

- **偵測**：[app/data/stencil_assignment_registry.py](../../../app/data/stencil_assignment_registry.py) `is_coord_path_changed(product_name, current_coord_path)`（L76-88）
  - 若該產品有階梯指派且目前座標路徑與指派記錄之 `coord_file_path` 不同（或記錄為空），回傳 True。
- **重設**：同模組 `clear_by_product(product_name)`（L126-138）清空該產品所有指派並更新 `coord_path_by_product`。
- **觸發時機**：[app/ui/main_window.py](../../../app/ui/main_window.py) `on_load_finished()`（L604-611）
  - 依產品名稱載入座標完成後，若 `is_coord_path_changed(product_name, current_coord_path)` 則呼叫 `clear_by_product(product_name)`，並顯示「座標已更新，請在資料設定頁重新指定階梯鋼板精密元件。」
- **移除產品時**：[app/data/coordinate_registry.py](../../../app/data/coordinate_registry.py) `remove_by_product_name()`（L67-84）會一併呼叫 `clear_by_product(key)`，移除座標時同步清除指派。
- 結論：座標路徑變更或產品自註冊表移除時，會重設該產品之精密元件指派。

---

### 9. 是否避免不同頁面維護不同版本的規格值

**結果：是**

- **單一寫入處**：規格僅在「資料設定頁 → 鋼板規格編輯器」寫入產品規格主檔與階梯指派；工單頁不寫入規格（有產品規格時為唯讀）。
- **單一讀取路徑**：分析與工單顯示皆透過 `resolve_workorder_spec(product_name)` 取得規格，再寫入 `store.workorder_spec` 並同步工單頁；不從工單頁 QLineEdit 回寫。
- **無重複編輯**：工單頁規格區在有產品規格時 `setReadOnly(True)`，tooltip 提示「請至資料設定頁修改」。
- 結論：僅在資料設定頁維護鋼板規格，其他頁面不維護規格值，避免多版本不一致。

---

## 四、驗收總結

| 項目 | 結果 |
|------|------|
| 指定 precision 後其餘歸 main | 是 |
| 指派粒度為 RefDes | 是 |
| 階梯未指定精密元件不可分析 | 是 |
| 普通鋼板單一 Height 全域套用 | 是 |
| 階梯鋼板依 RefDes 不同 Height（解析層） | 是（彙總 Phase 1 以 main 代表） |
| Volume/Area 固定預設 | 是 |
| 鋼板規格 single source of truth | 是 |
| 座標更新重設精密指派 | 是 |
| 避免多頁面維護不同規格 | 是 |

以上項目均符合 checklist 要求；階梯鋼板 per-RefDes 之「彙總圖表/報表」使用 `height_spec_by_refdes` 為 Phase 2 擴充，設計與實作已預留介面與 store 欄位。
