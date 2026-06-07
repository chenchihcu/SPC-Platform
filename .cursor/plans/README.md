# `.cursor/plans` — 迭代計畫檔說明

本目錄存放 **實作／重構計畫**（Markdown）。計畫 **不** 凌駕於主分支程式與 `docs/` 規格；若內容與現況不符，請依 `docs/plans/document_alignment_patch_plan.md` 標示 `needs-update` 或 `[ARCHIVED]`，並補上程式證據。

**與問題解決工作流的關係**：修 bug 或跨模組變更時，**先**對照 **`docs/specs/issue_resolution_workflow.md`**（步驟 1–7 與閘門），再依下方範本撰寫計畫；避免只寫計畫卻跳過根因／橫向搜尋。

## 必填紀律

撰寫或修訂任何計畫前，請閱讀並遵守：

- **`docs/plans/ai_change_and_planning_discipline.md`** — 計畫擬定前 Preflight、根因分析、關聯模組與爆炸半徑。
- **`docs/specs/spec_maintenance_and_alignment.md`** — 何時必須更新規格、計畫生命週期。
- **`docs/governance/GLOBAL_PLAN_FRAMEWORK_V2_2.md`** — 全域（跨專案）計畫框架 v2.2，永久單人模型與 Gate A~F pass/fail criteria。

## 標準模板（直接複製）

- **Canonical template**: `docs/templates/PLAN.md`
- 若為新任務，優先直接複製 `docs/templates/PLAN.md` 建立計畫檔，再填入實際內容。
- 使用順序（固定）：
  1. 先填 `triage_route / triage_confidence / triage_triggers / triage_evidence / triage_decision_note`
  2. 再依 triage 結果選擇 `L1 Quick Path` 或 `Full Path`
  3. 若有不確定，一律升級 `Full Path`
- 若為既有計畫補強，至少補齊：
  - `Code Change Matrix`
  - `AGENTS Compliance Gate`
  - `Verification Matrix`
  - `Gate A~F Self-review`

### 最小示例（AI 分流）

```markdown
triage_route: Full
triage_confidence: 0.91
triage_triggers:
  - impact_type includes ui
triage_evidence:
  - app/ui/pages/<target>.py
  - docs/specs/ui_design_spec.md
triage_decision_note: Hard trigger matched (ui), route forced to Full.
```

## 舊版簡化骨架（歷史相容，非首選）

```markdown
---
status: draft
evidence_date: YYYY-MM-DD
related_specs:
  - docs/specs/ui_design_spec.md
---

# 計畫標題

## 1. 目的與非目標（Non-goals）

## 2. 現況盤點（Preflight 證據）
- 已讀／已 grep 之模組與路徑：
- 與本計畫相關之實際行為（一句話＋檔案參照）：

## 3. 依賴與影響範圍
- 上游（資料／設定）：
- 下游（UI／報表／測試）：

## 4. 方案與步驟

## 5. 驗收與可觀測條件
- （禁止只寫「無捲軸」而無解析度／DPI／容器定義）

## 6. 規格與文件更新清單
- [ ] 需更新之 `docs/` 或 `docs/governance/SPC_RULES.md`：

## 7. 根因分析（若為修 bug／技術債）
- 觀察 → 根因 → 對策 → 驗證
```

## 本 repo 已知對齊狀態（見 `docs/reports/document_alignment_report.md`）

| 計畫檔 | 建議狀態 |
|--------|-----------|
| `adaptive-toasting-ladybug.md` | `ARCHIVED`（與 JSON／UI 現況不符時） |
| `data_setup_流程版面重排_*.plan.md` | `needs-update`（scroll 順序敘述需對照 `data_setup_page.py`） |
| `data-setup-single-page-2k-layout_*.plan.md` | `needs-update`（2K／捲軸驗收需可測） |
| `limit-preview-to-three-lines_*.plan.md` 等 | 對照程式後可標 `ok` |

**注意**：若本機未建立上列檔名，仍以 `docs/reports/document_alignment_report.md` 為準；新增計畫時勿重複已歸檔前提（例如未經遷移即宣稱 SQLite）。
