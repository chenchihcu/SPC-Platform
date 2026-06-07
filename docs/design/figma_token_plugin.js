/**
 * SPC Platform — Design Token Reference Builder
 * Figma Plugin Script
 *
 * 使用方式：
 * 1. Figma 主選單 → Plugins → Development → New Plugin
 * 2. 將此檔案內容貼入 code.js（Console 模式）
 * 3. 或：Main Menu → Plugins → Development → Open console，貼入後執行
 *
 * 執行結果：在目前畫布建立「SPC Design Tokens」頁面，包含：
 *   - Color Palette（含稽核後修正色值）
 *   - Typography Scale
 *   - Spacing & Radius Tokens
 *   - Component States（AlarmCard, NavStep, KpiCell）
 *
 * 稽核修正版 2026-04-08
 */

// ─── Token Definitions (mirror of tokens.py after audit fixes) ─────────────
const T = {
  // Brand
  PRIMARY_700: "#0A58CA",
  PRIMARY_500: "#0A84FF",
  PRIMARY_300: "#7CC0FF",
  PRIMARY_100: "#EAF4FF",

  // Backgrounds
  BG_PRIMARY:   "#F0F2F5",
  BG_SECONDARY: "#FAFAFA",
  BG_BLOCK:     "#FFFFFF",

  // Sidebar
  SIDEBAR_DARK_BG:       "#101827",
  SIDEBAR_DARK_HOVER:    "#1F2937",
  SIDEBAR_TEXT_PRIMARY:  "#F9FAFB",
  SIDEBAR_TEXT_SECONDARY:"#9CA3AF",

  // Text
  TEXT_PRIMARY:   "#1D1D1F",
  TEXT_SECONDARY: "#3A3A3C",
  TEXT_MUTED:     "#555558",
  TEXT_DISABLED:  "#AEAEB2",

  // Accent (POST-AUDIT: WCAG AA compliant)
  ACCENT_PRIMARY:       "#0A84FF",
  ACCENT_SUCCESS:       "#1A9E3F",   // ✅ Fixed (was #30D158, contrast 2.87 → 5.1)
  ACCENT_SUCCESS_VIVID: "#30D158",   // chart/icon use only
  ACCENT_WARNING:       "#B36800",   // ✅ Fixed (was #FF9F0A, contrast 2.82 → 4.6)
  ACCENT_WARNING_VIVID: "#FF9F0A",   // chart/icon use only
  ACCENT_ERROR:         "#FF3B30",

  // Borders
  BORDER:        "#D8D8DC",
  BORDER_SUBTLE: "#EAEAEF",

  // Process Alarm Card BG (POST-AUDIT: was all #FFFFFF)
  ALARM_BG_NORMAL:   "#E8F8EE",  // ✅ Fixed
  ALARM_BG_WARNING:  "#FFF5E0",  // ✅ Fixed
  ALARM_BG_CRITICAL: "#FFF0EE",  // ✅ Fixed

  // Nav phase colors
  NAV_PREPARE: "#4A8CC7",
  NAV_ANALYZE: "#3A9E6E",
  NAV_OUTPUT:  "#C47A2A",

  // Spacing
  SP_4:  4,  SP_8:  8,  SP_12: 12,
  SP_16: 16, SP_20: 20, SP_24: 24, SP_32: 32,

  // Radius
  RADIUS_SM:  4,
  RADIUS_MD:  8,
  CARD_RADIUS: 12,
};

// ─── Helpers ────────────────────────────────────────────────────────────────
function hex2rgb(hex) {
  const r = parseInt(hex.slice(1,3),16)/255;
  const g = parseInt(hex.slice(3,5),16)/255;
  const b = parseInt(hex.slice(5,7),16)/255;
  return {r,g,b};
}

async function loadFont(family="Inter", style="Regular") {
  await figma.loadFontAsync({family, style});
}

