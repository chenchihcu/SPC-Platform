# 例外與 `pass` 審計（限定範圍）

**日期**：2026-04-05  
**依據**：[AGENTS.md](../../AGENTS.md) — 分析／匯入／報告路徑避免空 `except`／空 `pass`；本清單為靜態掃描與人工對照，非全面 `app/` 審計。

## 掃描範圍

| 區域 | 路徑 |
|------|------|
| 分析引擎 | `app/analytics/*.py` |
| 報告服務 | `app/services/report_*.py` |
| 匯入管線 | `app/services/import_service.py`、`app/data/loaders/*.py` |

## 允許／已對照（無需立即修改）

- **`app/analytics`**：`except` 多為明確型別元組（如 `TypeError, ValueError`）或數值後備（`bivariate_outlier_engine` 在無 `scipy` 時使用文件化常數閾值，非靜默失敗）。未發現 `except:` 裸捕或 `except Exception: pass` 型態。
- **`app/data/loaders/{measurement,coordinate}_loader.py`**：`UnicodeDecodeError`／`OSError`／`ValueError` 等具名例外，並透過 meta／錯誤字串回報。
- **`app/services/import_service.py`**：`DataLoaderWorker.run` 以具名例外集合捕捉，並 `finished.emit(False, msg)` 與 store meta 標記失敗。
- **`report_service.py` / `report_diagnostics.py` / `report_exec_summary.py`**：失敗路徑多搭配 `logger.exception` 或 `logger.debug(..., exc_info=True)`。
- **`report_diagnostics.build_pptx_diagnostics`**：頂層 `ImportError` 時回傳空診斷列表（可選模組不存在時之降級行為）。
- **`report_context.build_report_context`**：`ImportError` 時 `logger.debug(..., exc_info=True)`。

## 待改／建議追蹤（低優先，非阻擋）

| 檔案 | 位置 | 說明 | 建議 |
|------|------|------|------|
| `app/services/report_actions.py` | `collect_pptx_actions` 內 `except ImportError: pass` | 當 `failure_mode_library` 不可匯入時，略過 failure-mode 建議但仍可走 `optimization_suggestions`；行為正確但**無日誌**。 | 可選：改為 `logger.debug(..., exc_info=True)` 一次，便於診斷「為何沒有 failure-mode 動作」。 |

## 第二階段（本文件範圍外）

圖表渲染、通用 UI、`chart_render`／`session_store` 等之 `pass` 與寬泛 `except` 依 [AGENTS.md](../../AGENTS.md) 可另排迭代審計。

## 關聯

- 計畫來源：全專案結果彙整與修正提案（P2 審計項）。
- CI／`release_check` 政策見 [docs/decision-log.md](../decision-log.md) 2026-04-05「CI：`release_check --with-release-ext`」條目。
