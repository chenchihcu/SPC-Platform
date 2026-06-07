# 產品級鋼板厚度／錫膏規格資料庫管理 — 完整設計文件

本文件為「產品級鋼板厚度／錫膏規格資料庫管理」功能之分析與設計，不包含實作 patch。實作前請依此設計進行開發與驗收。

---

## 1. 現況架構盤點

### 1.1 產品名稱與主資料

| 項目 | 現況位置 | 說明 |
|------|----------|------|
| **產品名稱來源** | `SessionStore.workorder_master["product_name"]` | 由「資料設定」頁選擇產品載入座標時，經 `product_name_selected` 寫入；工單儲存時亦從 store 讀取 product_name 寫回 master。 |
| **產品名稱列表** | `app/data/coordinate_registry.py` → `list_registered()` | 註冊表每筆為 `{ product_name, product_part_no, file_path, created_at }`，產品名稱來自「座標檔管理」綁定。 |
| **產品 ↔ 座標** | `get_path_by_product_name(product_name)` | 依產品名稱回傳座標檔路徑；一產品一筆座標綁定，覆寫更新。 |

**結論**：目前沒有獨立的「產品主檔」；產品名稱事實上是座標註冊表的 key。鋼板規格若要以產品為維度管理，需新增「產品規格主檔」並與產品名稱（與座標註冊表）對齊。

### 1.2 座標檔 Registry / Mapping

| 項目 | 現況位置 | 說明 |
|------|----------|------|
| **座標註冊表** | `app/data/coordinate_registry.py` | JSON 檔 `data/coordinate_registry.json`，`list_registered()`、`register()`、`get_path_by_product_name()`、`remove_by_product_name()`。 |
| **座標載入** | `CoordinateLoader.load()` → `SessionStore.coord_df`、`coord_meta` | 載入後 join 產生 `joined_df`；`coord_meta` 含 `filepath`、`is_valid`、`missing_required` 等。 |
| **RefDes 清單** | `coord_df["RefDes"]` 或 `joined_df["RefDes"]` | 座標檔經 SchemaMapper 對應後必有 `RefDes`；join 後 joined_df 的 RefDes 為分析與篩選用。 |

**結論**：RefDes 清單可由目前載入之 `coord_df` 或 `joined_df` 的 `RefDes.unique()` 取得，供階梯鋼板「精密厚度套用元件」勾選清單使用。座標檔更新（重新載入或重新綁定同一產品）時，需能偵測並重設該產品之精密元件指派。

### 1.3 規格（Volume / Area / Height）目前儲存與套用

| 項目 | 現況位置 | 說明 |
|------|----------|------|
| **規格儲存** | `SessionStore.workorder_spec` | 工單儲存時由 `main_window._on_workorder_save_clicked()` 從工單頁 QLineEdit 寫入：`{"volume":{usl,lsl,target},"area":{...},"height":{...}}`，值為字串。 |
| **規格輸入** | `WorkorderPage` | 三組 QLineEdit：Volume / Area / Height 各 USL、LSL、Target；預設值為 120/80/100（Volume/Area）、0.15/0.08/0.12（Height）。 |
| **分析套用** | `main_window._schedule_refresh_analysis()` | 從 `wo_page.height_usl.text()` 等讀取，轉 float 後與 `workorder_spec` 一併傳入 `AnalysisWorker`；summary / capability 等皆用 `workorder_spec` 的 volume/area/height。 |
| **單一來源** | 否 | 規格目前來自「工單頁手動輸入」，未與產品綁定；若要做產品級鋼板規格，必須改為「以產品名稱讀取規格主檔」，工單頁僅顯示或唯讀帶出，不可再各自維護 Height。 |

**結論**：Volume/Area 可維持系統預設（Target=100, LSL=70, USL=150）；Height 需改為「依產品名稱 → 鋼板規格主檔 → 依類型與 RefDes 指派決定每筆之 Target/LSL/USL」。需引入「規格解析服務」：輸入產品名稱 + 當前座標/joined 狀態 + 可選 RefDes 清單，輸出用於分析的 `workorder_spec` 與 per-RefDes Height 規格（階梯時）。

### 1.4 Session / Central State 可否承接

