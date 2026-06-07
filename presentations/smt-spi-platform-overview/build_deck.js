/**
 * SMT SPI / SPC 平台｜工程導入簡報
 *
 * 前置：
 *   python gen_chart_thumbnails.py
 *   python capture_ui_screenshots.py（於可顯示之 Windows 桌面執行）
 *
 * 產出：SMT_SPI_SPC_平台簡介.pptx
 */
"use strict";

const PptxGenJS = require("pptxgenjs");
const fs = require("fs");
const path = require("path");
const sizeOf = require(path.join(__dirname, "node_modules", "image-size"));

const OUT = path.join(__dirname, "SMT_SPI_SPC_平台簡介.pptx");
const THUMB_DIR = path.join(__dirname, "assets", "chart_thumbs");
const UI_DIR = path.join(__dirname, "assets", "ui_screens");

const FONT = "Microsoft JhengHei";
const C = {
  bg: "F8F9FA",
  white: "FFFFFF",
  blue: "1A73E8",
  blueLight: "E8F0FE",
  text: "202124",
  muted: "5F6368",
  border: "DADCE0",
  green: "34A853",
  orange: "FBBC04",
  red: "EA4335",
};

const THUMB_FILES = [
  "thumb_imr.png",
  "thumb_run.png",
  "thumb_hist.png",
  "thumb_box.png",
  "thumb_pareto.png",
  "thumb_heatmap.png",
  "thumb_scatter.png",
  "thumb_ewma.png",
  "thumb_cusum.png",
  "thumb_parallel.png",
];

const UI_SHOTS = [
  { file: "01_data_setup.png", label: "匯入資料", use: "上傳量測與座標" },
  { file: "02_workorder.png", label: "工單設定", use: "綁定規格與產品條件" },
  { file: "03_statistics.png", label: "製程診斷儀表板", use: "Cp/Cpk、PPM、DPMO" },
  { file: "04_charts.png", label: "統計圖表", use: "趨勢、能力、空間" },
  { file: "05_measure_select.png", label: "量測選定", use: "切換特徵與範圍" },
  { file: "06_diagnostic.png", label: "診斷建議", use: "根因與 IPC 摘要" },
  { file: "07_report.png", label: "匯出報告", use: "交付 HTML / PDF" },
  { file: "08_reference.png", label: "參考說明", use: "圖表與知識檢索" },
];

function asset(...parts) {
  return path.join(...parts);
}

function ensureChartThumbs() {
  const missing = THUMB_FILES.filter((f) => !fs.existsSync(asset(THUMB_DIR, f)));
  if (missing.length) {
    throw new Error(`缺少圖表縮圖：${missing.join(", ")}\n請執行：python gen_chart_thumbnails.py`);
  }
}

function imageExists(imgPath) {
  return fs.existsSync(imgPath);
}

function addImageInBox(slide, imgPath, box) {
  if (!imageExists(imgPath)) return false;
  const dim = sizeOf(imgPath);
  const ar = dim.width / dim.height;
  let w = box.w;
  let h = w / ar;
  if (h > box.h) {
    h = box.h;
    w = h * ar;
  }
  const x = box.x + (box.w - w) / 2;
  const y = box.y + (box.h - h) / 2;
  slide.addImage({ path: imgPath, x, y, w, h });
  return true;
}

function addRectFrame(slide, box, lineColor = C.border, fillColor = C.white) {
  slide.addShape("rect", {
    x: box.x,
    y: box.y,
    w: box.w,
    h: box.h,
    fill: { color: fillColor },
    line: { color: lineColor, width: 0.8 },
  });
}

function applySectionStyle(slide) {
  slide.background = { color: C.bg };
  slide.addShape("rect", {
    x: 0,
    y: 0,
    w: 0.16,
    h: 5.63,
    fill: { color: C.blue },
    line: { type: "none" },
  });
}

function sectionTitle(slide, title, subtitle) {
  applySectionStyle(slide);
  slide.addText(title, {
    x: 0.42,
    y: 0.34,
    w: 9.25,
    h: 0.48,
    fontSize: 25,
    bold: true,
    fontFace: FONT,
    color: C.text,
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x: 0.42,
      y: 0.82,
      w: 9.15,
      h: 0.48,
      fontSize: 12,
      fontFace: FONT,
      color: C.muted,
      valign: "top",
    });
  }
}