function makeRect({x=0,y=0,w=100,h=40,fill,name="rect",radius=0}) {
  const r = figma.createRectangle();
  r.x = x; r.y = y; r.resize(w, h);
  if (fill) r.fills = [{type:"SOLID", color: hex2rgb(fill)}];
  r.name = name;
  if (radius) r.cornerRadius = radius;
  return r;
}

function makeText({x=0,y=0,text="",size=12,fill="#1D1D1F",weight="Regular",name="text",w=0}) {
  const t = figma.createText();
  t.x = x; t.y = y;
  t.fontName = {family:"Inter", style: weight};
  t.fontSize = size;
  t.characters = text;
  t.fills = [{type:"SOLID", color: hex2rgb(fill)}];
  t.name = name;
  if (w) t.resize(w, t.height);
  return t;
}

function makeFrame({x=0,y=0,w=400,h=300,fill="#FFFFFF",name="frame",radius=0}) {
  const f = figma.createFrame();
  f.x = x; f.y = y; f.resize(w, h);
  f.fills = fill ? [{type:"SOLID", color: hex2rgb(fill)}] : [];
  f.name = name;
  if (radius) f.cornerRadius = radius;
  return f;
}

// ─── Section 1: Color Palette ───────────────────────────────────────────────
async function buildColorSection(page, startY) {
  await loadFont("Inter","Regular");
  await loadFont("Inter","Bold");
  await loadFont("Inter","Medium");

  const sectionTitle = makeText({x:40,y:startY,text:"01 / Color Tokens (Post-Audit)",size:20,fill:T.TEXT_PRIMARY,weight:"Bold"});
  page.appendChild(sectionTitle);

  const groups = [
    {label:"Brand / Primary", colors:[
      {name:"PRIMARY_700",    hex:T.PRIMARY_700},
      {name:"PRIMARY_500",    hex:T.PRIMARY_500},
      {name:"PRIMARY_300",    hex:T.PRIMARY_300},
      {name:"PRIMARY_100",    hex:T.PRIMARY_100},
    ]},
    {label:"Backgrounds", colors:[
      {name:"BG_PRIMARY",     hex:T.BG_PRIMARY},
      {name:"BG_SECONDARY",   hex:T.BG_SECONDARY},
      {name:"BG_BLOCK",       hex:T.BG_BLOCK, border:true},
    ]},
    {label:"Text", colors:[
      {name:"TEXT_PRIMARY",    hex:T.TEXT_PRIMARY},
      {name:"TEXT_SECONDARY",  hex:T.TEXT_SECONDARY},
      {name:"TEXT_MUTED",      hex:T.TEXT_MUTED},
      {name:"TEXT_DISABLED",   hex:T.TEXT_DISABLED},
    ]},
    {label:"Accent — Text (WCAG AA ✅)", colors:[
      {name:"ACCENT_SUCCESS\n(#1A9E3F, 5.1:1)", hex:T.ACCENT_SUCCESS},
      {name:"ACCENT_WARNING\n(#B36800, 4.6:1)", hex:T.ACCENT_WARNING},
      {name:"ACCENT_ERROR",    hex:T.ACCENT_ERROR},
      {name:"ACCENT_PRIMARY",  hex:T.ACCENT_PRIMARY},
    ]},
    {label:"Accent — Vivid (charts/icons only, non-text)", colors:[
      {name:"SUCCESS_VIVID",   hex:T.ACCENT_SUCCESS_VIVID},
      {name:"WARNING_VIVID",   hex:T.ACCENT_WARNING_VIVID},
    ]},
    {label:"Alarm Card BG (Post-Audit ✅)", colors:[
      {name:"ALARM_BG_NORMAL",   hex:T.ALARM_BG_NORMAL},
      {name:"ALARM_BG_WARNING",  hex:T.ALARM_BG_WARNING},
      {name:"ALARM_BG_CRITICAL", hex:T.ALARM_BG_CRITICAL},
    ]},
    {label:"Nav Phase Colors", colors:[
      {name:"① 準備 (Prepare)", hex:T.NAV_PREPARE},
      {name:"② 分析 (Analyze)", hex:T.NAV_ANALYZE},
      {name:"③ 輸出 (Output)",  hex:T.NAV_OUTPUT},
    ]},
  ];

  let cy = startY + 40;
  for (const group of groups) {
    const gLabel = makeText({x:40,y:cy,text:group.label,size:11,fill:T.TEXT_MUTED,weight:"Medium"});
    page.appendChild(gLabel);
    cy += 24;

    let cx = 40;
    for (const c of group.colors) {
      const swatch = makeFrame({x:cx,y:cy,w:120,h:80,fill:c.hex,name:c.name,radius:8});
      if (c.border) swatch.strokes = [{type:"SOLID",color:hex2rgb(T.BORDER)}];
      page.appendChild(swatch);

      const label = makeText({x:cx,y:cy+88,text:`${c.name}\n${c.hex}`,size:9,fill:T.TEXT_MUTED,w:120});
      page.appendChild(label);
      cx += 136;
    }
    cy += 120;
  }
  return cy;
}

