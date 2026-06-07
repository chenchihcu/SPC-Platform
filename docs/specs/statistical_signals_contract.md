# Statistical Signals & Diagnosis Payload（契約）

## 版本

- `payload["statistical_signals"]["schema_version"]`：目前 **1.0.0**
- `payload["summary"]["process"]["diagnosis_engine"]["schema_version"]`：**1.0.0**
- `payload["knowledge_inference"]["schema_version"]`：**1.0.0**

## 欄位（精要）

| 鍵 | 說明 |
|----|------|
| `statistical_signals` | 由 `build_statistical_signals` 自 `summary` + 單特徵圖表 payload 組裝；含能力、相關、穩定、漂移、分布、變異、空間等 **evidence_refs** |
| `summary.process.diagnosis_engine` | `process_patterns`、`scope`、`distribution_shape`、`pattern_logic` |
| `summary.process.process_risk` | `level`（LOW/MEDIUM/HIGH）、`dimensions`、`rationale_zh`（能力／穩定／分布三維） |
| `knowledge_inference` | Steps 1–6 結構化快照 + `hypothesis_domain`（DFM_preferred / process） |

## 產生時機

`compute_analysis_payload` 成功後由 `enrich_analysis_payload` 寫入；不重算 Cp/Cpk 公式。
