# SPC Platform — 專案特定審查規則（code-audit 規則來源）

> **用途：** 本檔是 **SPC Platform** 專屬的 code-audit 規則來源。當在本工作區執行全域 `/code-audit` 時,
> 全域 skill 會偵測並讀取本檔,於通用 A–E 分類之外額外對照以下 P 規則。
> 架構：**PySide6 / Matplotlib 分析類桌面應用**。
>
> **單一真相來源：** P1（blockSignals 對稱性）的規則正文只在此檔,`qt-dynamic-parameter-selector` 技能連結回本檔,不另行重述。
> P3（三層 guard）的權威來源是 `.claude/skills/analytics-engine-contract/SKILL.md`,本檔只放指標。

每條違反規則的 finding 標記為對應類別（通常 **A** 或 **C**）。

---

## P1. PySide6 blockSignals 對稱性（→ A）

```python
# 正確：必須對稱，即使中途 return
self.combo.blockSignals(True)
try:
    self.combo.clear()
    self.combo.addItems(items)
finally:
    self.combo.blockSignals(False)

# 錯誤：中途 return 導致 blockSignals 永不解除
self.combo.blockSignals(True)
if not items:
    return          # ← blockSignals 未解除，後續所有 signal 全失效
self.combo.addItems(items)
self.combo.blockSignals(False)
```

**檢查：** 找所有 `blockSignals(True)`，確認每條執行路徑都有對應 `blockSignals(False)`。

---

## P2. QThread worker 清理（→ A）

```python
# 正確
self._worker = MyWorker(data, self)
self._worker.result_ready.connect(self._on_result)
self._worker.finished.connect(self._worker.deleteLater)  # ← 必須
self._worker.start()

# 錯誤：缺少 deleteLater，worker 物件永遠不釋放
self._worker.result_ready.connect(self._on_result)
self._worker.start()
```

**檢查：** 找所有 `QThread` 子類別的 `.start()`，確認有 `finished.connect(...deleteLater)`。

---

## P3. Analytics Engine guard pattern（→ A）

> **權威來源：** 三層 guard 的完整定義與範例見 `.claude/skills/analytics-engine-contract/SKILL.md`（「Standard Guard Pattern」段）。
> 本檔不重述,只在審查時對照該契約：每個 `compute_xxx()` 必須有「SPC validity → 必要參數 → 退化輸入」三層 guard,
> 且 `is_valid=False` 時 `data` 和 `statistics` 必須是 `{}`（不可有部分資料）。

---

## P4. Chart axis 管理（→ A）

```python
# 正確：figure.clear() 後必須重新賦值 self.ax
self.figure.clear()
self.ax = self.figure.add_subplot(111)   # ← 重新賦值
_apply_mpl_dark_style(self.figure, self.ax)

# 錯誤：figure.clear() 後仍使用舊的 self.ax（已失效）
self.figure.clear()
self.ax.set_title("...")   # ← RuntimeError 或靜默出圖錯誤
```

**多子圖模式：** `_draw_multi_feature()` 中必須先 `figure.clear()`，再 `add_subplot(1, N, i+1)`。

---

## P5. get_payload_slice 誤用（→ A）

```python
# 正確：只在單特徵模式使用
data = get_payload_slice(self._last_payload, chart_id)

# 錯誤：多特徵時使用 get_payload_slice（結構不匹配）
# 多特徵應走：
data = self._resolve_multi_feature_data(chart_id, self._display_features)
```

**檢查：** 找所有 `get_payload_slice` 呼叫，確認在多特徵路徑下不被使用。

---

## P6. _PARAM_KEY_FOR_CHART 映射完整性（→ C）

```python
# chart_analysis_page.py 中的映射表
_PARAM_KEY_FOR_CHART = {
    "imr":               "spc",
    "histogram_spec":    ("dist", "cap"),
    "boxplot":           "box",
    "normality":         "normality",
    # ... 所有 chart_id 必須在此列出
}
```

**檢查：** 找 `CHART_ORDER` 中的所有 chart_id，確認每個都有對應 key（或有明確的 fallback 邏輯）。

---

## P7. QFrame objectName（→ C）

以下 QFrame 必須設定 `setObjectName`，否則 QSS 選擇器無效：

| objectName | 用途 |
|---|---|
| `chartDashboardCard` | Dashboard 中每個圖表卡片 |
| `accordionArea` | 圖表選擇 accordion 外框 |
| `accordionGroup` | 每個 accordion 群組 |

```python
card.setObjectName("chartDashboardCard")   # 必要
```

---

## P8. canvas.draw() 遺漏（→ A）

每個 `draw_chart()` 或 `update_data()` 的所有執行路徑末端必須呼叫 `self.canvas.draw()`。

```python
# 正確：每個分支都呼叫 canvas.draw()
def draw_chart(self, data):
    if not data:
        self._show_placeholder("無資料")
        self.canvas.draw()    # ← 必須
        return
    self._draw_content(data)
    self.canvas.draw()        # ← 必須

# 錯誤：早返回路徑缺少 canvas.draw()（圖表不更新）
def draw_chart(self, data):
    if not data:
        return                # ← 漏掉 canvas.draw()
    self._draw_content(data)
    self.canvas.draw()
```

---

## P9. 效能回歸基準（→ A）

判定效能回歸前,固定環境連續量測 ≥5 次,以 median + 變異係數(CoV)區分主機噪音與真實回歸;確認後才重錄 baseline(噪音)或開修復任務(回歸)。

```python
import statistics
times = [measure_op() for _ in range(5)]
med = statistics.median(times)
cov = statistics.pstdev(times) / med if med else 0.0
# cov 偏高 → 視為噪音,附審計註記後重錄 baseline;
# 否則 median 超門檻 → 視為回歸,建立修復任務(明確 module / metric)。
```

---

## P10. Windows 啟動環境（→ A）

Windows host 啟動先 `ensure_home_env()`(補 `HOME` / `USERPROFILE`),避免 `_overlapped` import 失敗 / `WinError 10106`。驗證:`check_launch` + `import _overlapped` 不報錯。

```python
import os
def ensure_home_env():
    if not os.environ.get("HOME"):
        os.environ["HOME"] = os.environ.get("USERPROFILE", "")
```