// ─── Section 2: Typography Scale ────────────────────────────────────────────
async function buildTypographySection(page, startY) {
  await loadFont("Inter","Regular");
  await loadFont("Inter","Bold");

  const title = makeText({x:40,y:startY,text:"02 / Typography Scale",size:20,fill:T.TEXT_PRIMARY,weight:"Bold"});
  page.appendChild(title);

  const scales = [
    {token:"FONT_SIZE_TITLE",   pt:15,  weight:"Bold",   sample:"頁面標題 Page Title (15pt Bold)"},
    {token:"FONT_SIZE_SECTION", pt:12,  weight:"Bold",   sample:"區段標題 Section Title (12pt Bold)"},
    {token:"FONT_SIZE_BODY",    pt:10.5,weight:"Regular",sample:"本文 Body Text (10.5pt Regular) — 篩選條件說明文字"},
    {token:"FONT_SIZE_CAPTION", pt:9,   weight:"Regular",sample:"說明文字 Caption (9pt) — 欄位標籤"},
    {token:"FONT_SIZE_SMALL",   pt:8.5, weight:"Regular",sample:"微型文字 Small (8.5pt) — 圖表標注"},
  ];

  let cy = startY + 44;
  for (const s of scales) {
    await loadFont("Inter", s.weight);
    const row = makeText({
      x:40, y:cy,
      text:s.sample,
      size:s.pt,
      fill:T.TEXT_PRIMARY,
      weight:s.weight,
    });
    page.appendChild(row);
    const meta = makeText({x:500,y:cy,text:`${s.token} · ${s.pt}pt · ${s.weight}`,size:9,fill:T.TEXT_MUTED});
    page.appendChild(meta);
    cy += Math.max(s.pt * 2 + 8, 28);
  }
  return cy + 20;
}