| 項目 | 現況 | 可否承接 |
|------|------|----------|
| **SessionStore** | `meas_df`, `coord_df`, `joined_df`, `meas_meta`, `coord_meta`, `relation_meta`, `workorder_master`, `workorder_spec`, `selected_features`, `last_analysis_payload` | 可擴充：新增 `product_spec_master`（當前產品之規格主檔快取）、`stencil_assignment`（階梯鋼板時 RefDes → profile 對應），或由「規格服務」依 product_name 即時查表產出，不一定要在 store 放完整主檔。 |
| **分析入口** | 使用 `workorder_spec` 與 primary 的 usl/lsl/target | 分析前必須能取得「已解析之 workorder_spec」與（階梯時）per-RefDes 的 Height 規格；若沿用現有 workorder_spec 結構，則需在「解析規格」時產出扁平之 height 規格或依 RefDes 分組之結構供 summary/capability 使用。 |

**結論**：SessionStore 可保留 `workorder_spec` 作為「分析用已解析規格」；其來源改為「產品鋼板規格服務」依產品名稱 + 階梯指派產出，而非工單頁手動輸入。可選：在 store 增加 `product_spec_snapshot`（當前產品規格快取）與 `height_spec_by_refdes`（階梯時 RefDes → {target, lsl, usl}）供分析與 UI 顯示。

---

## 2. 規格資料模型設計

### 2.1 Product Spec Master（產品規格主檔）

建議儲存於獨立 JSON 檔（如 `data/product_spec_registry.json`）或與 coordinate_registry 同層，以產品名稱為 key 可查。

| 欄位 | 型別 | 說明 |
|------|------|------|
| `product_name` | str | 產品名稱，與座標註冊表對齊，唯一。 |
| `stencil_type` | `"normal"` \| `"stepped"` | 鋼板類型：普通 / 階梯。 |
| `default_volume_target` | float | 預設 100。 |
| `default_volume_lsl` | float | 預設 70。 |
| `default_volume_usl` | float | 預設 150。 |
| `default_area_target` | float | 預設 100。 |
| `default_area_lsl` | float | 預設 70。 |
| `default_area_usl` | float | 預設 150。 |
| `thickness_main` | float | 主厚度（mm）；普通鋼板即唯一厚度；階梯鋼板為「非精密」厚度。 |
| `thickness_precision` | float \| null | 階梯時之精密厚度（mm）；普通鋼板為 null。 |
| `precision_is_main` | bool | 階梯時：true 表示 main 為精密、false 表示 precision 為精密。可改為枚舉 `precision_profile: "main"|"precision"` 更直觀。 |
| `updated_at` | str (ISO) | 最後更新時間。 |

Volume/Area 固定用系統預設時，Master 可只存 Height 相關與 stencil_type，Volume/Area 由程式常數帶入。

### 2.2 Height / Stencil Thickness Spec（推導結構，可不持久）

由 Master 推導，供分析與 UI 顯示用：

**普通鋼板**

- `thickness_main` = T
- `height_target_main` = T
- `height_lsl_main` = T × 0.70
- `height_usl_main` = T × 1.40  
- 所有 RefDes 使用此一組。

**階梯鋼板**

- `thickness_main`、`thickness_precision` 兩組
- `height_target_main` = thickness_main，`height_lsl_main` = thickness_main × 0.70，`height_usl_main` = thickness_main × 1.40
- `height_target_precision` = thickness_precision，`height_lsl_precision` = thickness_precision × 0.70，`height_usl_precision` = thickness_precision × 1.40
- 哪一組為「精密」由 `precision_profile` 或 `precision_is_main` 決定；指派時「精密厚度」對應的 profile 套用在被勾選的 RefDes 上。

### 2.3 Step Stencil Assignment Mapping（階梯鋼板 RefDes 指派）

建議儲存於同一產品規格下或獨立 JSON（如 `data/stencil_assignment_<product_name>.json`），以產品名稱為維度。

| 欄位 | 型別 | 說明 |
|------|------|------|
| `product_name` | str | 所屬產品。 |
| `refdes` | str | 元件位號。 |
| `assigned_profile` | `"main"` \| `"precision"` | 套用主厚度或精密厚度。 |
| `assignment_source` | `"manual"` \| `"batch_rule"` \| `"default"` | Phase 1 僅 manual。 |
| `coord_file_path` | str \| null | 建立指派時之座標檔路徑；若與目前載入座標路徑不同，視為座標已更新，清空指派。 |
| `coord_registry_updated_at` | str \| null | 可選：註冊表該產品最後更新時間，用於偵測座標綁定是否變更。 |

