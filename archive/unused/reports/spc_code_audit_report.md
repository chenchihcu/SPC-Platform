# SPC Code Audit 報告

依 **spc-code-audit** 技能執行審計；**本次覆核** 已重新執行基準測試、掃描器與 `app/` 手動檢查。

## 1. 前置與基準

- **規範**：已讀取 `docs/governance/AGENTS.md`、`docs/governance/SPC_RULES.md`。所有 triage 與修補均遵守 Safe Change Rules（不變更 SPC 公式、不混雜問題類型）。
- **文件**：已讀取 `docs/reference/platform_overview.md`、`docs/specs/project_architecture.md`。專案內無 `docs/outstanding-items.md`。
- **品質掃描**：自 skill 目錄執行 `python scripts/scan_repo_quality.py <repo-root>`。掃描器預設掃 `src/`、`tests/` 與 `docs/**/*.md` 等；本專案主體在 **`app/`**，故 **另以 grep 對 `app/`** 做 broad-except 與圖表路徑檢查。
  - **注意**：若本報告曾含 Python importlib 之「無原始碼檔載入器」類別全名，掃描器會將其誤判為 bytecode-coupling；本文件已改寫描述，避免誤判。
- **pytest 基準**：`pytest -q` **177 passed**（本次覆核）。

---

## 2. Triage 結果（依技能優先序）

| 優先級 | 項目 | 狀態 |
|--------|------|------|
| 1 | **Bytecode / runtime coupling** | 未發現：根目錄無 `.pyc`、無 checked-in bytecode；程式碼無依賴無原始碼打包載入。 |
| 2 | **Broad `except Exception`** | 見 §3：`app/` 內目前 **17 處**（grep 結果）；多數有 log、回傳結構化錯誤或 UI 可見訊息。 |
| 3 | **編碼損壞 (private-use / replacement codepoints)** | 掃描器僅掃 `src/**/*.py`；對 `app/` 未執行自動 codepoint 掃描；手動檢視無明顯問題。 |
| 4 | **圖表靜默 skip** | `chart_render.render_chart_to_png_bytes` 遇例外 **log 後 re-raise**。`report_service` 綜合報告路徑對單圖失敗採 **降級輸出**（見 §3）。 |
| 5 | **根目錄 temp / decompiled** | 未發現需隔離之 `tmp` / `decompiled` / `main_window*.pyc`。 |
| 6 | **Packaging / README 與執行期不一致** | README 啟動為 `python main.py`，與結構一致。 |

---

## 3. Broad `except Exception` 盤點（app/，本次 grep）

| 檔案 | 行號（約） | 行為 | 評估 |
|------|------------|------|------|
| `app/services/chart_render.py` | 139 | `logger.exception` 後 **raise** | 符合：渲染失敗傳給呼叫端。 |
| `app/services/report_service.py` | 84, 103 | `logger.exception` + HTML 錯誤段落 | 符合：使用者可見。 |
| `app/services/report_service.py` | 279 | 單圖失敗 → `img_bytes=None` + 「（此條件下無法產出圖表）」 | 可接受：綜合報告降級。 |
| `app/services/report_service.py` | 308, 342, 364 | `logger.exception` + `return (False, str(e))` | 符合。 |
| `app/services/import_service.py` | 61 | 設定 store 錯誤 + `finished.emit(False, msg)` | 符合。 |
| `app/viewmodels/chart_analysis_viewmodel.py` | 280, 308 | 雙/三特徵預先計算失敗 → `logger.debug`，略過該組合 | **可接受但須知**：僅 debug，生產環境若 log level 過高可能不易追蹤；屬可選收斂例外型別之處。 |
| `app/viewmodels/chart_analysis_viewmodel.py` | 371 | `compute_analysis_payload` 外層 → `logger.exception` + `return (None, 錯誤字串)` | 符合：`analyze()` 經 `error_occurred.emit(err)` 傳 UI。 |
| `app/ui/pages/chart_analysis_page.py` | 84 | 背景 worker 失敗 → emit 預設「分析明細」 | 可接受：避免 UI 崩潰。 |
| `app/ui/pages/chart_analysis_page.py` | 740 | Dashboard `update_data` 失敗 → `logger.warning` | 符合：單卡失敗不中斷整板。 |
| `app/ui/pages/data_upload_page.py` | 87 | 預覽讀檔失敗 → 路徑列顯示「讀取失敗」 | 符合：仍會 `meas_uploaded.emit`；使用者可知預覽失敗。 |
| `app/charts/density_chart.py` | 22 | `cbar.remove()` 失敗 → **pass** | **技術債**：Matplotlib 清理；建議改為具體例外或一行註解說明「軸已釋放可忽略」（符合 AGENTS「非靜默 pass」精神）。 |
| `app/charts/pareto_chart.py` | 21 | `_ax2.remove()` 失敗 → **pass** | 同上。 |
| `app/analytics/cusum_engine.py` | 93 | `board_ids.reindex` 失敗 → `board_vals = None` | 可接受：降級為無板邊界偵測；可選縮小為 `ValueError` 等。 |
| `app/analytics/normality_engine.py` | 70 | 回傳 `metadata.is_valid=False` + `error` | 符合。 |
| `app/analytics/optimization_suggestions.py` | 25, 43 | `logger.debug`，部分清單 | 可接受：best-effort。 |

---

## 4. 先前修補摘要（仍有效）

- **chart_render.py**：渲染例外 **log 後 re-raise**。
- **mpl_font_config.py**：字型列舉改為 `except (OSError, RuntimeError)`。
- **測試與 API**：與現有 Engine / ViewModel 對齊。

---

## 5. 驗證指令

```bash
cd "c:\Users\user\Documents\SPC Platform"
python -m pytest -q
```

結果（本次覆核）：**177 passed**。

掃描器（skill 內建）對本 repo：`OK|no-findings`（在稽核文件避免觸發誤判字串後）。

---

## 6. 未改動與保留風險

- **SPC / Cp / Cpk / yield / spec-limit / pass-fail**：未改動計算與判斷邏輯。
- **report_service 綜合報告**：單圖失敗仍產出報告並標示無法產圖；若需 fail-fast 可改為 re-raise。
- **registry 類模組**：檔案錯誤時仍可能回傳空清單；若需向 UI 表面化錯誤可後續擴充。

---

## 7. 後續建議

1. **可選**：`density_chart.py` / `pareto_chart.py` 的 `clear()` 內 `except …: pass` 改為具體例外或加註解（小範圍、單一問題類型）。
2. **可選**：`chart_analysis_viewmodel` 中 dual/triple 預算失敗改為 `logger.warning` 或收斂例外型別，便於追蹤。
3. 將 `scan_repo_quality.py` 擴充為掃描 `app/**/*.py`，或於 CI 定期執行並比對本報告 §3。
