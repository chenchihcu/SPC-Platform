# AI 代理結構化輸出範本（複製即用）

非 **L1** 時，先填下方區塊再給程式 diff。可貼在 PR 描述或對話框。

```markdown
## Tier
- [ ] L1（單檔 typo／無行為變更） — 一句話理由：……
- [ ] L2 或 不確定 → 依 L2

## 1 Scope
- in-scope：……
- non-goals：……

## 2 Evidence
- …（檔案路徑、函式或 log 行）

## 3 RCA
- 觀察：……
- 根因：……
- 對策對應根因：（是／否，一句）

## 4 Blast
- 上游／下游：……
- 已 grep 之 pattern／符號：……
- 圖表語意單一來源：（不適用／已查）

## 5 Verify
- `python -m pytest -q`：（通過／子集 ……）
- 領域附表（若適用）：QSS 字型 §4.1／DPI／SPC 規格：……
```

完整閘門見 **`docs/specs/issue_resolution_workflow.md`**。