**重設規則**：當產品座標檔更新（同一產品名稱重新 register 或載入之 coord 路徑/內容變更）時，該產品之所有 `refdes → profile` 指派一律清空，需重新勾選。

---

## 3. 普通鋼板／階梯鋼板的規格邏輯設計

### 3.1 普通鋼板

- 僅一組厚度 `thickness_main`。
- Height 規格：Target = thickness_main，LSL = thickness_main × 0.70，USL = thickness_main × 1.40。
- 所有 RefDes、所有分析皆使用此一組；無需 RefDes 指派表。

### 3.2 階梯鋼板

- 兩組厚度：`thickness_main`、`thickness_precision`；且需標記哪一組為「精密」。
- 兩組之 LSL/USL 比例一致：LSL = Target × 70%，USL = Target × 140%。
- **指派**：使用者勾選「套用精密厚度的 RefDes」；被勾選者使用精密厚度那一組，其餘一律使用 main。
- **約束**：若產品為階梯鋼板但「精密 RefDes 清單」為空，不允許開始分析，並顯示「尚未指定元件」。

---

## 4. 階梯鋼板元件位置指派設計

### 4.1 資料來源

- RefDes 清單來自「目前產品的座標檔」：即 `coord_df["RefDes"].unique()` 或 `joined_df["RefDes"].unique()`（建議以 coord 為準，與量測 join 後可能只會少不會多）。
- 若尚未載入該產品座標，可顯示「請先依產品名稱載入座標後再指定精密元件」。

### 4.2 指派流程（Phase 1：手動勾選）

1. 使用者選擇產品名稱（或已依產品載入座標，產品名稱即 store.workorder_master["product_name"]）。
2. 若該產品為階梯鋼板，顯示「精密厚度套用元件」區塊。
3. 由「目前座標檔」載入 RefDes 清單，以 CheckBox 或多選 List 供使用者勾選。
4. 儲存時寫入 Step Stencil Assignment Mapping（product_name + refdes + assigned_profile=precision，source=manual），並記錄當前 coord 路徑或版本。
5. 若之後同一產品座標檔更新（見下節），清空該產品指派並提示使用者重新指定。

### 4.3 座標更新偵測與重設

- **觸發時機**：產品 A 已存在規格與指派；使用者重新「匯入 PCB 座標」並「儲存至註冊表」覆寫產品 A 的座標路徑，或重新「依產品名稱載入」產品 A 時載入的檔案與上次不同。
- **實作建議**：在 assignment 記錄 `coord_file_path`（或 coord 檔的 hash/updated_at）；每次「依產品名稱載入座標」完成時，若當前產品有階梯指派，比對當前載入之 `coord_meta["filepath"]` 與指派記錄的 coord_file_path；若不同或缺失，則清空該產品之精密元件指派並寫回，UI 顯示「座標已更新，請重新指定精密厚度套用元件」。

### 4.4 批量規則擴充點（Phase 2）

- 保留 `assignment_source`：`manual` | `batch_rule` | `default`。
- 預留「批量規則」介面：例如依 PartType、區域等寫入 `batch_rule`，Phase 1 可不實作規則引擎，僅架構預留。

---

## 5. 與座標檔管理整合的設計方案

### 5.1 產品維度一致

- 座標註冊表以 `product_name` 為 key；產品規格主檔亦以 `product_name` 為 key；兩邊共用同一產品名稱來源（資料設定頁選擇產品 = 座標註冊表內之名稱）。
- 「依產品名稱載入座標」後，可自動帶入該產品之鋼板規格（若存在）：寫入 store 的 workorder_spec 與 height 指派快取，並驅動工單頁規格顯示為唯讀或預填。

### 5.2 流程整合

- **資料設定頁**：在「座標檔管理」區塊旁或下方新增「產品鋼板規格」區塊（或獨立 Tab/子頁），流程為：選擇產品 → 若無規格則建立（鋼板類型、厚度、階梯時精密厚度與 RefDes 勾選）→ 若有規格則可編輯；RefDes 清單由「目前載入之座標」提供，若尚未載入則提示先載入該產品座標。
- **座標註冊表變更**：移除產品時，可同步移除或保留該產品之規格主檔（建議：移除產品時一併移除其規格與指派，保持一致性）。
- **座標覆寫**：同一產品名稱重新 register 新座標路徑時，觸發「階梯指派重設」邏輯。