function addBodyText(slide, text, x, y, w, h, fontSize = 11.5, color = C.text) {
  slide.addText(text, {
    x, y, w, h,
    fontSize,
    fontFace: FONT,
    color,
    valign: "top",
  });
}

function addBulletBlock(slide, lines, x, y, w, h, fontSize = 11.2) {
  const body = lines.map((t) => ({
    text: t + "\n",
    options: { bullet: true, fontSize, fontFace: FONT, color: C.text },
  }));
  slide.addText(body, {
    x, y, w, h,
    valign: "top",
    lineSpacingMultiple: 1.12,
  });
}

function addCard(slide, { x, y, w, h, title, body, fill = C.white, accent = C.blue, fontSize = 10.5 }) {
  addRectFrame(slide, { x, y, w, h }, C.border, fill);
  slide.addShape("rect", {
    x, y, w: 0.08, h,
    fill: { color: accent },
    line: { type: "none" },
  });
  slide.addText(title, {
    x: x + 0.16,
    y: y + 0.12,
    w: w - 0.24,
    h: 0.24,
    fontSize: 11.5,
    bold: true,
    fontFace: FONT,
    color: C.text,
  });
  slide.addText(body, {
    x: x + 0.16,
    y: y + 0.38,
    w: w - 0.24,
    h: h - 0.44,
    fontSize,
    fontFace: FONT,
    color: C.muted,
    valign: "top",
  });
}

function addPill(slide, x, y, w, text, fill = C.blueLight, color = C.blue) {
  slide.addShape("rect", {
    x, y, w, h: 0.32,
    fill: { color: fill },
    line: { color: fill, width: 0.4 },
  });
  slide.addText(text, {
    x, y: y + 0.03, w, h: 0.22,
    fontSize: 10,
    bold: true,
    fontFace: FONT,
    color,
    align: "center",
    valign: "middle",
  });
}

function addChevron(slide, x, y, w = 0.28, h = 0.28, fill = C.blue) {
  slide.addShape("chevron", {
    x, y, w, h,
    fill: { color: fill },
    line: { color: fill, width: 0.4 },
  });
}

function addThumbCard(slide, thumbFile, title, body, x, y, w = 2.18, h = 1.75) {
  const imageH = Math.max(0.82, Math.min(h * 0.62, h - 0.58));
  addRectFrame(slide, { x, y, w, h });
  addImageInBox(slide, asset(THUMB_DIR, thumbFile), {
    x: x + 0.05,
    y: y + 0.05,
    w: w - 0.1,
    h: imageH,
  });
  slide.addText(title, {
    x: x + 0.1, y: y + imageH + 0.1, w: w - 0.2, h: 0.2,
    fontSize: 10.5, bold: true, fontFace: FONT, color: C.text, align: "center",
  });
  slide.addText(body, {
    x: x + 0.1, y: y + imageH + 0.32, w: w - 0.2, h: h - imageH - 0.38,
    fontSize: 8.6, fontFace: FONT, color: C.muted, valign: "top",
  });
}

function addUIScreen(slide, shot, x, y, w, h, showUse = true) {
  addRectFrame(slide, { x, y, w, h });
  const ok = addImageInBox(slide, asset(UI_DIR, shot.file), { x: x + 0.04, y: y + 0.04, w: w - 0.08, h: h - 0.18 });
  if (!ok) {
    slide.addText("請執行 capture_ui_screenshots.py", {
      x: x + 0.1, y: y + 0.5, w: w - 0.2, h: 0.3,
      fontSize: 8.5, fontFace: FONT, color: C.muted, align: "center",
    });
  }
  slide.addText(shot.label, {
    x, y: y + h - 0.12, w, h: 0.12,
    fontSize: 8.8, bold: true, fontFace: FONT, color: C.text, align: "center",
  });
  if (showUse) {
    slide.addText(shot.use, {
      x, y: y + h + 0.02, w, h: 0.12,
      fontSize: 7.6, fontFace: FONT, color: C.muted, align: "center",
    });
  }
}

