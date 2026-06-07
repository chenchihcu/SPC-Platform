# 強化版 Antigravity Agent 任務需求
## SMT SPI / SPC 統計分析平台 v2
## PySide6 UI 實作任務圖 + 驗證 + 失敗處理邏輯

**專案類型：** 桌面工程分析軟體  
**框架：** PySide6  
**主要領域：** SMT SPI / SPC 統計分析  
**實作模式：** 任務圖(Task Graph) + 里程碑驗證  
**視覺基準：** 使用者提供的 UI 截圖為設計規範  
**資料基準：** 專案必須支援「座標檔」與「量測記錄檔」作為核心資料來源，並建立可驗證的資料契約、欄位映射、關聯邏輯與失敗處理機制

**規格治理索引：** 契約／計畫／程式三者對齊、必須先更新規格再改碼之觸發條件，見 **`docs/specs/spec_maintenance_and_alignment.md`**。

# 1 任務目標

依據提供的 UI 截圖，實作或重構 **SMT SPI / SPC 統計分析平台 v2** 的 PySide6 UI 元件與資料流整合邏輯。

本專案不是一般 Dashboard，而是 **工程統計分析平台**。因此系統必須同時滿足：

- DPI-aware 桌面顯示
- 穩定三區式工作流程
- 大數據量下可用
- SPC 統計語義正確
- 圖表與資料來源一致
- 模組化 UI 結構
- 座標檔與量測記錄檔可正確關聯
- 關聯失敗時可被偵測、提示、隔離

所有 UI 結構以截圖為視覺基準；所有分析功能以 **實際資料契約與欄位映射成功** 為完成前提。

# 2 核心執行規則

## 2.1 不可任意重新設計 UI
必須以截圖架構為基礎。不可自行改為不同的 dashboard 形式或與既有流程不一致的資訊架構。

## 2.2 不可忽略資料契約
本專案不只做畫面。Agent 必須把以下兩種資料來源視為核心：
- 座標檔
- 量測記錄檔

若未完成資料契約、欄位映射、關聯鍵驗證，則不得聲稱分析功能完成。

## 2.3 保持工程統計語義
UI 名稱、指標、圖表、摘要、狀態標示必須符合：
- SMT / SPI 製程語義
- SPC 統計意義
- 能力分析與分布分析的正確區分

## 2.4 必須模組化
所有頁面、表單、表格、圖表元件需可拆分、可維護、可測試。不得把資料解析、商業邏輯、UI 更新寫成單一大函式。

## 2.5 必須進行 DPI 驗證
每個主要頁面完成後，必須執行 Windows 高 DPI 驗證。

## 2.6 不可假裝完成
若遇到以下情況：
- backend 未完成
- schema 不一致
- chart adapter 未接好
- 座標檔欄位不完整
- 量測記錄缺關聯鍵
- 圖表輸入資料不足

必須明確回報缺口，不得輸出偽完成畫面或偽統計數值。

# 3 專案資料模型核心要求

本專案至少需支援以下資料實體：

## 3.1 座標檔（Coordinate File）
用途：建立 PCB 元件位置、RefDes、元件類型與空間分析基礎。

### 預期常見欄位
- RefDes
- X
- Y
- Layer
- PartType
- Rotation
- Width
- Height
- PartDecal 或 Package
- PadType 或相近欄位

### 最低必要欄位
- RefDes
- X
- Y

若缺少最低必要欄位，則不得啟用空間分析與 RefDes 空間映射。

## 3.2 量測記錄檔（Measurement Record File）
用途：提供 SPI / SPC 量測值、時間序、批次、元件量測資訊。

### 預期常見欄位
- RefDes
- BoardNo / BoardID / PanelID
- Time / Timestamp / InspectTime
- Volume
- Area
- Height
- XOffset
- YOffset
- Result / Judge / Status
- RunID / Batch / Lot / 工單相關欄位

### 最低必要欄位
- RefDes
- 至少一個量測值欄位（如 Volume / Area / Height）
- 至少一個批次或樣本識別欄位（如 BoardNo / Time / Batch）

若缺少上述最低必要欄位，則不得啟用完整統計分析。