### 5.3 RefDes 清單來源單一

- 一律以「當前 SessionStore 內該產品對應之 coord_df」為 RefDes 清單來源；若目前載入的座標並非該產品，則「精密元件勾選」區塊顯示「請先依產品名稱載入座標」或停用。

---

## 6. UI / Workflow 設計建議

### 6.1 規格管理放置位置

- **建議**：在「資料設定」頁內，與「座標檔管理」並列或在其下方新增「產品鋼板規格 (Stencil Spec)」區塊；或於同一頁用 Tab/GroupBox 區隔「座標檔管理」與「鋼板規格管理」。理由：產品名稱、座標、規格三者皆在資料設定階段完成，分析與工單頁僅消費規格，不在此維護。

### 6.2 建立／編輯產品規格流程

1. **選擇產品**：下拉選單與座標註冊表共用產品名稱列表（或從 `list_registered()` 取得）；選後可「載入該產品規格」到表單。
2. **鋼板類型**：單選 Normal / Stepped。
3. **厚度輸入**：  
   - Normal：僅「鋼板厚度」(mm)。  
   - Stepped：主厚度 + 精密厚度（兩欄），並標示「哪一組為精密」（例如 radio：主厚度為精密 / 精密厚度為精密）。
4. **Volume/Area**：Phase 1 可固定顯示系統預設（100/70/150），唯讀或隱藏。
5. **階梯鋼板 — 精密套用元件**：  
   - 若尚未載入該產品座標：顯示「請先依產品名稱載入座標，以取得 RefDes 清單」。  
   - 已載入：列出當前 coord 之 RefDes，多選勾選「套用精密厚度」的元件；儲存時寫入 Step Stencil Assignment。
6. **儲存**：寫入 Product Spec Master + 若有階梯則寫入 Assignment；並可更新 SessionStore 的規格快取，使工單頁與分析即時反映。

### 6.3 「由目前座標檔載入 RefDes 清單」

- **建議實作**：在階梯鋼板區塊內，「RefDes 清單」直接從 `SessionStore.coord_df`（或 joined_df）的 `RefDes.unique()` 取得；若當前載入的座標是依產品名稱載入的，則產品名稱與座標一致，清單即為該產品之 RefDes。若使用者先選產品再載入座標，載入完成後自動刷新該區塊清單。

### 6.4 「產品名稱 → 自動載入鋼板規格」

- **建議實作**：  
  - 「依產品名稱載入座標」完成時，若該產品存在規格主檔，則自動讀取並寫入 `SessionStore.workorder_spec`（及必要時 `height_spec_by_refdes`），並將工單頁之規格欄位設為唯讀或預填（不可手動改 Height，避免破壞單一來源）。  
  - 工單頁「產品名稱」仍為唯讀（由資料設定帶入）；規格區改為顯示「來自產品鋼板規格」之 Volume/Area/Height，階梯時 Height 可顯示兩組與「依 RefDes 套用」說明。

### 6.5 階梯鋼板未指定精密元件

- 若產品為階梯鋼板且精密 RefDes 清單為空：  
  - 「重新整理分析」時先檢查此條件；若不通過，不呼叫 AnalysisWorker，並顯示「尚未指定元件」或「請在資料設定頁指定階梯鋼板之精密厚度套用元件」。  
  - 可於 control_panel 或工單頁顯示狀態：例如「階梯鋼板：尚未指定精密元件」。

---

## 7. 分析階段的規格套用邏輯

### 7.1 Volume / Area

- 固定使用系統預設：Target = 100，LSL = 70，USL = 150（或從 Product Spec Master 的 default_* 讀取，Phase 1 可寫死常數）。

### 7.2 Height — 普通鋼板

- 全部分析皆使用同一組：Target = thickness_main，LSL = thickness_main × 0.70，USL = thickness_main × 1.40。  
- `workorder_spec["height"]` = 此組；summary/capability 等與現行一致，單一 series 一組 spec。

