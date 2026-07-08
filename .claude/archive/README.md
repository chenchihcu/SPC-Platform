# .claude/archive — 封存區

依「先盤點、再合併、再優化、最後移 archive、不硬刪」原則建立(2026-07-08 AI Skill 架構盤點)。

## 封存項目

### spc-validation-matrix-workspace/
- **原位置**:`.claude/skills/spc-validation-matrix-workspace/`(以 `git mv` 遷入,保留歷史)
- **封存原因**:非技能(整棵目錄無 SKILL.md),是建置 `spc-validation-matrix` 技能時的
  eval/測試執行產出(iteration-1 的 matrix.csv、SUMMARY.md、failures/*.json、
  exports/*.pptx+*.xlsx,ITERATION_1_SUMMARY.md 日期 2026-04-30)。
  放在 skills/ 會被誤認為第 7 個技能,且未列於全域 CLAUDE.md 索引。
- **對應新版 skill**:`.claude/skills/spc-validation-matrix/`(仍在原位,正常使用)
- **保留價值**:`iteration-1/BUG_FINDINGS.md` 記錄驗證器抓到的真實 bug,
  `ITERATION_1_SUMMARY.md` 是該技能的 eval 歷史證據——**建議長期保留這兩份**。
- **是否可永久刪除**:文件類(BUG_FINDINGS.md、各 SUMMARY.md)不建議刪;
  二進位測試產出(exports/*.pptx、*.xlsx、failures/*.json)經使用者確認後可刪。