function addFlowSteps(slide, steps, y) {
  steps.forEach((step, idx) => {
    const x = 0.46 + idx * 2.23;
    addCard(slide, {
      x, y, w: 1.8, h: 1.1,
      title: step[0],
      body: step[1],
      fill: idx % 2 === 0 ? C.white : C.blueLight,
      fontSize: 9.4,
    });
    if (idx < steps.length - 1) addChevron(slide, x + 1.9, y + 0.4);
  });
}

const pptx = new PptxGenJS();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "SMT SPI / SPC Platform";
pptx.title = "SMT SPI / SPC 統計分析平台";
pptx.subject = "工程導入簡報";

// 1 封面
{
  const s = pptx.addSlide();
  s.background = { color: C.white };
  s.addShape("rect", { x: 0, y: 0, w: 10, h: 0.22, fill: { color: C.blue }, line: { type: "none" } });
  s.addText("SMT SPI / SPC 統計分析平台", {
    x: 0.5, y: 0.84, w: 7.5, h: 0.7,
    fontSize: 30, bold: true, fontFace: FONT, color: C.text,
  });
  s.addText("工程導入簡報｜資料導入、判讀流程、圖表應用、失效分析與交付物", {
    x: 0.5, y: 1.56, w: 8.5, h: 0.35,
    fontSize: 14.5, fontFace: FONT, color: C.muted,
  });
  addPill(s, 0.52, 2.08, 1.3, "24 種圖表");
  addPill(s, 1.96, 2.08, 1.5, "80 筆 IPC/FA");
  addPill(s, 3.62, 2.08, 1.48, "報告同源");
  addRectFrame(s, { x: 0.5, y: 2.62, w: 4.35, h: 2.15 });
  addRectFrame(s, { x: 5.06, y: 2.62, w: 4.0, h: 1.02 });
  addRectFrame(s, { x: 5.06, y: 3.75, w: 4.0, h: 1.02 });
  addImageInBox(s, asset(UI_DIR, "04_charts.png"), { x: 0.54, y: 2.66, w: 4.27, h: 2.07 });
  addImageInBox(s, asset(THUMB_DIR, "thumb_heatmap.png"), { x: 5.1, y: 2.67, w: 1.86, h: 0.94 });
  addImageInBox(s, asset(THUMB_DIR, "thumb_ewma.png"), { x: 7.12, y: 2.67, w: 1.86, h: 0.94 });
  addImageInBox(s, asset(UI_DIR, "06_diagnostic.png"), { x: 5.1, y: 3.8, w: 1.86, h: 0.94 });
  addImageInBox(s, asset(UI_DIR, "07_report.png"), { x: 7.12, y: 3.8, w: 1.86, h: 0.94 });
  s.addText(`版本：工程導入版｜產出日期 ${new Date().toISOString().slice(0, 10)}`, {
    x: 0.52, y: 5.03, w: 5.5, h: 0.2, fontSize: 10.5, fontFace: FONT, color: C.muted,
  });
}