### 7.3 Height — 階梯鋼板

- **Per-RefDes 規格**：每個 RefDes 依 Assignment 取得 profile（main 或 precision），再對應到該 profile 的 target/lsl/usl。  
- **分析時**：  
  - 若為「單一特徵 Height」之整體圖表（如 I-MR、直方圖、Cpk）：需以「加權」或「分組」方式處理兩組規格，或先依 RefDes 分組計算再彙總；具體可為：按 RefDes 分組，每組用對應之 target/lsl/usl 算 Cpk/良率，再彙總 overall。  
  - 若為「單一板/單一 RefDes」篩選：該 RefDes 對應一組規格，直接套用。  
- **workorder_spec**：可維持一份「代表值」供既有 summary 使用（例如用 main 作為預設），另提供 `height_spec_by_refdes: Dict[str, {target, lsl, usl}]` 給需要 per-RefDes 的引擎或圖表；或改 summary_engine 支援 per-RefDes height spec 再彙總。

### 7.4 產品未建立規格

- 若產品名稱存在於座標註冊表但不存在於規格主檔：  
  - 可視為「尚未設定鋼板規格」；不自動帶入規格，工單頁可顯示「未設定產品規格，請至資料設定建立」；分析時可阻止或使用 fallback（例如沿用目前工單頁預設值並顯示 warning）。  
  - 建議：若已選產品且無規格，阻止分析並提示「請先為該產品建立鋼板規格」。

### 7.5 產品已選但無對應鋼板規格

- 阻止分析並顯示：「該產品尚未建立鋼板規格，請至資料設定頁建立。」

### 7.6 階梯鋼板且精密 RefDes 為空

- 阻止分析並顯示：「階梯鋼板尚未指定精密厚度套用元件，請在資料設定頁指定。」

---

## 8. 預計新增／修改的檔案與模組

### 8.1 新增

| 類型 | 路徑／名稱 | 說明 |
|------|------------|------|
| 資料層 | `app/data/product_spec_registry.py` | 產品規格主檔的 list/get/save/remove，JSON 持久化（如 `data/product_spec_registry.json`）。 |
| 資料層 | `app/data/stencil_assignment_registry.py` | 階梯鋼板 RefDes 指派的 list/save/clear_by_product，含座標版本比對與重設。 |
| 服務層 | `app/services/spec_resolver.py` 或 `app/data/spec_resolver.py` | 依 product_name + 當前 coord/assignment 解析出 workorder_spec 與 height_spec_by_refdes；供 main_window 與分析使用。 |
| UI | `app/ui/widgets/stencil_spec_editor.py` 或內嵌於資料設定頁 | 鋼板類型、厚度、階梯時精密 RefDes 勾選清單、儲存。 |
| UI | 資料設定頁擴充 | 新增「產品鋼板規格」區塊或 Tab，呼叫 stencil_spec_editor 與 registry。 |

### 8.2 修改

| 檔案 | 修改要點 |
|------|----------|
| `app/data/session_store.py` | 可選：新增 `product_spec_snapshot`、`height_spec_by_refdes`；或僅由 spec_resolver 在分析前即時寫入 `workorder_spec`。 |
| `app/ui/pages/workorder_page.py` | 規格區改為由產品規格帶入；Height（及必要時 Volume/Area）改唯讀或僅顯示，不可手動改；或依產品是否已設定規格切換「編輯/唯讀」。 |
| `app/ui/main_window.py` | 分析前呼叫 spec_resolver，取得 workorder_spec；檢查階梯鋼板是否已指定精密元件、產品是否有規格；必要時阻止分析並提示；「依產品名稱載入座標」完成時載入產品規格並同步到工單頁。 |
| `app/viewmodels/chart_analysis_viewmodel.py` 或 analysis worker | 使用 spec_resolver 產出之 workorder_spec；若支援 per-RefDes Height，summary_engine 或 capability 需能接受 per-RefDes spec 或預先合併。 |
| `app/analytics/summary_engine.py` | 若階梯鋼板 Height 需 per-RefDes 計算再彙總，需擴充介面（例如傳入 height_spec_by_refdes 或按 RefDes 分組後再算 overall）。 |
| `app/ui/pages/data_setup_page.py` | 整合「產品鋼板規格」區塊；座標載入完成時可通知規格區刷新 RefDes 清單。 |
| `app/data/coordinate_registry.py` | 可選：remove_by_product_name 時通知或呼叫規格側「移除該產品規格與指派」以保持一致。 |