## 3.3 工單 / 批次主資料
用途：對應工單編號、產線、產品料號、產品名稱、供應商、批量等資訊，作為篩選與報表輸出基礎。

## 3.4 分析目標 / 規格資料（若有）
可支援：
- USL
- LSL
- Target
- Control limit rule source
- 指標對應規則

若未提供規格資料，能力分析頁需明確區分「只有分布統計」與「具規格能力分析」。

# 4 任務圖 (Task Graph)

```text
T0 架構掃描與資料契約盤點
T1 主框架 Layout 驗證
T2 左側導航實作
T3 中間條件控制區
T4 右側分析區與 Tabs
T5 座標檔管理頁
T6 工單資料輸入頁
T7 資料匯入與欄位映射機制
T8 座標檔與量測記錄關聯驗證
T9 圖表分析頁與圖表整合
T10 DPI 視覺驗證
T11 SPC 統計語義驗證
T12 效能檢查
T13 最終整合報告
```

# 5 詳細執行計畫

## T0 架構掃描與資料契約盤點
### 目標
先理解目前專案 UI 架構與資料處理架構，再開始改動。

### 必須識別
- 主視窗入口
- Page container / stacked widget
- 左側 navigation owner
- 圖表區 owner
- 量測記錄載入流程
- 座標檔載入流程
- 欄位映射邏輯位置
- DPI 初始化位置
- 現有 schema / parser / adapter 類別

### 必須輸出
- UI 架構圖
- 資料流程圖
- 資料實體列表
- 目前已知 schema
- 缺失欄位 / 技術債 / 阻塞點

### 驗證
Agent 必須能說明：
- 主視窗 class
- Page switch 機制
- 座標檔 parser 位置
- 量測記錄 parser 位置
- DPI 設定位置

### 失敗處理
若無法識別，停止實作並回報未知點。

## T1 主框架 Layout 驗證
UI 必須符合三區架構：
```text
左側 Navigation
中間條件控制區
右側圖表 / 分析區
```

### 要求
- 水平主佈局
- 左側寬度穩定
- 中間控制區固定或半固定
- 右側分析區最大化
- resize 不破版

### 驗證
- 視窗縮放正常
- sidebar 可讀
- 右側分析區優先擴展

## T2 左側 Navigation
必須包含：
- 上傳資料
- 工單資料輸入
- 元件/量測選定
- 統計分析
- 圖表分析
- 報告輸出
- 座標檔管理
- 資料管理

### 驗證
- 單選 active state
- page switch 正常
- 不重置已載入資料
- 不重複建立 widget

### 失敗處理
未完成頁面以 placeholder 顯示，不可留白。

## T3 中間條件控制區
圖表分析頁至少包含：
- 分析批次
- 取樣模式
- RefDes
- 元件類型

操作按鈕：
- 重新整理批次
- 前往目標設定

### 額外要求
條件控制區必須能反映資料來源狀態，例如：
- 座標檔已載入 / 未載入
- 量測記錄已載入 / 未載入
- 欄位映射成功 / 未完成
- 關聯成功率

### 驗證
- 選 batch 後更新右側摘要
- 未選資料時顯示 empty state
- 資料狀態提示正確

## T4 右側分析區與 Tabs
必須包含 Tabs：
- 控制圖
- 分布與能力
- 群組比較(元件比較)
- 空間分析
- 柏拉圖分析
- 箱型圖
- 常態分析

### 規則
- tab 必須一直可見
- tab label 不可被 DPI 裁切
- 空資料要有 empty state
- 缺資料要有 dependency message

## T5 座標檔管理頁
### 必須支援
- 匯入歷史
- 欄位預覽
- 偵測格式
- 匯入紀錄編輯
- 刪除選取紀錄
- 重新整理歷史

### 歷史表格欄位
- 匯入批次
- 產品料號
- 產品名稱
- 檔案名稱
- 偵測格式
- 列數
- 匯入時間
- 來源路徑

### 預覽區
需顯示：
- 欄位名稱
- 偵測格式
- row / column summary
- 關聯可用欄位狀態

### 驗證
- row select 更新 preview
- 長路徑顯示安全
- schema 預覽正確
- 最低必要欄位驗證正確