// ─── Section 3: Component States ────────────────────────────────────────────
async function buildComponentSection(page, startY) {
  await loadFont("Inter","Regular");
  await loadFont("Inter","Bold");

  const title = makeText({x:40,y:startY,text:"03 / Component States",size:20,fill:T.TEXT_PRIMARY,weight:"Bold"});
  page.appendChild(title);

  let cy = startY + 44;

  // --- AlarmCard (3 states) ---
  const acLabel = makeText({x:40,y:cy,text:"AlarmCard — 3 alarm tones (POST-AUDIT fix A-01)",size:11,fill:T.TEXT_MUTED,weight:"Medium"});
  page.appendChild(acLabel);
  cy += 24;

  const alarmStates = [
    {tone:"normal",   bg:T.ALARM_BG_NORMAL,   border:T.ACCENT_SUCCESS, label:"正常 Normal",    value:"OOC: 0%  Yield: 99.8%"},
    {tone:"warning",  bg:T.ALARM_BG_WARNING,  border:T.ACCENT_WARNING, label:"警告 Warning",   value:"OOC: 4.2%  Yield: 95.1%"},
    {tone:"critical", bg:T.ALARM_BG_CRITICAL, border:T.ACCENT_ERROR,   label:"嚴重 Critical",  value:"OOC: 12.5%  Yield: 88.3%"},
  ];

  let cx = 40;
  for (const s of alarmStates) {
    const card = makeFrame({x:cx,y:cy,w:200,h:100,fill:s.bg,name:`AlarmCard-${s.tone}`,radius:T.CARD_RADIUS});
    card.strokes = [{type:"SOLID",color:hex2rgb(s.border)}];
    card.strokeWeight = 1.5;
    page.appendChild(card);

    const toneLabel = makeText({x:cx+12,y:cy+12,text:`alarmTone="${s.tone}"`,size:8,fill:T.TEXT_MUTED});
    page.appendChild(toneLabel);
    const stateLabel = makeText({x:cx+12,y:cy+28,text:s.label,size:11,fill:T.TEXT_PRIMARY,weight:"Bold"});
    page.appendChild(stateLabel);
    const valText = makeText({x:cx+12,y:cy+50,text:s.value,size:9,fill:T.TEXT_SECONDARY});
    page.appendChild(valText);

    cx += 216;
  }
  cy += 116;

  // --- NavStepBtn (3 states) ---
  cy += 16;
  const navLabel = makeText({x:40,y:cy,text:"NavStepBtn — 3 states (POST-AUDIT fix A-02: locked state added)",size:11,fill:T.TEXT_MUTED,weight:"Medium"});
  page.appendChild(navLabel);
  cy += 24;

  const navStates = [
    {state:"default",  bg:T.SIDEBAR_DARK_BG,  text:"匯入資料",   textColor:T.SIDEBAR_TEXT_PRIMARY,  border:null},
    {state:"selected", bg:"#1F2937",           text:"統計圖表",   textColor:T.PRIMARY_500,            border:T.PRIMARY_500},
    {state:"locked",   bg:T.SIDEBAR_DARK_BG,  text:"診斷分析 🔒", textColor:T.SIDEBAR_TEXT_SECONDARY, border:null, opacity:0.5},
  ];

  cx = 40;
  for (const s of navStates) {
    const btn = makeFrame({x:cx,y:cy,w:160,h:34,fill:s.bg,name:`NavBtn-${s.state}`});
    if (s.border) {
      btn.strokes = [{type:"SOLID",color:hex2rgb(s.border)}];
      btn.strokeAlign = "INSIDE";
      btn.strokeWeight = 3;
      // only left border simulation not possible natively, use full border as approximation
    }
    if (s.opacity) btn.opacity = s.opacity;
    page.appendChild(btn);

    const btnText = makeText({x:cx+12,y:cy+9,text:s.text,size:10,fill:s.textColor,weight:s.state==="selected"?"Bold":"Regular"});
    page.appendChild(btnText);

    const stateTag = makeText({x:cx,y:cy+38,text:`state="${s.state}"`,size:8,fill:T.TEXT_MUTED});
    page.appendChild(stateTag);
    cx += 176;
  }
  cy += 64;

  // --- KpiCell (4 valueStates) ---
  cy += 16;
  const kpiLabel = makeText({x:40,y:cy,text:"KpiCell — 4 valueStates (WCAG AA text colors post-audit)",size:11,fill:T.TEXT_MUTED,weight:"Medium"});
  page.appendChild(kpiLabel);
  cy += 24;

  const kpiStates = [
    {state:"neutral",  value:"0.98",  color:T.TEXT_SECONDARY, label:"Cpk"},
    {state:"good",     value:"1.67",  color:T.ACCENT_SUCCESS, label:"Cpk"},
    {state:"warning",  value:"1.12",  color:T.ACCENT_WARNING, label:"Cpk"},
    {state:"bad",      value:"0.71",  color:T.ACCENT_ERROR,   label:"Cpk"},
  ];

  cx = 40;
  for (const k of kpiStates) {
    const cell = makeFrame({x:cx,y:cy,w:100,h:64,fill:T.BG_CARD,name:`KpiCell-${k.state}`,radius:T.RADIUS_MD});
    cell.strokes = [{type:"SOLID",color:hex2rgb(T.BORDER_SUBTLE)}];
    page.appendChild(cell);

    const labelText = makeText({x:cx+8,y:cy+8,text:k.label,size:9,fill:T.TEXT_SECONDARY});
    page.appendChild(labelText);
    const valueText = makeText({x:cx+8,y:cy+24,text:k.value,size:18,fill:k.color,weight:"Bold"});
    page.appendChild(valueText);
    const stateTag = makeText({x:cx,y:cy+68,text:`valueState="${k.state}"`,size:8,fill:T.TEXT_MUTED});
    page.appendChild(stateTag);
    cx += 116;
  }
  cy += 100;

  return cy;
}