// 2 導入總覽流程
{
  const s = pptx.addSlide();
  sectionTitle(s, "工程導入總覽", "用一條標準流程串起資料、指標摘要、判讀、根因與交付，降低導入摩擦");
  addFlowSteps(s, [
    ["資料導入", "量測檔、座標檔、欄位映射"],
    ["規格綁定", "USL/LSL/Target 與工單條件"],
    ["診斷分析", "製程診斷儀表板：摘要、能力、趨勢、異常"],
    ["根因定位", "空間、類別、失效與 IPC 摘要"],
    ["交付輸出", "HTML/PDF 報告與會議附件"],
  ], 1.34);
  addRectFrame(s, { x: 0.56, y: 2.78, w: 4.32, h: 1.48 });
  addImageInBox(s, asset(UI_DIR, "01_data_setup.png"), { x: 0.6, y: 2.82, w: 4.24, h: 1.4 });
  s.addText("導入起點：欄位映射、工單條件與規格綁定", {
    x: 0.56, y: 4.29, w: 4.32, h: 0.16,
    fontSize: 9.4, bold: true, fontFace: FONT, color: C.text, align: "center",
  });
  addRectFrame(s, { x: 5.06, y: 2.78, w: 4.32, h: 1.48 });
  addImageInBox(s, asset(UI_DIR, "04_charts.png"), { x: 5.1, y: 2.82, w: 4.24, h: 1.4 });
  s.addText("導入成果：同一工作區完成儀表板摘要、管制圖與診斷建議", {
    x: 5.06, y: 4.29, w: 4.32, h: 0.16,
    fontSize: 9.4, bold: true, fontFace: FONT, color: C.text, align: "center",
  });
  addCard(s, {
    x: 0.56, y: 4.56, w: 2.86, h: 0.78,
    title: "先把資料契約講清楚",
    body: "導入前先確認 CSV 欄位、RefDes、BoardNo/Time 與規格來源，後續圖表才有工程意義。",
    fill: C.white,
    fontSize: 9.0,
  });
  addCard(s, {
    x: 3.56, y: 4.56, w: 2.86, h: 0.78,
    title: "導入流程標準化",
    body: "由資料匯入到根因定位使用固定步驟，減少不同工程師用不同圖、不同口徑的情況。",
    fill: C.blueLight,
    fontSize: 9.0,
  });
  addCard(s, {
    x: 6.56, y: 4.56, w: 2.82, h: 0.78,
    title: "輸出可直接交付",
    body: "同一份分析結果可延伸到報告與會議簡報，減少重工與多版本結論。",
    fill: C.white,
    fontSize: 9.0,
  });
}

// 3 導入痛點與對策
{
  const s = pptx.addSlide();
  sectionTitle(s, "現場常見痛點與平台對策", "工程導入時最常遇到的不是缺圖，而是資料口徑、判讀流程與交付方式不一致");
  const items = [
    ["機台匯出格式不一", "SchemaMapper 與資料契約先對齊欄位，再進入分析流程"],
    ["只能看平均值", "I-MR / EWMA / CUSUM / Histogram 將波動型態拆開"],
    ["異常不知從哪看起", "內建 ROOT_CAUSE_FLOW_ORDER，提供建議鑽取順序"],
    ["座標與量測分開", "Join 後啟用空間熱圖、RefDes/PartType 定位"],
    ["客戶報告與內部圖不同", "報告與畫面共用同一 payload 與圖表語意"],
    ["知識只在資深工程師腦中", "失效模式與 IPC/J-STD 摘要留存在系統中"],
  ];
  items.forEach((item, idx) => {
    const col = idx % 3;
    const row = Math.floor(idx / 3);
    addCard(s, {
      x: 0.46 + col * 3.05,
      y: 1.56 + row * 1.62,
      w: 2.82,
      h: 1.32,
      title: item[0],
      body: item[1],
      fill: row === 0 ? C.white : C.blueLight,
      fontSize: 9.8,
    });
  });
}

// 4 產品介面全覽
{
  const s = pptx.addSlide();
  sectionTitle(s, "產品介面全覽", "從資料匯入到報告輸出，同一個桌面工作區完成；每頁對應一種實際工程任務");
  UI_SHOTS.forEach((shot, idx) => {
    const col = idx % 4;
    const row = Math.floor(idx / 4);
    addUIScreen(s, shot, 0.46 + col * 2.27, 1.46 + row * 1.74, 2.08, 1.42);
  });
}

