# 專案 UI 深度優化 — 經驗總結與預防指南

> 基於本次 PySide6/Qt 桌面應用完整重構過程的實際錯誤記錄，共計 127 項問題、1,289 次工具呼叫，歷時 2 個工作階段（2026-03-27 ～ 2026-03-28）。

---

## 一、Design Token 系統：從源頭杜絕硬編碼

### 發生了什麼

專案啟動時，顏色、間距、字型直接寫在 QSS、Matplotlib 調色盤、HTML 報表三處，且彼此獨立。本次掃描發現 **原始版本殘留 40+ 個裸 hex 色碼** 分散在 9 個檔案中，造成：

- 同一語意色（例如「停用狀態文字」）在不同位置用了三種不同的 hex 值
- 改一個顏色需要同時修改 3 個檔案，且容易遺漏
- Matplotlib 圖表色 和 Qt 介面色毫無關聯，視覺語言不一致

### 根本原因

Token 系統（`tokens.py`）建立初期只涵蓋 Qt QSS 用途，**圖表調色盤和 HTML 報表色從未納入**。

### 修正

- `tokens.py` 從 ~180 個 token 擴充到 256 個，新增：
  - `CHART_PALETTE_*`（14 個圖表顏色）
  - `RPT_*`（20 個 HTML 報表顏色）
  - 尺寸常數：`SCROLLBAR_WIDTH`、`CHECKBOX_INDICATOR_SIZE`、`QT_MAX_WIDGET_DIM` 等
- 全專案正則掃描驗證：`re.findall(r'"#[0-9A-Fa-f]{6}"', src)` 最終結果 = 0

### 預防規則

```
規則 T-1：Token First
任何新增的顏色、間距、字型大小，一律先加入 tokens.py，
禁止在任何其他檔案中出現裸 hex 或裸 pixel 數字。

規則 T-2：三層覆蓋（Qt QSS / Matplotlib / HTML）
建立 token 時必須同時考慮三個使用場景；
若三處語意相同，共用同一 token；若語意不同，分別命名前綴（CHART_*, RPT_*）。

規則 T-3：新功能 checklist
每次新增 UI 元件前，先確認所需 token 是否已存在；
若不存在，先在 tokens.py 定義再寫元件。
```

---

## 二、語意 Token 誤用：`TEXT_MUTED` ≠ `TEXT_DISABLED`

### 發生了什麼

所有 `:disabled` 狀態的 QSS 規則（共 6 處）均使用 `TEXT_MUTED`，而非 `TEXT_DISABLED`。

| Token | 語意 | 對應場景 |
|---|---|---|
| `TEXT_MUTED` | 次要資訊、說明文字 | placeholder、caption、輔助說明 |
| `TEXT_DISABLED` | 非互動元素 | `:disabled` 狀態的按鈕、輸入框、標籤 |

兩個 token 的色值不同（`TEXT_DISABLED` 更暗），混用導致「停用」和「次要」視覺上無法區分。

### 根本原因

初始設計時只有 `TEXT_MUTED`，`TEXT_DISABLED` 是後來新增的。新增後，舊有的 `:disabled` 規則未統一更新。

### 預防規則

```
規則 S-1：語意 vs 視覺
命名 token 時以「用途/語意」為準，而非色值深淺；
禁止用 "light/dark/grey" 命名語意 token，應用 "muted/disabled/secondary"。

規則 S-2：新增 token 後全掃描
每次新增語意 token，立即 grep 全專案，
確認所有舊有用法是否應遷移至新 token。
```

---

## 三、Qt QSS 的能力邊界

### 發生了什麼

`QComboBox::down-arrow` 寫了標準 CSS 三角形技法：

```css
width: 0; height: 0;
border-left: 4px solid transparent;
border-right: 4px solid transparent;
border-top: 6px solid #B0B8C1;
```

在瀏覽器中完美運作，但在 Qt 中 **渲染為純黑色填滿方塊**，因為 Qt QSS 不支援此技法。

### Qt QSS 已確認不支援的 CSS 特性