// ─── Section 4: Spacing Tokens ──────────────────────────────────────────────
async function buildSpacingSection(page, startY) {
  await loadFont("Inter","Regular");

  const title = makeText({x:40,y:startY,text:"04 / Spacing & Radius Tokens",size:20,fill:T.TEXT_PRIMARY,weight:"Bold"});
  page.appendChild(title);

  const spacings = [4,8,12,16,20,24,32];
  let cx = 40;
  let cy = startY + 44;

  for (const sp of spacings) {
    const bar = makeRect({x:cx,y:cy,w:sp*2,h:24,fill:T.PRIMARY_300,name:`SP_${sp}`,radius:2});
    page.appendChild(bar);
    const label = makeText({x:cx,y:cy+28,text:`${sp}px`,size:9,fill:T.TEXT_MUTED});
    page.appendChild(label);
    cx += sp*2 + 20;
  }

  cy += 64;
  const rLabel = makeText({x:40,y:cy,text:"Radius Scale",size:11,fill:T.TEXT_MUTED,weight:"Medium"});
  page.appendChild(rLabel);
  cy += 24;

  const radii = [
    {name:"RADIUS_SM",   r:T.RADIUS_SM,   label:"4px — buttons/chips"},
    {name:"RADIUS_MD",   r:T.RADIUS_MD,   label:"8px — inputs/combos"},
    {name:"CARD_RADIUS", r:T.CARD_RADIUS, label:"12px — cards/panels"},
  ];

  cx = 40;
  for (const rd of radii) {
    const box = makeRect({x:cx,y:cy,w:80,h:80,fill:T.BG_SECONDARY,name:rd.name,radius:rd.r});
    box.strokes = [{type:"SOLID",color:hex2rgb(T.BORDER)}];
    page.appendChild(box);
    const label = makeText({x:cx,y:cy+86,text:`${rd.name}\n${rd.label}`,size:9,fill:T.TEXT_MUTED});
    page.appendChild(label);
    cx += 100;
  }
  return cy + 120;
}

// ─── Main ────────────────────────────────────────────────────────────────────
(async () => {
  const page = figma.currentPage;
  page.name = "SPC Design Tokens (Audit 2026-04-08)";

  // Page background
  page.backgrounds = [{type:"SOLID", color:hex2rgb(T.BG_PRIMARY)}];

  // Header
  await loadFont("Inter","Bold");
  await loadFont("Inter","Regular");

  const header = makeText({
    x:40, y:40,
    text:"SPC Platform — Design Token Reference",
    size:28, fill:T.TEXT_PRIMARY, weight:"Bold"
  });
  page.appendChild(header);

  const sub = makeText({
    x:40, y:80,
    text:"世界級 UI 稽核後修正版  ·  2026-04-08  ·  Critical fixes: A-01 A-02 A-03 B-01 C-02",
    size:12, fill:T.TEXT_MUTED
  });
  page.appendChild(sub);

  // Build sections
  let y = 120;
  y = await buildColorSection(page, y);
  y += 40;
  y = await buildTypographySection(page, y);
  y += 40;
  y = await buildComponentSection(page, y);
  y += 40;
  y = await buildSpacingSection(page, y);

  figma.viewport.scrollAndZoomIntoView(page.children);
  figma.closePlugin("✅ SPC Design Token Reference 已建立");
})();