// 5 功能頁面與任務對照
{
  const s = pptx.addSlide();
  sectionTitle(s, "功能頁面與工程任務對照", "每個頁面不只是視覺功能，而是工程師在不同時機點的工作站");
  const rows = [
    ["匯入資料 / 工單設定", "新產品、換線、不同 SPI CSV", "完成欄位映射、規格綁定、確認空間分析可用"],
    ["製程診斷儀表板（診斷分析）", "首件、日報、能力追蹤", "Cp/Cpk、PPM、DPMO 與 OOC 風險總覽"],
    ["統計圖表 / 量測選定", "量產偏移、調機前後比較", "時序、能力、空間與多特徵檢驗"],
    ["診斷建議 / 匯出報告", "停線調查、客訴、跨部門交接", "根因提示、IPC 摘要、HTML/PDF 交付"],
  ];
  rows.forEach((row, idx) => {
    const y = 1.58 + idx * 0.82;
    addCard(s, { x: 0.46, y, w: 2.2, h: 0.68, title: row[0], body: "", fill: C.blueLight, fontSize: 9.2 });
    addCard(s, { x: 2.86, y, w: 2.7, h: 0.68, title: "典型情境", body: row[1], fill: C.white, fontSize: 9.0 });
    addCard(s, { x: 5.76, y, w: 3.7, h: 0.68, title: "工程輸出 / 決策", body: row[2], fill: C.white, fontSize: 9.0 });
  });
  addImageInBox(s, asset(THUMB_DIR, "thumb_run.png"), { x: 8.02, y: 4.92, w: 0.74, h: 0.48 });
  addImageInBox(s, asset(THUMB_DIR, "thumb_heatmap.png"), { x: 8.8, y: 4.92, w: 0.74, h: 0.48 });
}

// 6 應用案例1
{
  const s = pptx.addSlide();
  sectionTitle(s, "應用案例 1：首件 / 換線放行", "目標：在首件或換線後快速判斷是否受控、是否達規格、是否可以放行");
  addRectFrame(s, { x: 0.46, y: 1.42, w: 4.24, h: 1.72 });
  addImageInBox(s, asset(UI_DIR, "03_statistics.png"), { x: 0.5, y: 1.46, w: 4.16, h: 1.64 });
  addRectFrame(s, { x: 4.94, y: 1.42, w: 4.48, h: 1.72 });
  addImageInBox(s, asset(UI_DIR, "04_charts.png"), { x: 4.98, y: 1.46, w: 4.4, h: 1.64 });
  addCard(s, { x: 0.46, y: 3.34, w: 2.6, h: 1.3, title: "操作頁面", body: "工單設定先綁定 USL/LSL，再在製程診斷儀表板檢視 Cp/Cpk 與缺陷摘要，最後回到圖表頁確認是否有早期 shift。", fontSize: 9.4 });
  addCard(s, { x: 3.18, y: 3.34, w: 2.6, h: 1.3, title: "判斷重點", body: "能力是否達標、分布是否偏斜、是否存在板序異常、是否有單點超限。", fontSize: 9.4, fill: C.blueLight });
  addThumbCard(s, "thumb_hist.png", "關鍵圖表", "直方圖能力 + I-MR / EWMA，可同時回答規格與受控狀態。", 5.98, 3.18, 3.44, 1.72);
}

// 7 應用案例2
{
  const s = pptx.addSlide();
  sectionTitle(s, "應用案例 2：量產偏移與調機", "目標：分辨短期雜訊、持續偏移或局部空間問題，縮短停線到再驗證的時間");
  addRectFrame(s, { x: 0.46, y: 1.38, w: 4.34, h: 1.74 });
  addImageInBox(s, asset(UI_DIR, "04_charts.png"), { x: 0.5, y: 1.42, w: 4.26, h: 1.66 });
  addRectFrame(s, { x: 5.0, y: 1.38, w: 4.42, h: 1.74 });
  addImageInBox(s, asset(UI_DIR, "06_diagnostic.png"), { x: 5.04, y: 1.42, w: 4.34, h: 1.66 });
  addFlowSteps(s, [
    ["EWMA/CUSUM", "辨識是否為持續偏移"],
    ["I-MR/Run", "找異常開始區段"],
    ["熱圖/柏拉圖", "定位空間與分類異常"],
    ["診斷卡片", "形成調機與再驗證清單"],
  ], 3.38);
}