| CSS 特性 | Qt 行為 |
|---|---|
| `box-shadow` | 完全忽略 |
| `transition` / `animation` | 完全忽略 |
| `transform` | 完全忽略 |
| `outline` | 忽略（需用 `border` 模擬 focus ring）|
| `opacity` | 忽略（需用 `rgba()` 或 `QPalette`）|
| CSS border-trick triangle | 渲染為實心方塊 |
| `:not()` 複雜選擇器 | 部分版本不支援 |

### 修正

移除三角形 CSS，改為只設定尺寸，讓 Qt 平台繪製原生箭頭：

```css
QComboBox::down-arrow {
    width: 10px;
    height: 24px;
}
```

### 預防規則

```
規則 Q-1：Qt QSS 能力白名單思維
撰寫 QSS 時，預設「不支援」直到確認可用；
不要套用瀏覽器 CSS 技法，除非有 Qt 文件佐證。

規則 Q-2：視覺效果替代策略
- shadow → 改用 border + 深色背景色對比
- animation → 使用 QPropertyAnimation（Python side）
- triangle → 讓 Qt 原生繪製，或用圖片 resource
- focus ring → border: 2px solid ACCENT_PRIMARY（非 outline）
```

---

## 四、QPalette 與 QSS 雙軌制

### 發生了什麼

`apply_dark_theme()` 只呼叫 `app.setStyleSheet()`，未設定 `QPalette`。導致：

- 文字選取高亮使用系統預設藍色（與深色主題不符）
- Placeholder 文字顏色使用平台預設（在深色背景下幾乎不可見）
- 停用元素的顏色在 native rendering path 上無法被 QSS 覆蓋

### 根本原因

Qt 有兩套平行的外觀系統：QSS 處理「可見元件外觀」，QPalette 處理「Qt 內部渲染路徑、accessibility API、選取狀態」。兩者必須同時設定才能完整覆蓋。

### 修正

新增 `_build_app_palette()` 設定 12 個 Color Role + 5 個 Disabled group override，並在 `apply_dark_theme()` 中優先呼叫。

### 預防規則

```
規則 P-1：主題應用雙步驟
任何深色主題應用，標準流程為：
  1. app.setPalette(build_palette())   ← 先設 QPalette
  2. app.setStyleSheet(get_qss())      ← 再覆蓋 QSS

規則 P-2：QPalette 必蓋清單
Window / WindowText / Base / AlternateBase / Text /
Button / ButtonText / Highlight / HighlightedText /
ToolTipBase / ToolTipText / PlaceholderText
以及 Disabled group：WindowText / Text / ButtonText / Button / Base
```

---

## 五、互動狀態完整性：每個控件必須有完整的狀態矩陣

### 發生了什麼

本次掃描發現多個控件缺少部分互動狀態的 QSS 規則：

- `QPushButton#navStepBtn` 有 `:hover`，但 `:focus` border 只有 1px（全站其他控件為 2px）
- `QTextEdit` 缺少 `:disabled` 規則
- `QTabBar::tab` 缺少 `:disabled` 規則
- `#sidebarToggleBtn`、`#sidebarMinimalNextBtn` 缺少 `:hover` / `:pressed`
- `QCheckBox::indicator` 缺少 `:focus` 狀態的 focus ring

### 預防規則

```
規則 I-1：控件狀態矩陣（每個互動控件必須完整定義）

| 狀態 | 所有 QPushButton | 所有輸入框 | 所有選擇控件 |
|------|----------------|-----------|------------|
| default | ✓ | ✓ | ✓ |
| :hover | ✓ | ✓ | ✓ |
| :focus | ✓（2px border）| ✓（2px border）| ✓（indicator focus）|
| :disabled | ✓ | ✓ | ✓ |
| :pressed | ✓ | — | ✓ |
| :checked | ✓（如適用）| — | ✓ |

規則 I-2：Focus ring 一致性
全站 focus ring 統一為 2px solid ACCENT_PRIMARY；
禁止單一控件使用 1px（視覺不一致）。

規則 I-3：新增控件 checklist
每次新增自訂控件（尤其是帶 objectName 或 property 的），
必須在 dark_stylesheet.py 中補齊完整狀態矩陣後才算完成。
```

---

## 六、Python f-string 中的邏輯陷阱

### 發生了什麼