### 失敗處理
若缺少 RefDes / X / Y：
- 標記為不可用於空間分析
- 禁用相關功能
- 顯示缺欄位提示

## T6 工單資料輸入頁
欄位：
- 工單編號
- 錫膏批號
- PCB Datecode
- 產線

操作：
- 儲存編輯
- 刪除批次
- 高風險完整刪除
- 清除選取
- 重新整理

表格：
- 工單編號
- 錫膏批號
- PCB Datecode
- 產線
- 供應商
- 產品料號
- 產品名稱
- 批量
- 更新時間

### 驗證
- row select 更新表單
- 刪除按鈕 enable/disable 正確
- 危險操作明確區隔

## T7 資料匯入與欄位映射機制
### 目標
系統必須能處理不同 CSV 欄位命名差異，建立標準欄位映射。

### 必須支援
#### 座標檔標準欄位映射
- RefDes
- X
- Y
- Layer
- PartType
- Rotation

#### 量測記錄標準欄位映射
- RefDes
- BoardNo / 樣本識別
- Time / 時間
- Volume
- Area
- Height
- XOffset
- YOffset
- Result

### 規則
- 支援欄位別名
- 保留原始欄位名
- 顯示映射結果
- 標示必要欄位是否齊備

### 驗證
- 能解析使用者上傳 CSV
- 映射結果可預覽
- 缺欄位時有提示
- 無效欄位不會讓 UI crash

### 失敗處理
若映射失敗：
- 不進入分析頁
- 顯示缺欄位與建議欄位名
- 保留原始檔 metadata

## T8 座標檔與量測記錄關聯驗證
### 目標
建立座標檔與量測記錄檔的可驗證關聯邏輯。

### 預設關聯鍵
第一優先：
- RefDes

可擴充輔助條件：
- Product / PartNo
- Layer
- Batch / RunID
- BoardNo

### 必須輸出
- 關聯筆數
- 未匹配筆數
- 匹配率
- 無效 RefDes 清單摘要
- 重複 RefDes 警示

### 驗證
- 關聯成功率可被顯示
- 關聯失敗時能追查原因
- 空間分析只使用成功映射資料

### 失敗處理
若關聯失敗：
- 禁用空間分析
- 圖表分析中顯示關聯不足
- 不可假裝有完整熱圖

## T9 圖表分析頁與圖表整合
必須支援：
- trend chart
- control chart
- histogram
- capability view
- comparison view
- heatmap
- pareto
- boxplot
- normality

### SPC 規則
- UCL / CL / LCL 必須明確
- out-of-control 點需標記
- Cp/Cpk/Pp/Ppk 需以有效資料計算
- 無規格資料時不可假裝能力分析成立
- histogram 與 capability 必須區分
- 空間熱圖只能基於成功關聯之座標資料

### 額外資料邏輯
#### 若只有量測檔、沒有座標檔
可啟用：
- 控制圖
- 分布分析
- 箱型圖
- 常態分析
- Pareto
- 群組比較

不可啟用：
- 空間分析 / heatmap

#### 若座標檔與量測檔皆存在且關聯成功
可啟用完整分析。

### 驗證
- legend 正確
- label 正確
- 空資料安全
- partial data 安全
- insufficient data 時明確提示

### 失敗處理
統計不足時顯示：
- 資料不足
- 缺少規格
- 缺少座標映射
- 批次不可用

不可輸出虛構統計值。

## T10 DPI 視覺驗證
必測：
- 100%
- 125%
- 150%

若可行再測：
- 175%

### 檢查
- sidebar
- tab label
- table header
- chart canvas
- button label
- form field
- widget overlap
- scroll behavior

### 輸出
每個主要頁面需標示：
- pass / fail
- clipping
- overlap
- misalignment

### 失敗處理
優先調整：
- layout policy
- size policy
- stretch factor
- min size

避免硬編碼座標。

## T11 SPC 統計語義驗證
### 必須檢查
- 控制圖語義
- 分布圖語義
- 能力分析語義
- 群組比較語義
- 空間分析語義
- Pareto 分類語義
- 常態分析語義

### 特別規則
- capability ≠ distribution
- 空間異常 ≠ 自動根因
- 群組差異 ≠ 製程穩定性結論
- normality ≠ 品質良好