// 8 應用案例3
{
  const s = pptx.addSlide();
  sectionTitle(s, "應用案例 3：客訴、FA 與報告交付", "目標：以同一份分析 payload 產生圖表、解釋與標準依據，降低多版本結論");
  addUIScreen(s, UI_SHOTS[3], 0.46, 1.44, 2.9, 1.72, false);
  addUIScreen(s, UI_SHOTS[6], 3.58, 1.44, 2.9, 1.72, false);
  addUIScreen(s, UI_SHOTS[7], 6.7, 1.44, 2.76, 1.72, false);
  addCard(s, { x: 0.46, y: 3.42, w: 2.9, h: 1.26, title: "情境", body: "客戶要求說明某批次少錫、邊緣異常或重工後改善是否有效。", fontSize: 9.6 });
  addCard(s, { x: 3.58, y: 3.42, w: 2.9, h: 1.26, title: "平台作法", body: "保留趨勢、空間與能力圖，並附帶 root cause hints、IPC 摘要與建議措施。", fontSize: 9.6, fill: C.blueLight });
  addCard(s, { x: 6.7, y: 3.42, w: 2.76, h: 1.26, title: "交付價值", body: "報告、會議簡報與內部追蹤都引用相同圖表與口徑，降低重工與爭議。", fontSize: 9.6 });
}

// 9 導入資料與條件
{
  const s = pptx.addSlide();
  sectionTitle(s, "導入資料與前置條件", "先把資料契約與規格條件講清楚，後續圖表與診斷才有工程意義");
  addCard(s, { x: 0.46, y: 1.58, w: 1.96, h: 1.82, title: "座標檔 CSV", body: "RefDes、X、Y、Layer、PartType…\n支援空間熱圖與 footprint 比較。", fill: C.white });
  addCard(s, { x: 2.86, y: 1.58, w: 1.96, h: 1.82, title: "量測檔 CSV", body: "Volume / Area / Height、BoardNo、Time…\n支援趨勢、能力與異常分析。", fill: C.blueLight });
  addCard(s, { x: 5.26, y: 1.58, w: 1.96, h: 1.82, title: "工單 / 規格", body: "USL、LSL、Target、產品條件\n驅動能力與缺陷摘要。", fill: C.white });
  addCard(s, { x: 7.66, y: 1.58, w: 1.72, h: 1.82, title: "Join / 映射", body: "欄位別名映射後關聯，決定能否啟用空間與根因圖。", fill: C.blueLight, fontSize: 9.5 });
  [2.52, 4.92, 7.3].forEach((x) => addChevron(s, x, 2.32));
  addThumbCard(s, "thumb_heatmap.png", "空間可視化", "座標與量測成功 Join 後，才能正確畫熱圖與定位圖。", 5.64, 3.54, 1.95, 1.5);
  addThumbCard(s, "thumb_hist.png", "能力與分布", "綁定規格後可輸出能力與缺陷摘要。", 7.68, 3.54, 1.78, 1.5);
}

// 10 圖表族群
{
  const s = pptx.addSlide();
  sectionTitle(s, "圖表族群與工程問題對應", "不是圖表越多越好，而是每張圖要能回答一種工程問題");
  addThumbCard(s, "thumb_imr.png", "製程監控", "I-MR、Run、EWMA、CUSUM\n回答：是否受控？是否 drift / shift？", 0.46, 1.42, 4.35, 1.75);
  addThumbCard(s, "thumb_hist.png", "能力與分布", "Histogram、Boxplot、Normality\n回答：是否達規格？尾部風險在哪？", 5.0, 1.42, 4.42, 1.75);
  addThumbCard(s, "thumb_scatter.png", "關聯比較", "Scatter、Quadrant、Density\n回答：兩個特徵是否共變、是否存在離群群集？", 0.46, 3.33, 4.35, 1.75);
  addThumbCard(s, "thumb_parallel.png", "異常分析", "3F 異常、一致性、平行座標\n回答：多特徵是否同向惡化，是否需要機制驗證？", 5.0, 3.33, 4.42, 1.75);
}