```python
# 原始錯誤寫法
f"background: {SURFACE_HOVER_SUBTLE or SURFACE_HOVER};"
```

意圖：優先用 `SURFACE_HOVER_SUBTLE`，若未定義則 fallback 到 `SURFACE_HOVER`。

實際行為：Python `or` 運算符對非空字串永遠返回左邊操作數（因為非空字串為 truthy），`SURFACE_HOVER` **從未被使用**，且這段邏輯在靜態分析中也不會報錯。

### 修正

```python
# 正確寫法
f"background: {SURFACE_HOVER_SUBTLE};"
```

若確實需要 fallback：

```python
_hover = SURFACE_HOVER_SUBTLE if SURFACE_HOVER_SUBTLE else SURFACE_HOVER
f"background: {_hover};"
```

### 預防規則

```
規則 F-1：CSS 生成 f-string 中禁止使用 or 邏輯
f-string 的 {} 內部只放 token 名稱或簡單算術；
條件邏輯一律在 f-string 外部用變數處理。

規則 F-2：Token 定義即保證
若 token 已在 tokens.py 中定義，則不需要 fallback；
若 token 有可能未定義，應在 tokens.py 加上預設值，而不是在使用點寫 or。
```

---

## 七、魔法數字（Magic Numbers）的清零策略

### 發生了什麼

全專案發現的魔法數字（直接寫在 Python 邏輯中的裸數字）：

```python
# 出現在多個檔案中
setMaximumWidth(16777215)   # Qt 最大值，無任何說明
setVerticalSpacing(CONTROL_FORM_ROW_SPACING - 2)  # 為什麼減 2？
RAIL_WIDTH_COLLAPSED - 8    # 8 是什麼？
```

### 修正

```python
# tokens.py
QT_MAX_WIDGET_DIM = 16_777_215      # Qt's QWIDGETSIZE_MAX
FORM_GRID_ROW_SPACING = 6           # 明確語意
RAIL_COLLAPSED_BTN_MARGIN = 8       # 命名 margin

# 使用端
setMaximumWidth(QT_MAX_WIDGET_DIM)
setVerticalSpacing(FORM_GRID_ROW_SPACING)
RAIL_WIDTH_COLLAPSED - RAIL_COLLAPSED_BTN_MARGIN
```

### 預防規則

```
規則 M-1：所有 pixel 值進 tokens.py
即使只用一次，若該數字有特定意義（間距、邊距、最大值），
必須命名後進 tokens.py。

規則 M-2：-2、-4 等偏移值的警戒
任何「token - 小數字」的寫法，必須說明理由（comment 或命名）；
若理由成立，將結果本身命名為 token。
```

---

## 八、診斷流程的標準化

### 本次使用的有效診斷工具

本次 382 次診斷掃描命令，最有效的幾個模式：

```bash
# 1. 裸 hex 掃描（最高優先）
python3 -c "
import re, os
for root, _, files in os.walk('app'):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            src = open(path).read()
            hits = re.findall(r'\"#[0-9A-Fa-f]{6}\"', src)
            if hits: print(path, hits)
"

# 2. 魔法數字掃描
grep -rn 'setMinimumWidth([0-9]\+)' app/

# 3. CSS 語法驗證（無 display server 時）
python3 -c "import ast; ast.parse(open('app/ui/theme/dark_stylesheet.py').read()); print('OK')"

# 4. 重複 CSS 規則偵測
python3 -c "
import re
css = open('/tmp/generated.css').read()
selectors = re.findall(r'^[^{]+(?=\s*\{)', css, re.MULTILINE)
from collections import Counter
for s, c in Counter(s.strip() for s in selectors).items():
    if c > 1: print(c, repr(s))
"
```

### 預防規則

```
規則 D-1：每個 Sprint 的 UI 品質門檻
每次功能完成後，執行「裸 hex 掃描」和「魔法數字掃描」，
結果必須為 0 才算 done。

規則 D-2：AST 驗證取代肉眼 review
有 Python 程式碼生成 CSS 的場景，必須用 ast.parse() 驗證語法；
不依賴「看起來沒問題」。

規則 D-3：控件狀態矩陣自動檢查
建立腳本確認每個 QPushButton objectName 在 QSS 中都有
:hover / :focus / :disabled 三個規則；否則 CI 警告。
```

