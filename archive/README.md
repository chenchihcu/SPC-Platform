# Archive 說明

`archive/unused/` 用於保存目前未被專案文字內容引用（reference count = 0）的歷史文件。

`archive/outputs/` 用於保存已從 `Outputs/` 收斂的歷史稽核報告與索引（例如 `final_audit_index.md`）。

此區文件**不代表永遠無效**，僅代表在目前版本中未被引用。若後續需要回復：

1. 從 `archive/unused/` 搬回對應功能資料夾（`docs/governance|specs|plans|reports|reference|samples`）。
2. 更新相關文件連結。
3. 在 `docs/reports/document_relocation_log.csv` 補上回復紀錄。
