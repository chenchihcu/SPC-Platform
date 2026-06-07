# Project Rules（`.cursor/rules`）

本目錄規則之格式與語意以 **Cursor 官方文件** 為準（以下連結請以官網最新版為準）：

- **Rules（總覽）**：<https://cursor.com/docs/context/rules>

---

## 1. 官方：規則類型與 frontmatter

依官方說明，規則為 Markdown（支援 **`.md` / `.mdc`**）；**`.mdc`** 可含 YAML frontmatter，以 `description`、`globs`、`alwaysApply` 控制套用方式；亦可由 **類型下拉選單** 變更上述屬性。

| 類型（UI） | 行為（官方敘述） |
|------------|------------------|
| **Always Apply** | `alwaysApply: true` — 套用至**每次對話**（every chat session）。 |
| **Apply Intelligently** | `alwaysApply: false` — Agent 依 **`description`** 判斷是否相關。 |
| **Apply to Specific Files** | 使用 **`globs`** — 符合檔案模式時套用。 |
| **Apply Manually** | 在對話中以 **`@`-mention** 規則名稱手動套用。 |

**Intelligent 必備**：官方 FAQ 指出，若規則未套用，且類型為 **Apply Intelligently**，請確認已定義 **`description`**。

---

## 2. 官方：規則優先順序（衝突時）

官方說明 **Team Rules → Project Rules → User Rules** 之順序；**較前項**在指引衝突時優先（earlier sources take precedence）。

本 repo 以 **Project Rules**（本目錄）為主；若帳號另有 **User Rules**，以官方優先順序為準。

---

## 3. 官方：適用哪些 Cursor 功能（避免誤會）

依官方 **FAQ**（同頁 *Why isn't my rule being applied?*）：

- **Rules 不影響 Cursor Tab** 等部分 AI 功能之敘述（*Rules do not impact Cursor Tab or other AI features*）。
- **User Rules** 不套用於 **Inline Edit（Cmd/Ctrl+K）**，僅適用於 **Agent（Chat）**。

**含義**：閘門／流程類 Project Rules 主要約束 **Agent 對話式編修**；若期望 **Tab 連字** 也遵守同一套，官方文件未保證與 Project Rules 同步，請勿假設。

---

## 4. 官方：`AGENTS.md`、`.cursorrules`、Project Rules

| 機制 | 官方定位（摘錄） |
|------|------------------|
| **`AGENTS.md`** | 於專案根目錄或子目錄放置之**純 Markdown** 說明；子目錄可**巢狀**，較深路徑之指示可覆蓋上層。與 Project Rules **並存**；適合較直述之指令。 |
| **`.cursorrules`（根目錄）** | **Legacy**，仍支援但**將淘汰**；建議新設定改為 **Project Rules** 或 **`AGENTS.md`**。 |
| **`.cursor/rules/*.mdc`** | **Project Rules**，具 frontmatter，可細控套用條件。 |

本 repo：**根目錄 `AGENTS.md`**（專案強制規則與 SPC／UI 細則）＋ **`.cursor/rules/*.mdc`**（路徑／情境分流），與官方「並存」用法一致；**未使用** `.cursorrules`。

---

## 5. 本 repo 之取捨（效率 vs 覆蓋率）

- **`cross-platform-repo-baseline.mdc`**：`alwaysApply: true` — 跨平台（UTF-8/LF）、`AGENTS.md` 權威、驗證指令與 `pyproject.toml` 工具設定入口。
- **`agent-residence-minimal.mdc`**：`alwaysApply: false` + 完整 **`description`**（符合 Intelligent 與 FAQ 要求）。若須**每次對話必載入**，請於 Cursor **Rules** 將該條設為 **Always Apply**（`alwaysApply: true`）。
- **`backend-python-quality.mdc`**：`globs` 涵蓋 `app/`、`tests/`、`pyproject.toml` — Python 後端與品質工具約束。
- **`frontend-react-vite-prototype.mdc`**：`globs` 涵蓋 `Outputs/industrial-data-setup-ui/` — React/Vite 原型之 TS strict、ESLint、Vitest/MSW。
- **其餘 `*.mdc`**：以 **`globs`** 限定 `app/ui`、`app/charts` 等，對應 **Apply to Specific Files**，減少無關檔案編輯時之上下文。

---

## 6. 維護

- 規則與行為以 **目前 Cursor 版本** 及 **官方文件** 為準；若 Cursor 更新 UI／語意，請先對照 [Rules](https://cursor.com/docs/context/rules) 再改本目錄。
- **Intelligent 未套用**：先查 **description**、再查 **globs** 是否與當前檔案一致（FAQ）。

---

## 7. 修訂紀錄

| 日期 | 摘要 |
|------|------|
| 2026-03-26 | 初版：四種類型、本 repo 取捨。 |
| 2026-03-26 | 對齊官方文件：優先順序（Team / Project / User）、FAQ（Tab／Inline Edit／Agent）、`AGENTS.md`、`.cursorrules` 遺留、FAQ 排查。 |
| 2026-04-04 | 提升 **Apply Intelligently** 命中率：各 `.mdc` 的 `description` 補強中英關鍵字與常見觸發詞；略擴 `globs`（例：`app/ui/pages/**`、`report_service`、workflow／`SPC_RULES` 相關 docs）；修正 ai-planning 對 workflow 路徑之涵蓋（以 `docs/**/*workflow*.md` 對齊 `docs/specs/`）。 |
| 2026-04-04 | 新增 **跨平台基線**（`cross-platform-repo-baseline.mdc`）、**後端**（`backend-python-quality.mdc`）、**前端原型**（`frontend-react-vite-prototype.mdc`）；根目錄 **`pyproject.toml`** 統一 `[tool.ruff]` / `[tool.mypy]` / `[tool.pytest.ini_options]`；**`.editorconfig`**、**`.gitattributes`**；移除獨立 `ruff.toml`；CI 依賴清單內之 ruff/mypy。 |