---

## 9. Phase 1 / Phase 2 實作順序

### Phase 1（本次範圍）

1. **資料模型與持久化**：Product Spec Master、Step Stencil Assignment 的 JSON 結構與 registry API（list/get/save/remove；assignment 含 clear_by_product 與 coord 版本檢查）。
2. **規格解析服務**：spec_resolver 依 product_name 讀取 Master + Assignment，產出 workorder_spec（Volume/Area 固定預設，Height 依類型與指派）；階梯時產出 height_spec_by_refdes。
3. **分析前檢查**：產品無規格 → 阻止分析；階梯鋼板且精密清單為空 → 阻止分析並提示。
4. **工單頁**：規格改為由產品規格帶入（唯讀或預填），不再手動輸入 Height；必要時 Volume/Area 也唯讀。
5. **資料設定頁 — 鋼板規格區塊**：選擇產品、鋼板類型、厚度、階梯時精密厚度與 RefDes 勾選（RefDes 來自當前 coord_df）、儲存；座標載入完成時刷新 RefDes 清單。
6. **座標更新重設**：依產品名稱載入座標完成時，若該產品有階梯指派且當前 coord 路徑與指派記錄不同，清空指派並提示。
7. **依產品名稱載入時帶入規格**：載入座標完成後若該產品有規格，自動寫入 store.workorder_spec 並同步工單頁顯示。

### Phase 2（擴充）

- 批量規則架構與 UI（依 PartType、區域等自動指派 profile）。  
- 若需更細的 per-RefDes 分析報表，擴充 summary_engine 與圖表使用 height_spec_by_refdes。  
- 產品規格與座標註冊表刪除產品時的聯動（移除產品時一併刪除規格與指派）。

---

## 10. 驗收標準

- 可為每個產品名稱建立／編輯一筆鋼板規格（類型、主厚度、階梯時第二厚度與精密標記）。  
- 階梯鋼板可從當前座標檔 RefDes 清單手動勾選「精密厚度套用元件」，儲存後可載入與編輯。  
- 同一產品座標檔更新（重新綁定或重新載入）後，該產品之精密元件指派自動清空並提示重新指定。  
- 分析前：若產品無規格或階梯鋼板未指定任何精密元件，阻止分析並顯示明確提示。  
- 分析時 Volume/Area 使用系統預設 100/70/150；Height 依產品規格與類型（及階梯時 RefDes 指派）正確套用。  
- 工單頁規格區不再手動輸入 Height，改為由產品規格唯讀或預填；單一來源無二處維護。  
- 「依產品名稱載入座標」完成後，若該產品有規格，自動帶入工單與分析用規格。

---

## 11. 潛在風險與邊界條件

| 風險／邊界 | 說明 | 緩解 |
|------------|------|------|
| 產品有座標但未建規格 | 使用者先載入座標再建規格，或只建座標不建規格 | 分析前檢查並提示「請先建立產品鋼板規格」；工單頁可顯示「未設定規格」狀態。 |
| 座標與規格產品不一致 | 先選產品 A 載入座標，再切換產品 B 未重新載入座標 | RefDes 清單與指派以「當前 store 的 product_name + coord_df」為準；若當前 coord 非產品 B，則產品 B 的階梯指派區顯示「請先載入產品 B 座標」。 |
| 階梯時 summary 的 Height 彙總 | 兩組規格如何彙總成一個 Cpk/良率 | Phase 1 可先以「main 規格」作為整體代表，或按 RefDes 分組計算再取 min/平均；Phase 2 再細化 per-RefDes 報表。 |
| 規格主檔與座標註冊表不同步 | 手動刪除 JSON 或只刪座標不刪規格 | 移除座標產品時一併移除規格（Phase 2）；或提供「同步檢查」提示。 |
| 多視窗／多 Session | 同一產品在兩台機器上編輯規格 | 以檔案為準，最後寫入覆蓋；必要時可加樂觀鎖或 updated_at 提示。 |

---

以上為產品級鋼板厚度／錫膏規格資料庫管理之完整設計，實作時請依此文件與業務規則進行開發與驗收。
