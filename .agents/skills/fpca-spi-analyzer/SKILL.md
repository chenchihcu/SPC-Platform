---
name: fpca-spi-analyzer
description: "FPCA SPI 量測分析與 PowerPoint 報告（厚度/面積/體積%、Cp/Cpk、幾何熱圖）。Use when 使用者提供 FPCA/PCB SPI CSV 與座標檔並要 pptx 報告。Do NOT use for 一般 SMT SPI 製程 RCA（改用 analyze-smt-spi）、SPC 圖表語意驗證（改用 spc-db-chart-semantics-validator）或非製造資料視覺化。"
license: MIT
metadata:
  version: v2.0
  publisher: Antigravity
---

# FPCA SPI 數據分析與 PowerPoint 報告生成器 (fpca-spi-analyzer)

此自訂技能專門用於分析 FPCA（軟性電路板組裝）製程中的 SPI 錫膏量測資料，自動將量測數據換算為厚度、面積與體積百分比（相對於 0.06mm 鋼板厚度與平均焊盤面積），並依據統計規格上下限進行合格率與 Cp/Cpk 製程能力分析。腳本支援自動偵測多段式 SPI CSV 的 `Component ID` 標題列位置。

## 主要功能
1. **PCB 實體空間幾何熱圖**：整合零件實體 X, Y 座標檔，以 2D 平面熱圖在簡報中直觀展現各元件印刷平均厚度，助於診斷印刷機水平度與鋼板下凹問題。
2. **高階 SMT DFM 品質因子與 Panel 幾何拼板多重熱圖**：整合拼板 Image 1~8 繪製 2x4 多重幾何熱圖，並自動生成 Cpk-Sigma 矩陣圖、開孔面積比與 TE% 散佈圖、以及元件方向挖料效應對比圖。
3. **機器學習特徵分群與多變量 SPC 診斷**：使用 PCA 主成分分析降維，結合 K-means (K=3) 對板子印刷特徵進行無監督分群；並計算 Hotelling T² 多變量 SPC 管制圖。
4. **印刷 DOE 3D 響應曲面與 2D 等高線圖**：以 scipy.interpolate.griddata 建立刮刀速度/壓力的 3D 響應面與 2D 等高線圖，定位印刷參數最優窗口。
5. **網板開孔幾何形狀與長寬比脫模極限圖**：繪製開孔形狀 vs. TE% 的散佈擬合圖，標示 DFM 警戒線（Aspect Ratio = 1.5）。
6. **Moran's I 空間自相關缺陷群聚圖**：手動實現 K-nearest (K=3) 空間權重矩陣，計算 Local Moran's I (LISA)，精確定位局部製程失控位置。
7. **EWMA 指數加權移動平均管制圖**：以 λ=0.2 對歷史均值賦予指數衰減權重，捕捉均值偏移小於 1.5σ 的微小漂移，提供預警性擦網與錫膏更換決策依據。
8. **帕雷托缺陷分析與 PCB 缺陷位置聯合圖**：左圖帕雷托圖鎖定 Top Offender 引腳（80/20 法則），右圖在 PCB 空間中標示缺陷位置與頻率，診斷載具支撐與鋼板局部損傷。
9. **Gauge R&R 量測系統分析 (MSA)**：以 ANOVA 法將總變異分解為量測系統 (Gauge) 與零件間 (Part-to-Part) 兩成分，計算 %R&R 相對規格容差佔比，為所有 SPC 分析建立數據品質信心基礎。
10. **多統計維度分析**：常態分佈與 Cp/Cpk、X-bar SPC 管制圖、各 PAD 箱型圖。
11. **PowerPoint 報告自動化生成**：利用 `python-pptx` 直接在本地產生寬螢幕（16:9）24 頁簡報。

## 執行指令
啟動此技能後，可於終端機執行其核心 Python 腳本來產出 PowerPoint 簡報：

```powershell
python "<skill-root>/scripts/fpca_spi_report_gen.py" --csv "<CSV數據路徑>" --components "<元件名稱，如 U1,U2>" --coord "<座標檔路徑>" --output "<輸出PPTX路徑>"
```

將 `<skill-root>` 替換成目前載入此 `SKILL.md` 的目錄；不得寫死 `.agents` 或 `.claude` loader root。