### 驗證
建立 chart-by-chart checklist。

### 失敗處理
若語義模糊：
- 更名
- 加 subtitle
- 移除誤導性 badge

## T12 效能檢查
預期資料量：
- 10k
- 50k
- 100k+

### 檢查項目
- 切頁速度
- filter 更新速度
- chart refresh
- table update
- 空間圖生成

### 失敗處理
- calculation 移出 UI thread
- cache filtered data
- 避免重複重繪
- 限制不必要 redraw

## T13 最終整合報告
必須輸出：

### A 完成任務
列出完成的 milestone。

### B 修改檔案
列出檔案與用途。

### C UI 行為摘要
哪些頁面、哪些圖表、哪些條件控制已可運作。

### D 資料契約摘要
- 座標檔支援欄位
- 量測記錄支援欄位
- 映射規則
- 關聯鍵
- 缺欄位處理

### E DPI 驗證摘要
100% / 125% / 150% 結果。

### F SPC 語義摘要
哪些圖表已驗證、哪些仍待確認。

### G 剩餘問題
誠實列出未完成項目與依賴缺口。

# 6 驗收標準

必須同時滿足：

## UI
- 符合截圖風格與三區架構
- 主要頁面可切換
- 空狀態與錯誤狀態清楚

## 功能
- navigation 正常
- 表單正常
- table 正常
- chart tabs 正常
- 欄位映射正常
- 座標 / 量測關聯可驗證

## DPI
- 多縮放比例可用
- 無重大 clipping / overlap

## SPC
- label 正確
- 無誤導統計
- 無偽 capability

## 資料契約
- 可辨識必要欄位
- 可提示缺欄位
- 可量化關聯成功率

## 維護性
- 模組化
- 無大面積重複程式
- page / parser / chart 職責清楚

# 7 失敗處理邏輯

## Level 1 UI 問題
例如：
- layout bug
- label 裁切
- tab 切換異常

處理：
- local fix
- 重新驗證頁面

## Level 2 整合問題
例如：
- signal 未接
- page registry 缺失
- chart adapter mismatch

處理：
- 隔離依賴
- 回報缺失 class / function
- 以安全 placeholder 取代

## Level 3 資料契約問題
例如：
- schema 缺欄位
- 欄位名稱不一致
- 關聯鍵不存在

處理：
- 停止相關分析輸出
- 顯示明確資料缺口
- 保留 metadata 與預覽

## Level 4 統計邏輯問題
例如：
- Cp/Cpk 算法錯誤
- subgroup 假設錯誤
- control limit 使用錯誤

處理：
- 阻止錯誤圖表輸出
- 標示待統計驗證
- 不可用視覺假象替代正確計算

# 8 UI / 程式實作規則

- 優先使用 QWidget 模組化
- 使用 layout manager，不用固定座標
- QSplitter 僅在有助 resize 時使用
- page 與 page 間保持隔離
- parser、mapping、analysis、UI 分層
- 保持中文 UI 術語
- 維持工業工程軟體風格，不做消費型美化優先

# 9 Agent 輸出格式

每輪執行結果必須用以下格式：

## Plan
本輪要改什麼。

## Patch
修改哪些檔案 / class / widget。

## Verify
做了哪些驗證，包含 DPI-aware 檢查。

## Risks
目前仍有什麼風險。

## Next
下一輪應完成什麼。

# 10 視覺基準與資料基準提醒

使用者提供的截圖不是參考圖，而是 **正式 UI 視覺基準**。  
使用者提供的座標檔與量測記錄檔不是附加資料，而是 **正式資料契約驗證樣本**。

Agent 必須同時依據：
- UI 截圖
- 座標檔
- 量測記錄檔

來完成：
- 畫面
- 資料映射
- 關聯邏輯
- 分析功能
- 失敗處理

# 11 最終指示

這是 **工程 UI + 資料契約整合任務**，不是單純畫面重構。

不得：
- 任意 redesign
- 忽略資料欄位差異
- 假裝統計完成
- 假裝空間分析可用

必須：
- milestone 驗證
- DPI 驗證
- schema 驗證
- mapping 驗證
- join / relation 驗證
- SPC 語義驗證
- 明確回報缺口