---

## 九、佈局設計的關鍵教訓

### 發生了什麼

「圖表選單從直式改橫式」和「診斷頁面移除捲軸改一頁式」兩個需求，反映出一個共同問題：**佈局決策在初期沒有被文件化**，導致後期改動成本高。

具體問題：
- 診斷頁面原始設計是垂直 scroll，重構為橫向無捲軸需要重寫整個 layout 邏輯
- 圖表選單的 grouping 邏輯依賴語意（SMT SPI 業務知識），與純 UI 分離不清

### 預防規則

```
規則 L-1：佈局決策記錄
每個主要頁面建立時，在 docstring 或 comments 中記錄：
  - 主要佈局方向（水平/垂直）
  - 是否允許捲軸（若不允許，說明替代方案）
  - 項目分組邏輯的業務依據

規則 L-2：業務分組與 UI 分離
選單的 grouping 標籤（如「趨勢監控」「能力分析」）來自業務定義，
應集中在 constants.py 或 config，不應硬編碼在 UI 元件中。
```

---

## 十、整體架構層面的反思

### Token 系統的正確演進路徑

```
錯誤路徑（本專案實際走過的）：
  先寫 UI → 事後提取 token → 發現 token 不夠 → 追加 → 漏網之魚持續存在

正確路徑（下次應執行）：
  先定義 token 系統（含圖表、報表） → 再寫 UI → 強制 lint 檢查裸值
```

### 主題系統的正確架構

```
正確的主題應用順序：
  1. tokens.py          → 單一真相來源（數值定義）
  2. dark_stylesheet.py → Qt QSS 生成（引用 tokens）
  3. __init__.py        → 應用入口（QPalette + QSS 雙設定）
  4. base_chart.py      → Matplotlib 調色盤（引用 CHART_PALETTE_* tokens）
  5. report_service.py  → HTML 報表（引用 RPT_* tokens）

任何新的視覺輸出渠道（例如 PDF 匯出、截圖水印）加入時，
必須新增對應前綴的 tokens，不得直接寫裸值。
```

### 可複用到其他專案的 Checklist

```markdown
## Qt 深色主題專案啟動 Checklist

### 架構
- [ ] tokens.py 建立，涵蓋 Qt / Matplotlib / HTML 三個渠道
- [ ] dark_stylesheet.py 使用 f-string 引用 tokens，零裸 hex
- [ ] apply_theme() 同時設定 QPalette + QSS
- [ ] CI 中加入裸 hex 掃描腳本

### 每個新控件
- [ ] 所需 token 已在 tokens.py 定義
- [ ] QSS 中有完整 5 狀態矩陣（default/hover/focus/disabled/pressed）
- [ ] Focus ring 統一為 2px solid ACCENT_PRIMARY
- [ ] 無魔法數字

### 發佈前
- [ ] 裸 hex 掃描結果 = 0
- [ ] 魔法數字掃描結果 = 0（或全部有命名）
- [ ] AST 驗證 dark_stylesheet.py 語法無誤
- [ ] 重複 CSS 規則確認為「刻意的特異性覆蓋」而非意外複製
```

---

## 總結

本次工作階段的 127 項問題，若按根本原因分類：

| 根本原因 | 問題數 | 最高影響 |
|---|---|---|
| Token 未涵蓋所有渠道（圖表/報表） | ~35 | 視覺一致性破壞 |
| 控件狀態矩陣不完整 | ~30 | 互動回饋缺失 |
| Qt QSS 能力邊界理解不足 | ~15 | 渲染錯誤（下拉箭頭）|
| 魔法數字 | ~20 | 可維護性差 |
| 語意 token 誤用 | ~10 | 停用/次要視覺混淆 |
| QPalette 未設定 | ~7 | 選取/placeholder 顯示異常 |
| f-string 邏輯錯誤 | ~1 | 靜默錯誤難發現 |
| 其他佈局/命名問題 | ~9 | — |

**核心教訓一句話：在 Qt 深色主題專案中，正確性不是「看起來像」，而是「token 來源可追溯、狀態矩陣完整、QPalette 與 QSS 雙設定、zero raw hex/magic number」。**
