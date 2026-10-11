---
name: analytics-engine-contract
version: 2.0.0
description: "SPC Platform analytics engine（SPCEngine、CapabilityEngine、NormalityEngine）標準回傳結構、guard 與測試慣例。Use when 在本 repo 新增或修改分析引擎契約或回傳結構。Do NOT use for 圖表統計語意驗證（改用 spc-db-chart-semantics-validator）、任務路由（改用 spc-change-router）或通用 REST API（改用 build-rest-api）。"
---

# Analytics Engine Contract — Universal Skill

定義 SPC/SPI 平台所有計算引擎 (`SPCEngine`, `CapabilityEngine`, `NormalityEngine` 等) 之標準回傳結構、Guard 防護與單元測試規範。

## 觸發時機
- 新增或重構統計計算引擎
- 審查或除錯引擎的回傳結構 (`payload`, `is_valid`, `statistics`, `metadata`)
- 為分析引擎撰寫單元測試

## 核心回傳結構概要 (High-Level Contract)
所有計算引擎方法必須統一回傳標準 Dictionary 格式：
```python
{
    "is_valid": bool,
    "chart_type": str,
    "statistics": dict,
    "parameters": dict,
    "metadata": dict,
    "error_message": str | None
}
```

## 參考指引 (Reference Routing)
詳細之 Payload 結構與防護模式請查閱：
- **完整契約規格與程式碼範本**：請讀取 `references/contract_specification.md`
  - 核心包含：各圖表專屬欄位定義、`is_valid=False` 乾淨降級規則、多參數組合契約與測試用例範本。