// 11 圖表九宮格
{
  const s = pptx.addSlide();
  sectionTitle(s, "常用圖表示意", "保留最常用的 6 種核心圖，放大後更適合簡報與工程會議判讀");
  const grid = [
    ["thumb_imr.png", "I-MR 管制"],
    ["thumb_run.png", "趨勢 Run"],
    ["thumb_hist.png", "分布與能力"],
    ["thumb_pareto.png", "柏拉圖"],
    ["thumb_heatmap.png", "空間熱圖"],
    ["thumb_scatter.png", "散點 / 四象限"],
  ];
  grid.forEach((cell, idx) => {
    const col = idx % 3;
    const row = Math.floor(idx / 3);
    const x = 0.46 + col * 3.02;
    const y = 1.42 + row * 1.72;
    addRectFrame(s, { x, y, w: 2.78, h: 1.34 });
    addImageInBox(s, asset(THUMB_DIR, cell[0]), { x: x + 0.04, y: y + 0.04, w: 2.7, h: 1.08 });
    s.addText(cell[1], {
      x, y: y + 1.15, w: 2.78, h: 0.16,
      fontSize: 9.5, fontFace: FONT, color: C.text, align: "center",
    });
  });
}

// 12 失效分析工作流程
{
  const s = pptx.addSlide();
  sectionTitle(s, "失效分析工作流程", "把「先看什麼圖、再做什麼判斷」寫進產品流程，讓工程團隊判讀方式標準化");
  addFlowSteps(s, [
    ["偵測偏移", "EWMA / EWMA 3F"],
    ["確認持續", "CUSUM / CUSUM 3F"],
    ["驗證失控", "I-MR / Run"],
    ["定位原因", "熱圖 / 柏拉圖 / RO"],
    ["機制驗證", "Scatter / 3F / 一致性"],
  ], 1.54);
  addThumbCard(s, "thumb_ewma.png", "Step 1", "先分辨是否為持續偏移，而不是單點雜訊。", 0.58, 3.0, 2.8, 1.64);
  addThumbCard(s, "thumb_pareto.png", "Step 2", "再回到分類與空間，確認是局部、類別還是全域問題。", 3.58, 3.0, 2.8, 1.64);
  addThumbCard(s, "thumb_scatter.png", "Step 3", "最後用關聯或多特徵圖驗證機制與因果假說。", 6.58, 3.0, 2.8, 1.64);
}

// 13 失效知識庫與證據鏈
{
  const s = pptx.addSlide();
  sectionTitle(s, "失效知識庫與證據鏈", "圖表不只畫數線，而是連到失效模式、IPC 摘要、建議措施與報告輸出");
  addCard(s, { x: 0.46, y: 1.56, w: 2.0, h: 2.55, title: "失效模式庫", body: "症狀、統計指標、典型根因與建議措施，供異常分類與報告建議措施引用。", fill: C.white });
  addCard(s, { x: 2.82, y: 1.56, w: 2.0, h: 2.55, title: "IPC 摘要庫", body: "依 rule_id 對應標準、條文代碼與中文工程摘要，支援診斷頁與報告依據。", fill: C.blueLight });
  addCard(s, { x: 5.18, y: 1.56, w: 2.0, h: 2.55, title: "支柱知識庫", body: "目前 80 筆結構化條目，涵蓋 DFM、印刷/SPI、BGA FA、材料等主題。", fill: C.white });
  addCard(s, { x: 7.54, y: 1.56, w: 1.92, h: 2.55, title: "推論引擎", body: "輸出 hint、ipc_refs、observable_charts、優先序與建議措施。", fill: C.blueLight, fontSize: 9.8 });
  [2.56, 4.92, 7.28].forEach((x) => addChevron(s, x, 2.68, 0.28, 0.3, C.blue));
  addPill(s, 2.05, 4.38, 1.4, "圖表");
  addChevron(s, 3.62, 4.4, 0.22, 0.24, C.orange);
  addPill(s, 3.92, 4.38, 1.55, "hint / IPC");
  addChevron(s, 5.64, 4.4, 0.22, 0.24, C.orange);
  addPill(s, 5.94, 4.38, 1.42, "建議措施");
  addChevron(s, 7.53, 4.4, 0.22, 0.24, C.orange);
  addPill(s, 7.83, 4.38, 1.18, "報告");
}

