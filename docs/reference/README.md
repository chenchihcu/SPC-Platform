# SMT SPI / SPC 平台 UI Design System（Light Theme）

此檔集中說明目前桌面端 Light Theme 的設計系統，方便工程師與代理直接複製 token 及對照使用。

## Color Tokens（摘要）

```python
COLOR_TOKENS = {
    "primary": {
        "900": "#0B2A66",
        "700": "#0A58CA",
        "500": "#0A84FF",
        "300": "#7CC0FF",
        "100": "#EAF4FF",
    },
    "neutral": {
        "bg_app": "#F2F2F7",
        "bg_panel": "#FFFFFF",
        "bg_subtle": "#F7F7FA",
        "bg_block": "#FFFFFF",
        "bg_block_alt": "#FAFBFC",
        "text_primary": "#1D1D1F",
        "text_secondary": "#3A3A3C",
        "text_muted": "#6E6E73",
        "text_disabled": "#AEAEB2",
        "border_default": "#D2D2D7",
        "border_strong": "#B8B8BD",
        "divider": "#E5E5EA",
    },
    "functional": {
        "success_700": "#30D158",
        "warning_700": "#FF9F0A",
        "danger_700": "#FF3B30",
        "info_700": "#0A84FF",
    },
    "spc_chart": {
        "series": "#0A84FF",
        "centerline": "#30D158",
        "control_limits": "#FF3B30",
        "spec_limits": "#AF52DE",
        "ooc_point": "#FF3B30",
        "hist_fill": "#66AFFF",
        "grid": "#DEE0E7",
        "axis_text": "#424245",
    },
}
```

## Typography Tokens（摘要）

- App Title：`FONT_SIZE_TITLE = 13.2`（對應 `TYPO_APP_TITLE_PT = 13.2`）
- Section Title：`SIDEBAR_SECTION_TITLE_FONT_SIZE = 13.2`（對應 `TYPO_SECTION_TITLE_PT = 13.2`）
- Body / Button：`FONT_SIZE_BODY = 13.2`
- Caption / Hint：`FONT_SIZE_CAPTION = 12`
- Font family：`FONT_FAMILY = "SF Pro Text / SF Pro Display 優先 + PingFang TC / Noto Sans TC / Microsoft JhengHei UI 回退"`

## Spacing Tokens（摘要）

- 基礎 8px grid：
  - `SPACING_4 = 4`
  - `SPACING_8 = 8`
  - `SPACING_12 = 12`
  - `SPACING_16 = 16`
  - `SPACING_24 = 24`
  - `SPACING_32 = 32`
- Page margins：`page_margins_and_spacing` 使用 24px 邊界、16px 元件間距。
- 表格行高：`TABLE_ROW_PADDING_COMPACT_V = 2`（對應約 28px row height）。

## 元件對應示意

- **Sidebar / Navigation**
  - 背景：`BG_CARD`
  - Active 項目：`SURFACE_ACTIVE` + 左側 `ACCENT_PRIMARY` bar
  - Phase header：`NAV_PHASE_BG`, `NAV_PHASE_TEXT`

- **Primary Button**
  - `class="primary"` 或特定 ID（例如 `refreshBtn`）
  - 背景：`ACCENT_PRIMARY` / hover：`ACCENT_PRIMARY_HOVER`

- **Table（核心工作區）**
  - Header 背景：`BG_SECONDARY`
  - 奇偶行：`BG_BLOCK` / `BG_BLOCK_ALT`
  - Hover：`SURFACE_HOVER`
  - Selected：`SURFACE_ACTIVE` + 左側 `ACCENT_PRIMARY` bar

- **SPC / Histogram Charts**
  - Data 線與點：`CHART_SERIES`
  - CL：`CHART_CENTERLINE`
  - UCL/LCL：`CHART_CONTROL_LIMITS`
  - USL/LSL：`CHART_SPEC_LIMITS`
  - OOC 點：`CHART_OOC` + `CHART_OOC_MARKER_SIZE`

未來新增頁面或元件時，請優先引用 `app.ui.theme.tokens` 內的對應 token，避免直接寫死顏色或字級，確保整體維護性與一致性。