// 14 技術架構
{
  const s = pptx.addSlide();
  sectionTitle(s, "技術架構與資料流", "PySide6 桌面端 + 分析引擎 + 報告服務 + 知識庫；利於維運、稽核與長期演進");
  const layers = [
    ["呈現層", "PySide6 / QSS / tokens\n頁面、導覽、圖表容器與互動。", C.white],
    ["分析層", "analytics/* + chart_registry\nSPC、能力、分布、關聯、診斷。", C.blueLight],
    ["資料層", "Loader / Mapper / Join / SessionStore\nCSV 載入、欄位映射、關聯與暫存。", C.white],
    ["交付層", "chart_render + report_service\n畫面與報告圖表同源。", C.blueLight],
    ["知識層", "failure mode + IPC/J-STD\n規則、摘要與建議措施。", C.white],
  ];
  layers.forEach((layer, idx) => {
    addCard(s, {
      x: 0.48 + idx * 1.84, y: 1.7, w: 1.64, h: 2.7,
      title: layer[0], body: layer[1], fill: layer[2], fontSize: 9.4,
    });
  });
  [2.18, 4.02, 5.86, 7.7].forEach((x) => addChevron(s, x, 2.88));
}

// 15 文件與驗證
{
  const s = pptx.addSlide();
  sectionTitle(s, "文件、測試與導入驗證", "工程導入不是只有畫面可用，還要有資料契約、統計治理與回歸驗證保護");
  addCard(s, { x: 0.46, y: 1.56, w: 2.18, h: 2.2, title: "治理文件", body: "AGENTS.md、SPC_RULES.md\n定義統計與圖表完整性邊界。", fill: C.white });
  addCard(s, { x: 2.92, y: 1.56, w: 2.18, h: 2.2, title: "資料契約", body: "data_contract.md\n欄位、Join、圖表啟用與 summary 口徑。", fill: C.blueLight });
  addCard(s, { x: 5.38, y: 1.56, w: 2.18, h: 2.2, title: "測試保護", body: "pytest 覆蓋 engine、router、registry、report 與圖表行為。", fill: C.white });
  addCard(s, { x: 7.84, y: 1.56, w: 1.62, h: 2.2, title: "知識版控", body: "IPC 摘要與失效模式可 diff、可審查、可追溯。", fill: C.blueLight, fontSize: 9.5 });
  addPill(s, 0.72, 4.18, 1.24, "可審查");
  addPill(s, 2.18, 4.18, 1.24, "可追溯");
  addPill(s, 3.64, 4.18, 1.24, "可驗證");
  addPill(s, 5.1, 4.18, 1.24, "可交接");
}

// 16 導入步驟與交付物
{
  const s = pptx.addSlide();
  sectionTitle(s, "導入步驟與交付物", "建議先跑一條產線 PoC，再擴展至多線體、知識庫與報告模板");
  addFlowSteps(s, [
    ["PoC", "匿名資料跑通匯入→分析→報告"],
    ["欄位對照", "凍結契約與規格解析方式"],
    ["現場試行", "換線/偏移/客訴案例驗收"],
    ["模板化", "報告、知識庫與串接格式落地"],
  ], 1.72);
  addCard(s, { x: 0.7, y: 3.42, w: 2.0, h: 1.25, title: "預期交付 1", body: "欄位映射與資料契約確認清單", fill: C.white, fontSize: 9.6 });
  addCard(s, { x: 2.98, y: 3.42, w: 2.0, h: 1.25, title: "預期交付 2", body: "範例工單分析結果與標準圖表組", fill: C.blueLight, fontSize: 9.6 });
  addCard(s, { x: 5.26, y: 3.42, w: 2.0, h: 1.25, title: "預期交付 3", body: "HTML/PDF 報告模板與會議附件", fill: C.white, fontSize: 9.6 });
  addCard(s, { x: 7.54, y: 3.42, w: 1.92, h: 1.25, title: "預期交付 4", body: "知識庫擴充與內部 SOP 對照", fill: C.blueLight, fontSize: 9.6 });
  addBodyText(s, "聯絡窗口／專案負責人：（請填入）", 0.46, 4.94, 4.8, 0.2, 11.5, C.blue);
}

ensureChartThumbs();

pptx
  .writeFile({ fileName: OUT })
  .then(() => {
    console.log("Wrote:", OUT);
  })
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
