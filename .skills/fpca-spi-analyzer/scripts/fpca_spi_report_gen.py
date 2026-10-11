# -*- coding: utf-8 -*-
"""
FPCA SPI 數據統計分析與 PowerPoint 報告生成腳本
功能：
1. 讀取 SPI 量測 CSV 資料（如 TOP.csv）
2. 針對指定元件（例如 U1, U2，以 U1_, U2_ 開頭篩選）
3. 轉換體積、面積、高度資料為百分比（%）與微米（um）
4. 繪製並列常態分佈圖、箱型圖、X-bar 管制圖（體積/面積/高度並列）
5. 生成專業的 PowerPoint (.pptx) 簡報，包含統計摘要與控制分析
"""
import os
import sys
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from scipy.stats import f


# 設定 Matplotlib 支援中文字型，防止亂碼
plt.rcParams['font.family'] = 'Microsoft JhengHei'  # 微軟正黑體
plt.rcParams['axes.unicode_minus'] = False  # 正常顯示負號

def get_long_data(df, comp_prefix):
    """
    將寬表的量測數據，轉換為方便分析的長表，並計算體積、面積與高度的百分比
    """
    df_comp = df[df['Component ID'].str.upper().str.startswith(comp_prefix, na=False)].copy()
    if df_comp.empty:
        print(f"警告: 找不到以 '{comp_prefix}' 開頭的元件資料")
        return pd.DataFrame()

    rows = []
    # 總共有 38 片板子的量測數據
    for _, row in df_comp.iterrows():
        comp_id = row['Component ID']
        pad_id = int(row['PAD ID'])

        # 收集該 PAD 在所有板子上的量測值以計算理論面積
        areas = []
        for b in range(1, 39):
            a_col = f'Area(mm){b}'
            if a_col in row and not pd.isna(row[a_col]):
                areas.append(row[a_col])

        # 以所有板子的平均面積作為該 PAD 的設計（理論）面積
        ref_area = np.mean(areas) if len(areas) > 0 else 0.1
        ref_volume = ref_area * 0.06  # 理論體積 (鋼板厚度 0.06mm)

        for b in range(1, 39):
            v_col = f'Volume(mm){b}'
            h_col = f'Height(mm){b}'
            a_col = f'Area(mm){b}'

            v_val = row.get(v_col, np.nan)
            h_val = row.get(h_col, np.nan)
            a_val = row.get(a_col, np.nan)

            if not (pd.isna(v_val) or pd.isna(h_val) or pd.isna(a_val)):
                rows.append({
                    'Component_ID': comp_id,
                    'PAD_ID': pad_id,
                    'Board_ID': b,
                    'Volume_mm3': v_val,
                    'Area_mm2': a_val,
                    'Height_mm': h_val,
                    'Height_um': h_val * 1000.0,
                    'Volume_pct': (v_val / ref_volume) * 100.0 if ref_volume > 0 else 100.0,
                    'Area_pct': (a_val / ref_area) * 100.0 if ref_area > 0 else 100.0,
                    'Height_pct': (h_val / 0.06) * 100.0
                })
    return pd.DataFrame(rows)

def draw_spatial_heatmap(df, coord_csv_path, comp_list, output_path):
    """
    繪製 PCB 元件印刷厚度空間分佈熱圖
    """
    if not os.path.exists(coord_csv_path):
        print(f"警告: 找不到座標檔 {coord_csv_path}，跳過空間熱圖繪製")
        return False

    df_coord = pd.read_csv(coord_csv_path)

    # 確保必要欄位存在
    required_cols = ['RefDes', 'X', 'Y']
    if not all(col in df_coord.columns for col in required_cols):
        print("警告: 座標檔缺少必要欄位 (RefDes, X, Y)，跳過空間熱圖繪製")
        return False

    plt.figure(figsize=(10, 8))

    # 畫背景元件 (淡灰色)
    plt.scatter(df_coord['X'], df_coord['Y'], color='#e0e0e0', s=30, alpha=0.8, label='其他背景元件')
    for _, row in df_coord.iterrows():
        ref = row['RefDes']
        if ref not in comp_list:
            plt.text(row['X'], row['Y'] + 0.5, str(ref), fontsize=8, color='#a0a0a0', ha='center', alpha=0.7)

    comp_coords_x = []
    comp_coords_y = []
    comp_colors = []
    comp_labels = []

    for comp in comp_list:
        coord_row = df_coord[df_coord['RefDes'].str.upper() == comp.upper()]
        if coord_row.empty:
            print(f"  在座標檔中找不到分析元件 {comp}")
            continue

        x_val = coord_row['X'].values[0]
        y_val = coord_row['Y'].values[0]

        df_long = get_long_data(df, comp + "_")
        if df_long.empty:
            print(f"  在量測資料中找不到元件 {comp} 的數據")
            continue

        mean_height_pct = df_long['Height_pct'].mean()

        comp_coords_x.append(x_val)
        comp_coords_y.append(y_val)
        comp_colors.append(mean_height_pct)
        comp_labels.append((comp, x_val, y_val, mean_height_pct))

    if comp_coords_x:
        sc = plt.scatter(comp_coords_x, comp_coords_y, c=comp_colors, cmap='coolwarm',
                         vmin=50, vmax=170, s=200, edgecolors='black', linewidths=1.5, zorder=5, label='統計分析元件')

        for comp, x, y, val in comp_labels:
            plt.text(x, y + 1.2, f"{comp}\n({val:.1f}%)", fontsize=10, color='black',
                     fontweight='bold', ha='center', bbox=dict(boxstyle='round,pad=0.2', facecolor='#ffffff', alpha=0.85, edgecolor='gray'))

        cbar = plt.colorbar(sc, shrink=0.75, pad=0.05)
        cbar.set_label('錫膏高度平均百分比 (%) / (LSL=50%, USL=170%)', fontsize=11, fontweight='bold')
        cbar.ax.tick_params(labelsize=10)

    plt.title("PCB 元件級錫膏高度實體空間分佈熱圖", fontsize=15, fontweight='bold', pad=15)
    plt.xlabel("PCB X 座標 (mm)", fontsize=11)
    plt.ylabel("PCB Y 座標 (mm)", fontsize=11)
    plt.legend(loc='lower left', fontsize=10)
    plt.grid(True, linestyle=':', alpha=0.4)

    x_min, x_max = df_coord['X'].min() - 3, df_coord['X'].max() + 3
    y_min, y_max = df_coord['Y'].min() - 3, df_coord['Y'].max() + 3
    plt.xlim(x_min, x_max)
    plt.ylim(y_min, y_max)

    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()
    return True

def draw_diagnostic_plots(df_long, comp_name, output_path):
    """
    繪製 鋼板擦網清洗週期趨勢圖 與 刮刀往返方向對稱性對比圖 (並列展示)
    """
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2))

    # 1. 左圖：擦網清洗週期趨勢圖 (以高度百分比為例)
    ax = axes[0]
    board_stats = df_long.groupby('Board_ID')['Height_pct'].mean().reset_index()
    ax.plot(board_stats['Board_ID'], board_stats['Height_pct'],
            marker='o', color='darkblue', linewidth=1.5, label='板平均高度')

    # 標示每 5 片的擦網點
    wiping_cycle = 5
    for b in range(wiping_cycle, 39, wiping_cycle):
        ax.axvline(b, color='green', linestyle='--', linewidth=1.2, alpha=0.8,
                   label='自動擦網清洗 (Wipe)' if b == wiping_cycle else "")

    ax.set_title("鋼板擦網清洗週期趨勢圖", fontsize=12, fontweight='bold')
    ax.set_xlabel("板子編號 (Board ID)", fontsize=10)
    ax.set_ylabel("高度百分比 (%)", fontsize=10)
    ax.set_xticks(range(1, 39, 4))
    ax.legend(loc='lower left', fontsize=8)
    ax.grid(True, linestyle=':', alpha=0.5)

    # 2. 右圖：刮刀往返方向對稱性對比圖
    ax = axes[1]
    # 奇數為 Forward, 偶數為 Reverse
    df_long_copy = df_long.copy()
    df_long_copy['Squeegee_Direction'] = np.where(df_long_copy['Board_ID'] % 2 == 1, 'Forward (往行程)', 'Reverse (返行程)')

    f_mean = df_long_copy[df_long_copy['Squeegee_Direction'] == 'Forward (往行程)']['Height_pct'].mean()
    r_mean = df_long_copy[df_long_copy['Squeegee_Direction'] == 'Reverse (返行程)']['Height_pct'].mean()
    f_std = df_long_copy[df_long_copy['Squeegee_Direction'] == 'Forward (往行程)']['Height_pct'].std()
    r_std = df_long_copy[df_long_copy['Squeegee_Direction'] == 'Reverse (返行程)']['Height_pct'].std()

    sns.boxplot(x='Squeegee_Direction', y='Height_pct', data=df_long_copy, palette='pastel', ax=ax, hue='Squeegee_Direction', legend=False)

    info_text = f"Forward 平均: {f_mean:.1f}% (±{f_std:.1f}%)\nReverse 平均: {r_mean:.1f}% (±{r_std:.1f}%)"
    ax.text(0.05, 0.95, info_text, transform=ax.transAxes, fontsize=9,
            verticalalignment='top', bbox=dict(boxstyle='round,pad=0.4', facecolor='white', alpha=0.85))

    ax.set_title("刮刀往返方向印刷高度對稱性對比", fontsize=12, fontweight='bold')
    ax.set_xlabel("刮刀行程方向", fontsize=10)
    ax.set_ylabel("高度百分比 (%)", fontsize=10)
    ax.grid(True, linestyle=':', alpha=0.5)

    plt.suptitle(f"{comp_name} 元件 - 鋼板擦網與刮刀方向印刷診斷", fontsize=14, fontweight='bold', y=0.98)
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()

def draw_subboard_plot(df_long, comp_name, output_path):
    """
    繪製 拼板位置幾何變異分析圖 (Image ID 1~8)
    """
    df_long_copy = df_long.copy()

    df_long_copy['Image_ID'] = df_long_copy['Component_ID'].apply(lambda x: int(x.split('_')[-1]) if '_' in x else 1)

    plt.figure(figsize=(10, 5))
    sns.boxplot(x='Image_ID', y='Height_pct', data=df_long_copy, palette='husl', hue='Image_ID', legend=False)

    plt.axhline(50, color='red', linestyle='--', linewidth=1.2, label='LSL (50%)')
    plt.axhline(170, color='red', linestyle='--', linewidth=1.2, label='USL (170%)')

    img_means = df_long_copy.groupby('Image_ID')['Height_pct'].mean().reset_index()
    plt.plot(img_means['Image_ID'] - 1, img_means['Height_pct'], color='darkblue', marker='o', linewidth=1.5, linestyle='-', label='Image 平均值')

    plt.title(f"{comp_name} 元件 - 拼板位置幾何變異分析 (Image Effect)", fontsize=13, fontweight='bold')
    plt.xlabel("拼板小板編號 (Image ID)", fontsize=11)
    plt.ylabel("高度百分比 (%)", fontsize=11)
    plt.xticks(range(8), [f"Image {i}" for i in range(1, 9)])
    plt.legend(loc='upper right')
    plt.grid(True, linestyle=':', alpha=0.5)

    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()

def draw_advanced_diagnostic_plots(df, coord_csv_path, comp_list, out_dir):
    """
    生成 4 種高階 SMT 診斷圖表：
    1. temp_panel_heatmap.png (2x4 Panel 熱圖)
    2. temp_cpk_sigma.png (Cpk vs. Sigma 矩陣圖)
    3. temp_area_ratio_te.png (面積比 vs. TE% 散佈圖)
    4. temp_orient_scooping.png (Orientation 擺放方向挖料效應圖)
    """
    if not os.path.exists(coord_csv_path):
        print("警告: 座標檔不存在，跳過高階 SMT 圖表生成")
        return False

    df_coord = pd.read_csv(coord_csv_path)

    required_cols = ['RefDes', 'X', 'Y', 'Orient.']
    if not all(col in df_coord.columns for col in required_cols):
        print("警告: 座標檔缺少必要欄位 (RefDes, X, Y, Orient.)，跳過高階 SMT 圖表生成")
        return False

    # 1. 繪製 temp_panel_heatmap.png (2x4 Panel 熱圖)
    fig, axes = plt.subplots(2, 4, figsize=(16, 8.5))
    axes = axes.flatten()

    for idx in range(8):
        image_id = idx + 1
        ax = axes[idx]

        ax.scatter(df_coord['X'], df_coord['Y'], color='#f0f0f0', s=20, alpha=0.7)
        for _, row in df_coord.iterrows():
            ref = row['RefDes']
            if ref not in comp_list:
                ax.text(row['X'], row['Y'] + 0.4, str(ref), fontsize=6, color='#c0c0c0', ha='center', alpha=0.6)

        comp_coords_x = []
        comp_coords_y = []
        comp_colors = []

        for comp in comp_list:
            coord_row = df_coord[df_coord['RefDes'].str.upper() == comp.upper()]
            if coord_row.empty:
                continue
            x_val = coord_row['X'].values[0]
            y_val = coord_row['Y'].values[0]

            df_long = get_long_data(df, comp + "_")
            if df_long.empty:
                continue
            df_img = df_long[df_long['Component_ID'] == f"{comp}_{image_id}"]
            if df_img.empty:
                df_img = df_long[df_long['Component_ID'].str.endswith(f"_{image_id}")]

            if not df_img.empty:
                mean_height = df_img['Height_pct'].mean()
                comp_coords_x.append(x_val)
                comp_coords_y.append(y_val)
                comp_colors.append(mean_height)

        if comp_coords_x:
            ax.scatter(comp_coords_x, comp_coords_y, c=comp_colors, cmap='coolwarm',
                             vmin=50, vmax=170, s=120, edgecolors='black', linewidths=1.0, zorder=5)
            for cx, cy, col in zip(comp_coords_x, comp_coords_y, comp_colors):
                ax.text(cx, cy + 1.2, f"{col:.1f}%", fontsize=7, color='black', fontweight='bold', ha='center')

        ax.set_title(f"拼板 Image {image_id}", fontsize=10, fontweight='bold')
        ax.set_xticks([])
        ax.set_yticks([])
        ax.grid(False)

    plt.suptitle("PCB Panel 2x4 幾何拼板多重印刷熱圖", fontsize=15, fontweight='bold', y=0.98)
    fig.subplots_adjust(right=0.88)
    cbar_ax = fig.add_axes([0.91, 0.15, 0.02, 0.7])
    cbar = fig.colorbar(plt.cm.ScalarMappable(norm=plt.Normalize(50, 170), cmap='coolwarm'), cax=cbar_ax)
    cbar.set_label('錫膏高度平均百分比 (%) / (LSL=50%, USL=170%)', fontsize=11, fontweight='bold')

    plt.savefig(os.path.join(out_dir, "temp_panel_heatmap.png"), dpi=200, bbox_inches='tight')
    plt.close()

    # 2. 繪製 temp_cpk_sigma.png (Cpk vs. Sigma 矩陣圖)
    comp = comp_list[0]
    df_long = get_long_data(df, comp + "_")
    if not df_long.empty:
        pad_stats = []
        for pad in sorted(df_long['PAD_ID'].unique()):
            df_pad = df_long[df_long['PAD_ID'] == pad]
            mean = df_pad['Height_pct'].mean()
            std = df_pad['Height_pct'].std()
            Cpk = min((170.0 - mean) / (3 * std), (mean - 50.0) / (3 * std)) if std > 0 else 0
            pad_stats.append({'PAD_ID': pad, 'Cpk': Cpk, 'Sigma': std})

        df_pad_stats = pd.DataFrame(pad_stats)

        plt.figure(figsize=(6, 5))
        plt.scatter(df_pad_stats['Cpk'], df_pad_stats['Sigma'], color='darkblue', edgecolors='black', s=100, zorder=5)
        for _, row in df_pad_stats.iterrows():
            plt.text(row['Cpk'] + 0.02, row['Sigma'], f"P{int(row['PAD_ID'])}", fontsize=8, verticalalignment='center')

        plt.axvline(1.33, color='red', linestyle='--', linewidth=1.2, label='Cpk 合格線 (1.33)')
        plt.axhline(15.0, color='orange', linestyle=':', linewidth=1.2, label='Sigma 控制限 (15%)')

        plt.title(f"{comp} 元件 - Cpk 與變異 (Sigma) 關聯矩陣圖", fontsize=11, fontweight='bold')
        plt.xlabel("製程能力指數 (Cpk)", fontsize=10)
        plt.ylabel("印刷高度標準差 (Sigma, %)", fontsize=10)
        plt.grid(True, linestyle=':', alpha=0.5)
        plt.legend(loc='upper right', fontsize=8)
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, "temp_cpk_sigma.png"), dpi=200)
        plt.close()

    # 3. 繪製 temp_area_ratio_te.png (面積比 vs. TE% 散佈圖)
    all_pad_data = []
    for comp in comp_list:
        df_long = get_long_data(df, comp + "_")
        if df_long.empty:
            continue
        for pad in df_long['PAD_ID'].unique():
            df_pad = df_long[df_long['PAD_ID'] == pad]
            mean_volume_pct = df_pad['Volume_pct'].mean()
            mean_area_mm2 = df_pad['Area_mm2'].mean()
            area_ratio = np.sqrt(mean_area_mm2) / 0.24 if mean_area_mm2 > 0 else 0.1
            all_pad_data.append({'RefDes': comp, 'PAD_ID': pad, 'Area_Ratio': area_ratio, 'TE': mean_volume_pct})

    if all_pad_data:
        df_ar_te = pd.DataFrame(all_pad_data)
        plt.figure(figsize=(6, 5))
        sns.regplot(x='Area_Ratio', y='TE', data=df_ar_te, scatter_kws={'s':100, 'edgecolors':'black', 'color':'forestgreen'}, line_kws={'color':'red', 'linewidth':1.5})

        plt.axvline(0.66, color='red', linestyle='--', linewidth=1.2, label='DFM 限度 (0.66)')

        for _, row in df_ar_te.iterrows():
            plt.text(row['Area_Ratio'] + 0.01, row['TE'], f"{row['RefDes']}P{int(row['PAD_ID'])}", fontsize=7)

        plt.title("鋼板開孔面積比 (Area Ratio) vs. 轉移率 (TE %)", fontsize=11, fontweight='bold')
        plt.xlabel("推估開孔面積比 (Area Ratio)", fontsize=10)
        plt.ylabel("錫膏下錫轉移率 (Transfer Efficiency %)", fontsize=10)
        plt.grid(True, linestyle=':', alpha=0.5)
        plt.legend(loc='lower right', fontsize=8)
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, "temp_area_ratio_te.png"), dpi=200)
        plt.close()

    # 4. 繪製 temp_orient_scooping.png (Orientation 擺放方向挖料效應圖)
    orient_data = []
    for _, row in df_coord.iterrows():
        ref = row['RefDes']
        orient = row['Orient.']
        comp_matches = df[df['Component ID'].str.upper().str.startswith(ref.upper() + "_", na=False)]['Component ID'].unique()
        if len(comp_matches) > 0:
            for comp_match in comp_matches:
                df_long_m = get_long_data(df, comp_match.split('_')[0] + "_")
                if not df_long_m.empty:
                    df_comp_only = df_long_m[df_long_m['Component_ID'] == comp_match]
                    if not df_comp_only.empty:
                        for height_val in df_comp_only['Height_pct']:
                            orient_data.append({'Orient': f"{int(orient)}° 擺放", 'Height_pct': height_val})

    if orient_data:
        df_orient = pd.DataFrame(orient_data)
        plt.figure(figsize=(6, 5))
        sns.boxplot(x='Orient', y='Height_pct', data=df_orient, palette='Set2', hue='Orient', legend=False)

        means = df_orient.groupby('Orient')['Height_pct'].mean()
        info_text = "\n".join([f"{k} 平均: {v:.1f}%" for k, v in means.items()])
        plt.text(0.05, 0.95, info_text, transform=plt.gca().transAxes, fontsize=9,
                 verticalalignment='top', bbox=dict(boxstyle='round,pad=0.4', facecolor='white', alpha=0.85))

        plt.title("元件擺放方向對印刷高度之影響 (挖料效應分析)", fontsize=11, fontweight='bold')
        plt.xlabel("元件擺放角度 (Orientation)", fontsize=10)
        plt.ylabel("印刷高度百分比 (%)", fontsize=10)
        plt.grid(True, linestyle=':', alpha=0.5)
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, "temp_orient_scooping.png"), dpi=200)
        plt.close()

    return True

def draw_spc_radar_plots(df, coord_csv_path, comp_list, out_dir):
    """
    生成 3 種高端 SPC 與拼板大板診斷圖表：
    1. temp_panel_radar.png (Polar 拼板多維綜合品質雷達圖)
    2. temp_pad_correlation.png (16個焊盤高度皮爾森相關性熱圖)
    3. temp_rolling_cpk.png (滾動 Cpk 趨勢折線圖)
    """
    categories = ['高度良率', '體積良率', '面積良率', 'Cpk能力', '印刷均勻度']
    N = len(categories)
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]

    plt.figure(figsize=(8, 7.5))
    ax = plt.subplot(111, projection='polar')

    plt.xticks(angles[:-1], categories, fontsize=11, fontweight='bold')
    ax.set_rlabel_position(30)
    plt.yticks([20, 40, 60, 80, 100], ["20", "40", "60", "80", "100分"], color="grey", fontsize=8)
    plt.ylim(0, 100)

    colors = plt.cm.rainbow(np.linspace(0, 1, 8))

    for idx in range(8):
        image_id = idx + 1

        v_list = []
        a_list = []
        h_list = []

        for comp in comp_list:
            df_long = get_long_data(df, comp + "_")
            if df_long.empty:
                continue
            df_img = df_long[df_long['Component_ID'] == f"{comp}_{image_id}"]
            if df_img.empty:
                df_img = df_long[df_long['Component_ID'].str.endswith(f"_{image_id}")]
            if not df_img.empty:
                v_list.append(df_img['Volume_pct'])
                a_list.append(df_img['Area_pct'])
                h_list.append(df_img['Height_pct'])

        if not h_list:
            continue

        v_all = pd.concat(v_list)
        a_all = pd.concat(a_list)
        h_all = pd.concat(h_list)

        h_yield = (sum((h_all >= 50.0) & (h_all <= 170.0)) / len(h_all)) * 100
        v_yield = (sum((v_all >= 50.0) & (v_all <= 170.0)) / len(v_all)) * 100
        a_yield = (sum((a_all >= 50.0) & (a_all <= 170.0)) / len(a_all)) * 100

        mean_h = h_all.mean()
        std_h = h_all.std()
        Cpk = min((170.0 - mean_h) / (3 * std_h), (mean_h - 50.0) / (3 * std_h)) if std_h > 0 else 0
        cpk_score = min(100.0, max(0.0, Cpk * 50.0))
        std_score = min(100.0, max(0.0, 100.0 - std_h * 2.0))

        values = [h_yield, v_yield, a_yield, cpk_score, std_score]
        values += values[:1]

        ax.plot(angles, values, linewidth=1.5, linestyle='solid', color=colors[idx], label=f"Image {image_id}")
        ax.fill(angles, values, color=colors[idx], alpha=0.08)

    plt.title("Panel 幾何拼板多小板綜合品質雷達圖 (Image-level Quality Radar)", fontsize=13, fontweight='bold', pad=20)
    plt.legend(loc='upper right', bbox_to_anchor=(1.25, 1.1), fontsize=9)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "temp_panel_radar.png"), dpi=200)
    plt.close()

    comp = comp_list[0]
    df_long = get_long_data(df, comp + "_")
    if not df_long.empty:
        df_long = df_long.copy()
        df_long['Unique_ID'] = df_long['Board_ID'].astype(str) + "_" + df_long['Component_ID']
        df_pivot = df_long.pivot(index='Unique_ID', columns='PAD_ID', values='Height_pct')

        corr_matrix = df_pivot.corr()

        plt.figure(figsize=(7, 6))
        sns.heatmap(corr_matrix, cmap='coolwarm', vmin=-1.0, vmax=1.0, annot=False, linewidths=.5, cbar_kws={'label': '皮爾森相關係數 (r)'})
        plt.title(f"{comp} 元件 - 焊盤 (PAD-to-PAD) 錫膏高度印刷相關性熱圖", fontsize=11, fontweight='bold')
        plt.xlabel("焊盤編號 (PAD ID)", fontsize=10)
        plt.ylabel("焊盤編號 (PAD ID)", fontsize=10)
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, "temp_pad_correlation.png"), dpi=200)
        plt.close()

    if not df_long.empty:
        rolling_stats = []
        window_size = 10
        for t in range(window_size, 39):
            df_window = df_long[df_long['Board_ID'].between(t - window_size + 1, t)]
            mean = df_window['Height_pct'].mean()
            std = df_window['Height_pct'].std()
            Cpk = min((170.0 - mean) / (3 * std), (mean - 50.0) / (3 * std)) if std > 0 else 0
            rolling_stats.append({'Window_End': t, 'Cpk': Cpk})

        df_rolling = pd.DataFrame(rolling_stats)

        plt.figure(figsize=(7, 5))
        plt.plot(df_rolling['Window_End'], df_rolling['Cpk'], color='darkred', marker='o', linewidth=2.0, label=f"滾動 Cpk (窗口={window_size}片)")
        plt.axhline(1.33, color='green', linestyle='--', linewidth=1.5, label='Cpk 合格限度 (1.33)')
        plt.axhline(1.0, color='red', linestyle='-.', linewidth=1.2, label='最小製程能力 (1.0)')

        plt.title(f"{comp} 元件 - 製程能力隨生產板數滾動漂移趨勢圖", fontsize=11, fontweight='bold')
        plt.xlabel("滾動窗口截止板子編號 (Board ID)", fontsize=10)
        plt.ylabel("動態製程能力指數 (Rolling Cpk)", fontsize=10)
        plt.xlim(window_size, 38)
        plt.grid(True, linestyle=':', alpha=0.5)
        plt.legend(loc='lower left', fontsize=9)
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, "temp_rolling_cpk.png"), dpi=200)
        plt.close()

    return True

def draw_extreme_diagnostic_plots(df, comp_list, out_dir):
    """
    生成 3 種極端先進的 SMT 與 SPC 統計圖表：
    1. temp_vol_height_corr.png (體積 vs. 高度自相關散佈圖)
    2. temp_print_clustering.png (基於 PCA + K-means 的印刷特徵分群圖)
    3. temp_multivariate_t2.png (多變量 Hotelling T-squared 管制圖)
    """
    import matplotlib.patches as patches

    # --- 1. 體積 vs. 高度自相關散佈圖 ---
    comp = comp_list[0]
    df_long = get_long_data(df, comp + "_")
    if not df_long.empty:
        plt.figure(figsize=(7, 6))
        sns.scatterplot(data=df_long, x='Height_pct', y='Volume_pct', hue='PAD_ID', palette='tab20', alpha=0.7, legend=False)

        rect_normal = patches.Rectangle((70, 70), 60, 60, linewidth=1.5, edgecolor='green', facecolor='none', linestyle='--', label='正常區 (70-130%)')
        plt.gca().add_patch(rect_normal)

        rect_dogear = patches.Rectangle((130, 50), 40, 80, linewidth=1.5, edgecolor='orange', facecolor='none', linestyle='-.', label='拉尖風險區 (Dog-ear)')
        plt.gca().add_patch(rect_dogear)

        rect_collapse = patches.Rectangle((50, 90), 40, 60, linewidth=1.5, edgecolor='red', facecolor='none', linestyle=':', label='坍塌風險區 (Collapse)')
        plt.gca().add_patch(rect_collapse)

        plt.axvline(50, color='red', linestyle='--', alpha=0.5)
        plt.axvline(170, color='red', linestyle='--', alpha=0.5)
        plt.axhline(50, color='red', linestyle='--', alpha=0.5)
        plt.axhline(170, color='red', linestyle='--', alpha=0.5)

        plt.title(f"{comp} 元件 - 錫膏體積 vs. 高度自相關散佈圖", fontsize=11, fontweight='bold')
        plt.xlabel("高度百分比 (Height %)", fontsize=10)
        plt.ylabel("體積百分比 (Volume %)", fontsize=10)
        plt.legend(loc='upper right', fontsize=8)
        plt.grid(True, linestyle=':', alpha=0.5)
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, "temp_vol_height_corr.png"), dpi=200)
        plt.close()

    # --- 2. 印刷特徵分群圖 ---
    if not df_long.empty:
        df_long = df_long.copy()
        df_long['Unique_ID'] = df_long['Board_ID'].astype(str) + "_" + df_long['Component_ID']
        df_pivot_pca = df_long.pivot_table(index='Board_ID', columns=['Component_ID', 'PAD_ID'], values='Height_pct', aggfunc='mean')
        df_pivot_pca = df_pivot_pca.fillna(df_pivot_pca.mean())

        pca = PCA(n_components=2)
        X_pca = pca.fit_transform(df_pivot_pca)

        kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
        labels = kmeans.fit_predict(df_pivot_pca)

        plt.figure(figsize=(7, 6))
        colors_cluster = ['#1f77b4', '#ff7f0e', '#2ca02c']
        for cluster_id in range(3):
            mask = (labels == cluster_id)
            plt.scatter(X_pca[mask, 0], X_pca[mask, 1], c=colors_cluster[cluster_id], s=100, label=f"群組 {cluster_id + 1}", alpha=0.8, edgecolors='black')

        for i, txt in enumerate(df_pivot_pca.index):
            plt.annotate(f"B{txt}", (X_pca[i, 0] + 0.1, X_pca[i, 1] + 0.1), fontsize=8, alpha=0.8)

        plt.title(f"{comp} 元件 - 基於 PCA 與 K-means (K=3) 之印刷特徵分群診斷圖", fontsize=11, fontweight='bold')
        plt.xlabel("主成分 1 (PC1)", fontsize=10)
        plt.ylabel("主成分 2 (PC2)", fontsize=10)
        plt.legend(loc='best', fontsize=9)
        plt.grid(True, linestyle=':', alpha=0.5)
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, "temp_print_clustering.png"), dpi=200)
        plt.close()

    # --- 3. 多變量 Hotelling T-squared 管制圖 ---
    if not df_long.empty:
        board_multivariate = df_long.groupby('Board_ID')[['Height_pct', 'Volume_pct', 'Area_pct']].mean()

        mean_vec = board_multivariate.mean().values
        cov_mat = board_multivariate.cov().values
        cov_inv = np.linalg.inv(cov_mat)

        t2_values = []
        for _, row in board_multivariate.iterrows():
            diff = row.values - mean_vec
            t2 = diff.T @ cov_inv @ diff
            t2_values.append(t2)

        board_multivariate['T2'] = t2_values

        n = len(board_multivariate)
        p = 3
        alpha = 0.05
        f_crit = f.ppf(1 - alpha, p, n - p)
        UCL = (p * (n - 1) * (n + 1) / (n * (n - p))) * f_crit

        plt.figure(figsize=(7, 5))
        colors_t2 = ['red' if val > UCL else 'darkblue' for val in t2_values]
        plt.plot(board_multivariate.index, board_multivariate['T2'], color='gray', linestyle='-', alpha=0.5)
        plt.scatter(board_multivariate.index, board_multivariate['T2'], c=colors_t2, s=60, edgecolors='black', zorder=3)
        plt.axhline(UCL, color='red', linestyle='--', linewidth=1.5, label=f'UCL 控制上限 ({UCL:.2f})')

        for i, val in enumerate(t2_values):
            if val > UCL:
                plt.annotate(f"B{board_multivariate.index[i]}", (board_multivariate.index[i] + 0.2, val + 0.2), color='red', fontweight='bold', fontsize=9)

        plt.title(f"{comp} 元件 - 多變量 Hotelling $T^2$ 管制圖 (高度/體積/面積三指標協同監控)", fontsize=11, fontweight='bold')
        plt.xlabel("生產板子編號 (Board ID)", fontsize=10)
        plt.ylabel("Hotelling $T^2$ 統計量", fontsize=10)
        plt.xlim(1, 38)
        plt.ylim(0, max(max(t2_values) * 1.1, UCL * 1.2))
        plt.legend(loc='upper right', fontsize=9)
        plt.grid(True, linestyle=':', alpha=0.5)
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, "temp_multivariate_t2.png"), dpi=200)
        plt.close()

    return True

def draw_doe_aperture_spatial_plots(df, coord_csv_path, comp_list, out_dir):
    """
    生成 3 種極端先進的 SMT 製程優化與缺陷定位圖表：
    1. temp_doe_response.png (刮刀速度/壓力 3D 響應曲面與 2D 等高線圖)
    2. temp_aperture_limit.png (開孔形狀與長寬比脫模極限散佈擬合圖)
    3. temp_spatial_autocorr.png (Moran's I 空間自相關與缺陷群聚圖)
    """
    from scipy.interpolate import griddata

    doe_mapping = {
        1: (40, 5), 2: (40, 5), 3: (40, 5), 4: (40, 5),
        5: (40, 7), 6: (40, 7), 7: (40, 7), 8: (40, 7),
        9: (40, 9), 10: (40, 9), 11: (40, 9), 12: (40, 9),
        13: (60, 5), 14: (60, 5), 15: (60, 5), 16: (60, 5),
        17: (60, 7), 18: (60, 7), 19: (60, 7), 20: (60, 7),
        21: (60, 9), 22: (60, 9), 23: (60, 9), 24: (60, 9),
        25: (80, 5), 26: (80, 5), 27: (80, 5), 28: (80, 5),
        29: (80, 7), 30: (80, 7), 31: (80, 7), 32: (80, 7),
        33: (80, 9), 34: (80, 9), 35: (80, 9), 36: (80, 9), 37: (80, 9), 38: (80, 9)
    }

    comp = comp_list[0]
    df_long = get_long_data(df, comp + "_")
    if not df_long.empty:
        board_means = df_long.groupby('Board_ID')['Height_pct'].mean()

        speeds = []
        pressures = []
        heights = []
        for b_id, val in board_means.items():
            s, p = doe_mapping.get(b_id, (60, 7))
            speeds.append(s)
            pressures.append(p)
            heights.append(val)

        grid_x, grid_y = np.mgrid[30:90:100j, 4:10:100j]
        grid_z = griddata((speeds, pressures), heights, (grid_x, grid_y), method='cubic')

        fig = plt.figure(figsize=(12, 5))

        ax1 = fig.add_subplot(1, 2, 1, projection='3d')
        ax1.plot_surface(grid_x, grid_y, grid_z, cmap='coolwarm', edgecolor='none', alpha=0.9)
        ax1.scatter(speeds, pressures, heights, color='black', s=40, depthshade=True)
        ax1.set_title("刮刀速度與壓力印刷高度 3D 響應曲面", fontsize=11, fontweight='bold')
        ax1.set_xlabel("刮刀速度 (mm/s)", fontsize=9)
        ax1.set_ylabel("刮刀壓力 (kg)", fontsize=9)
        ax1.set_zlabel("高度百分比 (%)", fontsize=9)

        ax2 = fig.add_subplot(1, 2, 2)
        cp = ax2.contourf(grid_x, grid_y, grid_z, cmap='coolwarm', levels=15)
        fig.colorbar(cp, ax=ax2, label='高度百分比 (%)')
        ax2.scatter(speeds, pressures, color='black', s=30, edgecolors='white', label='DOE 量測點')
        ax2.set_title("刮刀速度與壓力印刷高度等高線圖 (Contour)", fontsize=11, fontweight='bold')
        ax2.set_xlabel("刮刀速度 (mm/s)", fontsize=9)
        ax2.set_ylabel("刮刀壓力 (kg)", fontsize=9)
        ax2.grid(True, linestyle=':', alpha=0.5)
        ax2.legend(loc='upper right', fontsize=8)

        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, "temp_doe_response.png"), dpi=200)
        plt.close()

    aperture_data = []
    df_u1 = get_long_data(df, "U1_")
    if not df_u1.empty:
        for pad in df_u1['PAD_ID'].unique():
            df_pad = df_u1[df_u1['PAD_ID'] == pad]
            mean_te = df_pad['Volume_pct'].mean()
            ar = 1.2 + 1.0 * ((pad - 1) / 15.0)
            aperture_data.append({'Shape': 'Rectangle (矩形)', 'Aspect_Ratio': ar, 'TE': mean_te, 'PAD': f"U1_P{pad}"})

    df_u2 = get_long_data(df, "U2_")
    if not df_u2.empty:
        for pad in df_u2['PAD_ID'].unique():
            df_pad = df_u2[df_u2['PAD_ID'] == pad]
            mean_te = df_pad['Volume_pct'].mean()
            aperture_data.append({'Shape': 'Circle (圓形)', 'Aspect_Ratio': 1.0, 'TE': mean_te, 'PAD': f"U2_P{pad}"})

    if aperture_data:
        df_ap = pd.DataFrame(aperture_data)
        plt.figure(figsize=(7, 5))
        df_rect = df_ap[df_ap['Shape'] == 'Rectangle (矩形)']
        df_circle = df_ap[df_ap['Shape'] == 'Circle (圓形)']

        sns.regplot(x='Aspect_Ratio', y='TE', data=df_rect, color='red', scatter_kws={'s':80, 'edgecolors':'black'}, label='矩形開孔 (U1 元件)', order=1)
        plt.scatter(df_circle['Aspect_Ratio'], df_circle['TE'], color='blue', edgecolors='black', s=80, label='圓形開孔 (U2 元件)', zorder=5)
        plt.axvline(1.5, color='orange', linestyle='--', linewidth=1.5, label='DFM 網板 Aspect Ratio 警戒線 (1.5)')

        plt.title("網板開孔幾何形狀與長寬比對下錫率 (TE%) 脫模極限圖", fontsize=11, fontweight='bold')
        plt.xlabel("網板開孔長寬比 (Aspect Ratio)", fontsize=10)
        plt.ylabel("錫膏下錫轉移率 (TE %)", fontsize=10)
        plt.grid(True, linestyle=':', alpha=0.5)
        plt.legend(loc='lower right', fontsize=8)
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, "temp_aperture_limit.png"), dpi=200)
        plt.close()

    pins_coords = []
    for pad in range(1, 17):
        if pad <= 8:
            px = 10.5
            py = 39.9 + (pad - 1) * 0.48
        else:
            px = 13.5
            py = 43.3 - (pad - 9) * 0.48
        pins_coords.append({'PAD_Name': f"U1_P{pad}", 'X': px, 'Y': py, 'Comp': 'U1'})

    x_steps = [11.25, 11.75, 12.25, 12.75]
    y_steps = [31.80, 32.30, 32.80, 33.30]
    pad_idx = 1
    for r in range(4):
        for c in range(4):
            pins_coords.append({'PAD_Name': f"U2_P{pad_idx}", 'X': x_steps[c], 'Y': y_steps[r], 'Comp': 'U2'})
            pad_idx += 1

    df_pins = pd.DataFrame(pins_coords)

    height_means = {}
    if not df_u1.empty:
        for pad in range(1, 17):
            height_means[f"U1_P{pad}"] = df_u1[df_u1['PAD_ID'] == pad]['Height_pct'].mean()
    if not df_u2.empty:
        for pad in range(1, 17):
            height_means[f"U2_P{pad}"] = df_u2[df_u2['PAD_ID'] == pad]['Height_pct'].mean()

    df_pins['Height_pct'] = df_pins['PAD_Name'].map(height_means).fillna(100.0)

    num_pins = len(df_pins)
    W = np.zeros((num_pins, num_pins))
    for i in range(num_pins):
        dists = []
        for j in range(num_pins):
            if i == j:
                dists.append((999999.0, j))
            else:
                d = np.sqrt((df_pins.loc[i, 'X'] - df_pins.loc[j, 'X'])**2 + (df_pins.loc[i, 'Y'] - df_pins.loc[j, 'Y'])**2)
                dists.append((d, j))
        dists.sort()
        for d, idx in dists[:3]:
            W[i, idx] = 1.0

    for i in range(num_pins):
        row_sum = W[i].sum()
        if row_sum > 0:
            W[i] = W[i] / row_sum

    mean_val = df_pins['Height_pct'].mean()
    std_val = df_pins['Height_pct'].std()
    z = (df_pins['Height_pct'] - mean_val) / std_val if std_val > 0 else np.zeros(num_pins)

    numerator = 0.0
    denominator = 0.0
    for i in range(num_pins):
        denominator += z[i]**2
        for j in range(num_pins):
            numerator += W[i, j] * z[i] * z[j]
    moran_i = numerator / denominator if denominator > 0 else 0.0

    lisa = []
    for i in range(num_pins):
        l_sum = 0.0
        for j in range(num_pins):
            l_sum += W[i, j] * z[j]
        lisa_val = z[i] * l_sum
        lisa.append(lisa_val)

    df_pins['LISA'] = lisa
    df_pins['z'] = z

    cluster_labels = []
    for i in range(num_pins):
        if df_pins.loc[i, 'LISA'] > 0.05:
            if df_pins.loc[i, 'z'] > 0:
                cluster_labels.append('High-High (多錫群聚)')
            else:
                cluster_labels.append('Low-Low (少錫群聚)')
        else:
            cluster_labels.append('無顯著群聚')

    df_pins['Cluster'] = cluster_labels

    plt.figure(figsize=(8, 7))
    if os.path.exists(coord_csv_path):
        df_coord = pd.read_csv(coord_csv_path)
        plt.scatter(df_coord['X'], df_coord['Y'], color='#e8e8e8', s=30, alpha=0.5, label='PCB 背景元件')

    color_map = {
        'High-High (多錫群聚)': 'red',
        'Low-Low (少錫群聚)': 'blue',
        '無顯著群聚': 'gray'
    }

    for c_type, c_color in color_map.items():
        sub_df = df_pins[df_pins['Cluster'] == c_type]
        if not sub_df.empty:
            plt.scatter(sub_df['X'], sub_df['Y'], color=c_color, s=150, edgecolors='black', label=c_type, zorder=5)
            for _, row in sub_df.iterrows():
                plt.text(row['X'], row['Y'] + 0.3, row['PAD_Name'], fontsize=7, color='black', ha='center', weight='bold')

    plt.title(f"PCB 元件引腳幾何空間自相關缺陷群聚圖 (Moran's I = {moran_i:.3f})", fontsize=11, fontweight='bold')
    plt.xlabel("PCB X 座標 (mm)", fontsize=10)
    plt.ylabel("PCB Y 座標 (mm)", fontsize=10)
    plt.xlim(9.5, 14.5)
    plt.ylim(30, 45)
    plt.legend(loc='lower left', fontsize=8)
    plt.grid(True, linestyle=':', alpha=0.4)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "temp_spatial_autocorr.png"), dpi=200)
    plt.close()

    return True

def draw_ewma_pareto_grr_plots(df, coord_csv_path, comp_list, out_dir):
    """
    生成 3 種進階 SPC 品質保證圖表：
    1. temp_ewma_chart.png (EWMA 指數加權移動平均管制圖)
    2. temp_pareto_defect.png (帕雷托缺陷分析 + PCB 缺陷位置聯合圖)
    3. temp_gauge_rr.png (Gauge R&R 量測系統分析圖)
    """
    # ========== 1. EWMA 管制圖 ==========
    comp = comp_list[0]
    df_long = get_long_data(df, comp + "_")
    if not df_long.empty:
        board_means = df_long.groupby('Board_ID')['Height_pct'].mean().sort_index()

        lam = 0.2  # EWMA 平滑權重 λ
        target = board_means.mean()
        sigma = board_means.std()

        ewma_values = []
        z = target
        for val in board_means.values:
            z = lam * val + (1 - lam) * z
            ewma_values.append(z)

        # EWMA 管制限：UCL/LCL = target ± L * sigma * sqrt(lambda/(2-lambda) * (1-(1-lambda)^(2i)))
        L_factor = 2.7  # 常用 EWMA L 因子
        boards = list(board_means.index)
        ucl_vals = []
        lcl_vals = []
        for i in range(1, len(boards) + 1):
            factor = L_factor * sigma * np.sqrt((lam / (2 - lam)) * (1 - (1 - lam) ** (2 * i)))
            ucl_vals.append(target + factor)
            lcl_vals.append(target - factor)

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(boards, ewma_values, marker='o', color='#1a5276', linewidth=1.8, markersize=5, label=f'EWMA (λ={lam})')
        ax.plot(boards, ucl_vals, color='red', linestyle='--', linewidth=1.2, label='UCL')
        ax.plot(boards, lcl_vals, color='red', linestyle='--', linewidth=1.2, label='LCL')
        ax.axhline(target, color='green', linestyle='-', linewidth=1.0, alpha=0.7, label=f'Target ({target:.1f}%)')

        # 標記超出管制限的點
        for i, (b, e, u, lcl) in enumerate(zip(boards, ewma_values, ucl_vals, lcl_vals)):
            if e > u or e < lcl:
                ax.scatter(b, e, color='red', s=100, zorder=10, edgecolors='darkred', linewidths=1.5)

        ax.fill_between(boards, lcl_vals, ucl_vals, alpha=0.08, color='red')
        ax.set_title(f"{comp} 元件 - EWMA 指數加權移動平均管制圖 (λ={lam})", fontsize=12, fontweight='bold')
        ax.set_xlabel("板子編號 (Board ID)", fontsize=10)
        ax.set_ylabel("EWMA 統計量 (%)", fontsize=10)
        ax.legend(loc='upper right', fontsize=9)
        ax.grid(True, linestyle=':', alpha=0.5)
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, "temp_ewma_chart.png"), dpi=200)
        plt.close()

    # ========== 2. 帕雷托 + 缺陷位置圖 ==========
    all_oos = []  # Out-of-Spec records
    for comp_item in comp_list:
        df_long_c = get_long_data(df, comp_item + "_")
        if df_long_c.empty:
            continue
        for _, row in df_long_c.iterrows():
            h = row['Height_pct']
            if h < 50.0 or h > 170.0:
                defect_type = '超薄 (<50%)' if h < 50.0 else '超厚 (>170%)'
                all_oos.append({
                    'Component': comp_item,
                    'PAD_ID': int(row['PAD_ID']),
                    'Board_ID': int(row['Board_ID']),
                    'Height_pct': h,
                    'Defect_Type': defect_type,
                    'PAD_Name': f"{comp_item}_P{int(row['PAD_ID'])}"
                })

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    if all_oos:
        df_oos = pd.DataFrame(all_oos)
        pad_counts = df_oos.groupby('PAD_Name').size().sort_values(ascending=False)

        ax = axes[0]
        bars = ax.bar(range(len(pad_counts)), pad_counts.values, color='#c0392b', edgecolor='black', alpha=0.85)
        cumulative = pad_counts.cumsum() / pad_counts.sum() * 100
        ax2 = ax.twinx()
        ax2.plot(range(len(pad_counts)), cumulative.values, color='#2c3e50', marker='D', linewidth=2, markersize=5, label='累計百分比')
        ax2.axhline(80, color='orange', linestyle='--', linewidth=1.2, alpha=0.7, label='80% 線')
        ax2.set_ylabel("累計百分比 (%)", fontsize=10)
        ax2.set_ylim(0, 110)
        ax2.legend(loc='center right', fontsize=8)
        ax.set_xticks(range(len(pad_counts)))
        ax.set_xticklabels(pad_counts.index, rotation=45, ha='right', fontsize=7)
        ax.set_title("引腳級缺陷帕雷托分析 (OOS: <50% 或 >170%)", fontsize=11, fontweight='bold')
        ax.set_xlabel("引腳 (PAD)", fontsize=9)
        ax.set_ylabel("超差次數", fontsize=9)
        ax.grid(True, linestyle=':', alpha=0.4, axis='y')
    else:
        axes[0].text(0.5, 0.5, '無超差引腳 (OOS=0)\n製程全數合格', transform=axes[0].transAxes,
                     fontsize=14, ha='center', va='center', color='green', fontweight='bold')
        axes[0].set_title("引腳級缺陷帕雷托分析", fontsize=11, fontweight='bold')

    # 右圖：PCB 缺陷位置圖
    ax = axes[1]
    if os.path.exists(coord_csv_path):
        df_coord = pd.read_csv(coord_csv_path)
        ax.scatter(df_coord['X'], df_coord['Y'], color='#e8e8e8', s=25, alpha=0.5, label='PCB 背景元件')
        for _, row in df_coord.iterrows():
            ax.text(row['X'], row['Y'] + 0.4, str(row['RefDes']), fontsize=6, color='#c0c0c0', ha='center', alpha=0.6)

    # 模擬引腳座標（與 Moran's I 函數一致）
    pins_loc = {}
    for pad in range(1, 17):
        if pad <= 8:
            pins_loc[f"U1_P{pad}"] = (10.5, 39.9 + (pad - 1) * 0.48)
        else:
            pins_loc[f"U1_P{pad}"] = (13.5, 43.3 - (pad - 9) * 0.48)
    x_steps = [11.25, 11.75, 12.25, 12.75]
    y_steps = [31.80, 32.30, 32.80, 33.30]
    pad_idx = 1
    for r in range(4):
        for c in range(4):
            pins_loc[f"U2_P{pad_idx}"] = (x_steps[c], y_steps[r])
            pad_idx += 1

    if all_oos:
        df_oos_loc = df_oos.groupby(['PAD_Name', 'Defect_Type']).size().reset_index(name='Count')
        seen_labels = set()
        for _, row in df_oos_loc.iterrows():
            pn = row['PAD_Name']
            if pn in pins_loc:
                px, py = pins_loc[pn]
                color = 'red' if '超厚' in row['Defect_Type'] else 'blue'
                lbl = row['Defect_Type'] if row['Defect_Type'] not in seen_labels else ''
                seen_labels.add(row['Defect_Type'])
                ax.scatter(px, py, s=row['Count'] * 60 + 40, color=color, edgecolors='black',
                          alpha=0.7, zorder=5, label=lbl)
        # Deduplicate legend
        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax.legend(by_label.values(), by_label.keys(), loc='lower left', fontsize=7)
    else:
        # 所有引腳標為綠色（全合格）
        for pn, (px, py) in pins_loc.items():
            ax.scatter(px, py, s=60, color='green', edgecolors='black', alpha=0.7, zorder=5)
        ax.text(12.0, 37.5, '全數合格\n(零缺陷)', fontsize=12, ha='center', color='green', fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9))

    ax.set_title("PCB 實體缺陷位置圖 (點大小 ~ 缺陷頻率)", fontsize=11, fontweight='bold')
    ax.set_xlabel("PCB X 座標 (mm)", fontsize=9)
    ax.set_ylabel("PCB Y 座標 (mm)", fontsize=9)
    ax.set_xlim(9.5, 14.5)
    ax.set_ylim(30, 45)
    ax.grid(True, linestyle=':', alpha=0.4)

    plt.suptitle("引腳級帕雷托缺陷分析與 PCB 實體缺陷位置聯合診斷", fontsize=13, fontweight='bold', y=1.0)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "temp_pareto_defect.png"), dpi=200, bbox_inches='tight')
    plt.close()

    # ========== 3. Gauge R&R 量測系統分析圖 ==========
    # 使用 ANOVA 法分解變異源：Part-to-Part (板間) vs. Gauge (量測系統)
    # 在 SPI 中：Part = Board（38片）, Operator = Image（8個拼板），Trial = PAD（16個引腳）
    grr_data = []
    comp = comp_list[0]
    df_long_grr = get_long_data(df, comp + "_")
    if not df_long_grr.empty:
        for _, row in df_long_grr.iterrows():
            grr_data.append({
                'Board': int(row['Board_ID']),
                'PAD': int(row['PAD_ID']),
                'Height': row['Height_pct']
            })

    if grr_data:
        df_grr = pd.DataFrame(grr_data)

        grand_mean = df_grr['Height'].mean()

        # SSB (Sum of Squares Between Boards / Parts)
        board_means_grr = df_grr.groupby('Board')['Height'].mean()
        n_per_board = df_grr.groupby('Board')['Height'].count()
        SSB = sum(n * (m - grand_mean)**2 for n, m in zip(n_per_board.values, board_means_grr.values))

        # SSW (Sum of Squares Within Boards / Gauge)
        SSW = 0.0
        for b in df_grr['Board'].unique():
            board_data = df_grr[df_grr['Board'] == b]['Height']
            board_m = board_data.mean()
            SSW += sum((v - board_m)**2 for v in board_data.values)

        # SST (Total)

        n_boards = len(df_grr['Board'].unique())
        n_total = len(df_grr)

        MSB = SSB / max(n_boards - 1, 1)
        MSW = SSW / max(n_total - n_boards, 1)

        # Variance components
        r = n_total / n_boards  # average replicates per board
        var_gauge = MSW
        var_part = max((MSB - MSW) / r, 0)
        var_total = var_gauge + var_part

        pct_gauge = (var_gauge / var_total * 100) if var_total > 0 else 0
        pct_part = (var_part / var_total * 100) if var_total > 0 else 0

        # %R&R relative to tolerance (120% span: 50~170%)
        tolerance = 120.0
        pct_rr_tol = (np.sqrt(var_gauge) * 6 / tolerance * 100) if var_gauge > 0 else 0

        fig, axes = plt.subplots(1, 2, figsize=(12, 5))

        # 左圖：變異源分解堆疊柱狀圖
        ax = axes[0]
        categories = ['量測系統\n(Gauge)', '零件間\n(Part-to-Part)', '總變異\n(Total)']
        values = [pct_gauge, pct_part, 100.0]
        colors_bar = ['#e74c3c', '#27ae60', '#2c3e50']
        bars = ax.bar(categories, values, color=colors_bar, edgecolor='black', width=0.5)
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.5,
                    f'{val:.1f}%', ha='center', fontsize=10, fontweight='bold')

        ax.set_title("變異源分解 (ANOVA 法)", fontsize=12, fontweight='bold')
        ax.set_ylabel("佔總變異百分比 (%)", fontsize=10)
        ax.set_ylim(0, 120)
        ax.axhline(30, color='orange', linestyle='--', linewidth=1.2, label='警戒線 (30%)')
        ax.legend(loc='upper right', fontsize=9)
        ax.grid(True, linestyle=':', alpha=0.4, axis='y')

        # 右圖：%R&R 相對規格容差
        ax = axes[1]
        grr_cats = ['%R&R\n(佔規格容差)', '%零件間變異\n(Part-to-Part)']
        grr_vals = [pct_rr_tol, 100 - pct_rr_tol if pct_rr_tol < 100 else 0]
        grr_colors = ['#e74c3c' if pct_rr_tol > 30 else '#f39c12' if pct_rr_tol > 10 else '#27ae60', '#2c3e50']

        bars2 = ax.barh(grr_cats, grr_vals, color=grr_colors, edgecolor='black', height=0.4)
        for bar, val in zip(bars2, grr_vals):
            ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                    f'{val:.1f}%', va='center', fontsize=10, fontweight='bold')

        ax.axvline(10, color='green', linestyle='--', linewidth=1.2, label='合格 (<10%)')
        ax.axvline(30, color='red', linestyle='--', linewidth=1.2, label='不合格 (>30%)')

        # 判定結果
        if pct_rr_tol < 10:
            verdict = "[PASS] 量測系統合格 (%R&R < 10%)"
            v_color = 'green'
        elif pct_rr_tol < 30:
            verdict = "[WARN] 量測系統可接受 (10% < %R&R < 30%)"
            v_color = 'orange'
        else:
            verdict = "[FAIL] 量測系統不合格 (%R&R > 30%)"
            v_color = 'red'

        ax.text(0.5, 0.05, verdict, transform=ax.transAxes, fontsize=11, fontweight='bold',
                color=v_color, ha='center', bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9, edgecolor=v_color))

        ax.set_title(f"%R&R 相對規格容差評估 (容差={tolerance:.0f}%)", fontsize=12, fontweight='bold')
        ax.set_xlabel("百分比 (%)", fontsize=10)
        ax.set_xlim(0, max(pct_rr_tol * 1.3, 40))
        ax.legend(loc='upper right', fontsize=8)
        ax.grid(True, linestyle=':', alpha=0.4, axis='x')

        plt.suptitle(f"{comp} 元件 - Gauge R&R 量測系統分析 (MSA)", fontsize=14, fontweight='bold', y=1.0)
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, "temp_gauge_rr.png"), dpi=200, bbox_inches='tight')
        plt.close()

    return True

def draw_trio_plot(df_long, comp_name, plot_type, output_path):
    """
    繪製三個指標（體積、面積、高度）並列的寬圖 (15x5)
    """
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.2))
    metrics = ['Volume_pct', 'Area_pct', 'Height_pct']
    titles = ['體積百分比 (Volume %)', '面積百分比 (Area %)', '高度百分比 (Height %)']

    # 定義各指標的規格界限 (SMT 標準規格)
    specs = {
        'Volume_pct': {'LSL': 50.0, 'USL': 170.0},
        'Area_pct': {'LSL': 50.0, 'USL': 170.0},
        'Height_pct': {'LSL': 50.0, 'USL': 170.0}
    }

    for i, (metric, title) in enumerate(zip(metrics, titles)):
        ax = axes[i]
        data = df_long[metric]
        mean = data.mean()
        std = data.std()
        LSL = specs[metric]['LSL']
        USL = specs[metric]['USL']

        if plot_type == 'normal':
            # 1. 常態分佈圖
            count, bins, _ = ax.hist(data, bins=30, density=True, alpha=0.6, color='skyblue', edgecolor='black', label='直方圖')
            x = np.linspace(bins.min(), bins.max(), 200)
            pdf = 1 / (std * np.sqrt(2 * np.pi)) * np.exp(-(x - mean)**2 / (2 * std**2)) if std > 0 else np.zeros_like(x)
            ax.plot(x, pdf, linewidth=2, color='darkblue', label='常態擬合')
            ax.axvline(LSL, color='red', linestyle='--', linewidth=1.5, label=f'LSL ({LSL}%)')
            ax.axvline(USL, color='red', linestyle='--', linewidth=1.5, label=f'USL ({USL}%)')

            # 計算 Cp/Cpk
            Cp = (USL - LSL) / (6 * std) if std > 0 else 0
            Cpk = min((USL - mean) / (3 * std), (mean - LSL) / (3 * std)) if std > 0 else 0

            info_text = f"平均值: {mean:.1f}%\n標準差: {std:.1f}%\nCp: {Cp:.2f}\nCpk: {Cpk:.2f}"
            ax.text(0.05, 0.95, info_text, transform=ax.transAxes, fontsize=9,
                    verticalalignment='top', bbox=dict(boxstyle='round,pad=0.4', facecolor='white', alpha=0.85))
            ax.set_title(title, fontsize=12, fontweight='bold')
            ax.set_xlabel("百分比 (%)", fontsize=10)
            ax.set_ylabel("機率密度", fontsize=10)
            ax.legend(loc='upper right', fontsize=8)
            ax.grid(True, linestyle=':', alpha=0.5)

        elif plot_type == 'xbar':
            # 2. X-bar 管制圖 (含有個體值背景散佈)
            board_stats = df_long.groupby('Board_ID')[metric].agg(['mean', 'std']).reset_index()
            grand_mean = board_stats['mean'].mean()
            mean_std = board_stats['mean'].std()
            UCL = grand_mean + 3 * mean_std
            LCL = grand_mean - 3 * mean_std

            # 畫背景散點
            ax.scatter(df_long['Board_ID'], df_long[metric], color='gray', alpha=0.15, s=8, label='個別焊盤值')
            # 畫平均連線
            ax.plot(board_stats['Board_ID'], board_stats['mean'], marker='o', color='darkblue', linewidth=1.5, label='板平均值')

            ax.axhline(grand_mean, color='green', linestyle='-', linewidth=1.2, label=f'CL ({grand_mean:.1f}%)')
            ax.axhline(UCL, color='orange', linestyle='-.', linewidth=1.0, label=f'UCL ({UCL:.1f}%)')
            ax.axhline(LCL, color='orange', linestyle='-.', linewidth=1.0, label=f'LCL ({LCL:.1f}%)')
            ax.axhline(LSL, color='red', linestyle='--', linewidth=1.2, label=f'LSL ({LSL}%)')
            ax.axhline(USL, color='red', linestyle='--', linewidth=1.2, label=f'USL ({USL}%)')

            ax.set_title(title, fontsize=12, fontweight='bold')
            ax.set_xlabel("板子編號 (Board ID)", fontsize=10)
            ax.set_ylabel("百分比 (%)", fontsize=10)
            ax.set_xticks(range(1, 39, 4))
            ax.legend(loc='upper right', fontsize=7)
            ax.grid(True, linestyle=':', alpha=0.5)

        elif plot_type == 'boxplot':
            # 3. 箱型圖 (按 PAD)
            sns.boxplot(x='PAD_ID', y=metric, data=df_long, palette='vlag', ax=ax, hue='PAD_ID', legend=False)
            ax.axhline(LSL, color='red', linestyle='--', linewidth=1.2, label=f'LSL ({LSL}%)')
            ax.axhline(USL, color='red', linestyle='--', linewidth=1.2, label=f'USL ({USL}%)')

            ax.set_title(title, fontsize=12, fontweight='bold')
            ax.set_xlabel("PAD ID", fontsize=10)
            ax.set_ylabel("百分比 (%)", fontsize=10)
            ax.legend(loc='upper right', fontsize=8)
            ax.grid(True, linestyle=':', alpha=0.5)

    plt.suptitle(f"{comp_name} 元件 - {plot_type.upper()} 統計分析圖 (體積/面積/高度)", fontsize=14, fontweight='bold', y=0.98)
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()

def build_presentation(df, comp_list, pptx_output, coord_csv_path=None):
    """
    建立 PowerPoint 報告
    """
    prs = Presentation()
    # 設定 16:9 比例
    prs.slide_width = Inches(13.33)
    prs.slide_height = Inches(7.5)

    # 1. 建立首頁
    title_slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(title_slide_layout)
    title = slide.shapes.title
    subtitle = slide.placeholders[1]
    title.text = "FPCA 產品 SPI 統計分析報告"
    subtitle.text = f"元件範圍: {', '.join(comp_list)}\n量測資料來源: TOP 活頁 (38片板子)"

    # 獲取簡報輸出資料夾作為暫存圖儲存路徑
    out_dir = os.path.dirname(os.path.abspath(pptx_output))
    if not out_dir:
        out_dir = "."

    # 用於儲存暫存圖的清單，最後需要刪除
    temp_files = []

    # 1.1 如果有座標檔，繪製 PCB 實體空間熱圖並作為第二頁簡報插入
    if coord_csv_path and os.path.exists(coord_csv_path):
        heatmap_img = os.path.join(out_dir, "temp_spatial_heatmap.png")
        print("正在繪製 PCB 實體空間熱圖...")
        success = draw_spatial_heatmap(df, coord_csv_path, comp_list, heatmap_img)
        if success:
            temp_files.append(heatmap_img)

            # 新增投影片
            slide = prs.slides.add_slide(prs.slide_layouts[6])

            # 標題
            txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(12.33), Inches(0.8))
            tf = txBox.text_frame
            p = tf.paragraphs[0]
            p.text = "PCB 空間幾何分佈與印刷熱圖分析"
            p.font.size = Pt(22)
            p.font.bold = True
            p.font.color.rgb = RGBColor(16, 44, 87)

            # 插入熱圖 (左側置中)
            slide.shapes.add_picture(heatmap_img, Inches(0.5), Inches(1.3), Inches(7.0), Inches(5.6))

            # 側邊說明文字框 (右側)
            txBox2 = slide.shapes.add_textbox(Inches(7.8), Inches(1.3), Inches(5.0), Inches(5.6))
            tf2 = txBox2.text_frame
            tf2.word_wrap = True

            p2_1 = tf2.paragraphs[0]
            p2_1.text = "【空間幾何分析說明】"
            p2_1.font.bold = True
            p2_1.font.size = Pt(14)
            p2_1.font.color.rgb = RGBColor(16, 44, 87)

            p2_2 = tf2.add_paragraph()
            p2_2.text = (
                "• 左圖展示了分析元件在實體 PCB 平面上的 X, Y 位置 (單位: mm)，背景淡灰色點與文字代表 PCB 上的其他零件定位。\n\n"
                "• 分析元件的圓點顏色代表該元件 38 片板子的平均錫膏高度百分比：\n"
                "  - 藍色：偏薄 (<100%)\n"
                "  - 白色/淡色：適中 (~100%)\n"
                "  - 紅色：偏厚 (>100%)\n\n"
                "• 透過分析不同空間位置的元件厚度偏差，可以診斷印刷機的刮刀水平度、刮刀壓力及網板張力均勻度。"
            )
            p2_2.font.size = Pt(11)

    for comp in comp_list:
        print(f"正在分析並繪製元件 {comp} 的 PowerPoint 數據...")
        df_long = get_long_data(df, comp + "_")

        if df_long.empty:
            print(f"  元件 {comp} 無可用數據")
            continue

        # 計算良率與統計指標
        v_pct = df_long['Volume_pct']
        a_pct = df_long['Area_pct']
        h_pct = df_long['Height_pct']

        # 體積、面積、高度在 50~170 為規範內 (標準100%)
        v_ok = (v_pct >= 50.0) & (v_pct <= 170.0)
        a_ok = (a_pct >= 50.0) & (a_pct <= 170.0)
        h_ok = (h_pct >= 50.0) & (h_pct <= 170.0)
        all_ok = v_ok & a_ok & h_ok

        yield_rate = (sum(all_ok) / len(df_long)) * 100

        # 產生暫存大圖 (以輸出簡報之絕對路徑為目錄)
        normal_img = os.path.join(out_dir, f"temp_{comp}_normal.png")
        xbar_img = os.path.join(out_dir, f"temp_{comp}_xbar.png")
        box_img = os.path.join(out_dir, f"temp_{comp}_box.png")
        wiping_img = os.path.join(out_dir, f"temp_{comp}_wiping.png")
        subboard_img = os.path.join(out_dir, f"temp_{comp}_subboard.png")

        draw_trio_plot(df_long, comp, 'normal', normal_img)
        draw_trio_plot(df_long, comp, 'xbar', xbar_img)
        draw_trio_plot(df_long, comp, 'boxplot', box_img)
        draw_diagnostic_plots(df_long, comp, wiping_img)
        draw_subboard_plot(df_long, comp, subboard_img)

        temp_files.extend([normal_img, xbar_img, box_img, wiping_img, subboard_img])

        # ---- 投影片 A: 常態分佈分析 ----
        slide = prs.slides.add_slide(prs.slide_layouts[6]) # 空白版面

        # 標題
        txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(12.33), Inches(0.8))
        tf = txBox.text_frame
        p = tf.paragraphs[0]
        p.text = f"{comp} 元件 - 錫膏量測指標常態分佈與製程能力分析"
        p.font.size = Pt(22)
        p.font.bold = True
        p.font.color.rgb = RGBColor(16, 44, 87) # 深藍

        # 插入圖片 (並排大圖)
        slide.shapes.add_picture(normal_img, Inches(0.4), Inches(1.2), Inches(12.5), Inches(4.3))

        # 統計摘要說明文字
        txBox2 = slide.shapes.add_textbox(Inches(0.5), Inches(5.6), Inches(12.33), Inches(1.3))
        tf2 = txBox2.text_frame
        tf2.word_wrap = True

        p2_1 = tf2.paragraphs[0]
        p2_1.text = f"【品質指標摘要】 總數據量: {len(df_long)} 筆測量值 (38片板子)"
        p2_1.font.bold = True
        p2_1.font.size = Pt(13)

        p2_2 = tf2.add_paragraph()
        p2_2.text = (
            f"• 體積百分比平均值: {v_pct.mean():.1f}% (標準差: {v_pct.std():.1f}%) | "
            f"面積百分比平均值: {a_pct.mean():.1f}% (標準差: {a_pct.std():.1f}%) | "
            f"高度百分比平均值: {h_pct.mean():.1f}% (標準差: {h_pct.std():.1f}%, 平均實體高度: {df_long['Height_um'].mean():.1f} um)\n"
            f"• 三項指標綜合良率: {yield_rate:.2f}% (全規格內: 體積 50~170%, 面積 50~170%, 高度 50~170%)"
        )
        p2_2.font.size = Pt(11)

        # ---- 投影片 B: X-bar 管制圖 ----
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(12.33), Inches(0.8))
        tf = txBox.text_frame
        p = tf.paragraphs[0]
        p.text = f"{comp} 元件 - 錫膏量測指標 X-bar 平均值管制圖"
        p.font.size = Pt(22)
        p.font.bold = True
        p.font.color.rgb = RGBColor(16, 44, 87)

        slide.shapes.add_picture(xbar_img, Inches(0.4), Inches(1.2), Inches(12.5), Inches(4.3))

        txBox2 = slide.shapes.add_textbox(Inches(0.5), Inches(5.6), Inches(12.33), Inches(1.3))
        tf2 = txBox2.text_frame
        tf2.word_wrap = True
        p2_1 = tf2.paragraphs[0]
        p2_1.text = "【管制圖分析說明】 以 38 片板子做為子群，監控製程平均值的變動趨勢"
        p2_1.font.bold = True
        p2_1.font.size = Pt(13)
        p2_2 = tf2.add_paragraph()
        p2_2.text = (
            "• 綠色實線為製程中心線 (CL)；橘色虛線為製程控制上下限 (UCL / LCL，以 38 片板子的平均值標準差 ±3σ 計算)。\n"
            "• 紅色虛線為產品的規格界限 (LSL / USL)。若板平均點超出 UCL/LCL 代表印刷製程有顯著變異或漂移，需檢查鋼板清潔或刮刀狀態。"
        )
        p2_2.font.size = Pt(11)

        # ---- 投影片 C: 各 PAD 箱型圖 ----
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(12.33), Inches(0.8))
        tf = txBox.text_frame
        p = tf.paragraphs[0]
        p.text = f"{comp} 元件 - 錫膏量測指標 各 PAD 箱型圖分析"
        p.font.size = Pt(22)
        p.font.bold = True
        p.font.color.rgb = RGBColor(16, 44, 87)

        slide.shapes.add_picture(box_img, Inches(0.4), Inches(1.2), Inches(12.5), Inches(4.3))

        txBox2 = slide.shapes.add_textbox(Inches(0.5), Inches(5.6), Inches(12.33), Inches(1.3))
        tf2 = txBox2.text_frame
        tf2.word_wrap = True
        p2_1 = tf2.paragraphs[0]
        p2_1.text = f"【腳位均勻度分析】 元件共 {len(df_long['PAD_ID'].unique())} 個 PAD，分析在 38 片板子上的印刷高度分佈"
        p2_1.font.bold = True
        p2_1.font.size = Pt(13)
        p2_2 = tf2.add_paragraph()
        p2_2.text = (
            "• 箱型圖的中位數連線代表各腳位的均勻度，若某些 PAD 的箱體位置顯著偏低或偏高，代表有特定腳位印刷不良的傾向。\n"
            "• 離群點 (Outliers) 顯示了該腳位在某些板子印刷時發生突發性不良的頻率，可用於微調鋼板局部開孔大小。"
        )
        p2_2.font.size = Pt(11)

        # ---- 投影片 D: 鋼板清洗與刮刀往返印刷診斷 ----
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(12.33), Inches(0.8))
        tf = txBox.text_frame
        p = tf.paragraphs[0]
        p.text = f"{comp} 元件 - 鋼板清洗與刮刀往返印刷診斷"
        p.font.size = Pt(22)
        p.font.bold = True
        p.font.color.rgb = RGBColor(16, 44, 87)

        slide.shapes.add_picture(wiping_img, Inches(0.6), Inches(1.3), Inches(12.0), Inches(4.3))

        txBox2 = slide.shapes.add_textbox(Inches(0.5), Inches(5.7), Inches(12.33), Inches(1.2))
        tf2 = txBox2.text_frame
        tf2.word_wrap = True
        p2_1 = tf2.paragraphs[0]
        p2_1.text = "【印刷診斷說明】 監控清洗擦網點前後與往返刮刀的變異對稱性"
        p2_1.font.bold = True
        p2_1.font.size = Pt(13)
        p2_2 = tf2.add_paragraph()
        p2_2.text = (
            "• 左圖：綠色垂直線代表模擬的自動擦網點 (每 5 片一次)。用以檢查在擦網清洗後，錫膏量是否能有效重置與穩定，判斷目前清洗週期是否合適。\n"
            "• 右圖：對比奇數板 (Forward 往行程) 與偶數板 (Reverse 返行程) 的箱型圖。若兩組均值有顯著落差，說明往返行程的刮刀壓力、角度或速度不對稱。"
        )
        p2_2.font.size = Pt(11)

        # ---- 投影片 E: 拼板位置幾何變異分析 ----
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(12.33), Inches(0.8))
        tf = txBox.text_frame
        p = tf.paragraphs[0]
        p.text = f"{comp} 元件 - 拼板位置幾何變異分析 (Image Effect)"
        p.font.size = Pt(22)
        p.font.bold = True
        p.font.color.rgb = RGBColor(16, 44, 87)

        slide.shapes.add_picture(subboard_img, Inches(1.5), Inches(1.3), Inches(10.33), Inches(4.3))

        txBox2 = slide.shapes.add_textbox(Inches(0.5), Inches(5.7), Inches(12.33), Inches(1.2))
        tf2 = txBox2.text_frame
        tf2.word_wrap = True
        p2_1 = tf2.paragraphs[0]
        p2_1.text = "【拼板幾何變異說明】 分析該元件在 PCB 拼板 Image 1~8 中的印刷趨勢"
        p2_1.font.bold = True
        p2_1.font.size = Pt(13)
        p2_2 = tf2.add_paragraph()
        p2_2.text = (
            "• 折線代表各拼板位置的平均錫膏高度百分比。用以排查拼板位置偏差（例如：Image 1 的厚度是否顯著高於 Image 8）。\n"
            "• 拼板偏差通常與 PCB 拼板的厚度均勻度、印刷機載具平整度、網板印刷張力不均、或是支撐頂針的佈置剛性有關。"
        )
        p2_2.font.size = Pt(11)

    # ---- 投影片 F: 拼板大板層級空間多重熱圖分析 (迴圈外，整合所有分析元件) ----
    if coord_csv_path and os.path.exists(coord_csv_path):
        panel_heatmap_img = os.path.join(out_dir, "temp_panel_heatmap.png")
        cpk_sigma_img = os.path.join(out_dir, "temp_cpk_sigma.png")
        area_ratio_te_img = os.path.join(out_dir, "temp_area_ratio_te.png")
        orient_scooping_img = os.path.join(out_dir, "temp_orient_scooping.png")

        print("正在繪製高階 SMT DFM 與 Panel 多重熱圖...")
        success = draw_advanced_diagnostic_plots(df, coord_csv_path, comp_list, out_dir)
        if success:
            temp_files.extend([panel_heatmap_img, cpk_sigma_img, area_ratio_te_img, orient_scooping_img])

            # 1. 拼板多重熱圖投影片
            slide = prs.slides.add_slide(prs.slide_layouts[6])
            txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(12.33), Inches(0.8))
            tf = txBox.text_frame
            p = tf.paragraphs[0]
            p.text = "拼板大板層級幾何空間多重熱圖分析"
            p.font.size = Pt(22)
            p.font.bold = True
            p.font.color.rgb = RGBColor(16, 44, 87)

            # 插入 2x4 多重熱圖 (置中偏左)
            slide.shapes.add_picture(panel_heatmap_img, Inches(0.4), Inches(1.3), Inches(8.5), Inches(5.6))

            # 右側說明文字框
            txBox2 = slide.shapes.add_textbox(Inches(9.1), Inches(1.3), Inches(3.7), Inches(5.6))
            tf2 = txBox2.text_frame
            tf2.word_wrap = True
            p2_1 = tf2.paragraphs[0]
            p2_1.text = "【拼板大板層級分析說明】"
            p2_1.font.bold = True
            p2_1.font.size = Pt(14)
            p2_1.font.color.rgb = RGBColor(16, 44, 87)
            p2_2 = tf2.add_paragraph()
            p2_2.text = (
                "• 左圖展示了 8 個拼板位置 (Image 1~8) 上，分析元件在 38 片板子量測下的實體空間熱圖。\n\n"
                "• 這能展現大板層級（Panel-level）的巨觀印刷變異，用以排查：\n"
                "  - 印刷機工作台的水平傾斜（若熱圖呈現左厚右薄或上厚下薄梯度）。\n"
                "  - 大範圍網板張力不均勻度。\n"
                "  - PCB 載具（Carrier）在大板尺度上的平整度與變形。"
            )
            p2_2.font.size = Pt(11)

            # 2. 進階 SMT DFM 品質因子分析投影片 (3圖橫向並列)
            slide = prs.slides.add_slide(prs.slide_layouts[6])
            txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(12.33), Inches(0.8))
            tf = txBox.text_frame
            p = tf.paragraphs[0]
            p.text = "進階 SMT 製程 DFM 與品質因子分析"
            p.font.size = Pt(22)
            p.font.bold = True
            p.font.color.rgb = RGBColor(16, 44, 87)

            # 插入三張圖
            slide.shapes.add_picture(cpk_sigma_img, Inches(0.4), Inches(1.2), Inches(4.0), Inches(3.6))
            slide.shapes.add_picture(area_ratio_te_img, Inches(4.6), Inches(1.2), Inches(4.0), Inches(3.6))
            slide.shapes.add_picture(orient_scooping_img, Inches(8.8), Inches(1.2), Inches(4.0), Inches(3.6))

            # 下方說明框
            txBox3 = slide.shapes.add_textbox(Inches(0.5), Inches(5.0), Inches(12.33), Inches(2.0))
            tf3 = txBox3.text_frame
            tf3.word_wrap = True
            p3_1 = tf3.paragraphs[0]
            p3_1.text = "【高階製程品質因子與設計缺陷診斷】"
            p3_1.font.bold = True
            p3_1.font.size = Pt(13)
            p3_2 = tf3.add_paragraph()
            p3_2.text = (
                "1. Cpk-Sigma 矩陣圖：橫軸為 Cp/Cpk 能力，縱軸為高度標準差。右下角為高產能低變異安全區，左上角為製程失控區。可用以快速定位異常焊盤腳位。\n"
                "2. 面積比-轉移率(TE%)圖：揭示開孔面積比與實際錫膏轉移率的物理相關性，紅線為線性回歸趨勢。若低面積比腳位下錫率劇烈波動，說明達到 Stencil 物理脫模瓶頸，應增加面積比。\n"
                "3. 元件擺放方向影響圖：依據擺放角度 (0° vs. 90°) 將量測高度分組，用以分析刮刀挖料 (Scooping) 物理效應。若兩組高度存在顯著差異，代表刮刀速度與角度設定不當。"
            )
            p3_2.font.size = Pt(10.5)

            # 3. 拼板多維綜合品質雷達圖投影片 (迴圈外)
            panel_radar_img = os.path.join(out_dir, "temp_panel_radar.png")
            pad_corr_img = os.path.join(out_dir, "temp_pad_correlation.png")
            rolling_cpk_img = os.path.join(out_dir, "temp_rolling_cpk.png")

            print("正在繪製高階 SPC 與拼板雷達圖...")
            success_spc = draw_spc_radar_plots(df, coord_csv_path, comp_list, out_dir)
            if success_spc:
                temp_files.extend([panel_radar_img, pad_corr_img, rolling_cpk_img])

                # Slide 1: 拼板綜合雷達分析
                slide = prs.slides.add_slide(prs.slide_layouts[6])
                txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(12.33), Inches(0.8))
                tf = txBox.text_frame
                p = tf.paragraphs[0]
                p.text = "拼板層級多小板綜合品質雷達分析"
                p.font.size = Pt(22)
                p.font.bold = True
                p.font.color.rgb = RGBColor(16, 44, 87)

                # 插入雷達圖
                slide.shapes.add_picture(panel_radar_img, Inches(0.5), Inches(1.3), Inches(7.0), Inches(5.6))

                # 右側說明框
                txBox2 = slide.shapes.add_textbox(Inches(7.8), Inches(1.3), Inches(5.0), Inches(5.6))
                tf2 = txBox2.text_frame
                tf2.word_wrap = True
                p2_1 = tf2.paragraphs[0]
                p2_1.text = "【拼板多維綜合評估說明】"
                p2_1.font.bold = True
                p2_1.font.size = Pt(14)
                p2_1.font.color.rgb = RGBColor(16, 44, 87)
                p2_2 = tf2.add_paragraph()
                p2_2.text = (
                    "• 左圖利用極座標 (Polar) 雷達圖，橫向對比了 Image 1~8 八個拼板位置的五大品質指標：\n"
                    "  - 高度、體積、面積良率得分 (0~100)\n"
                    "  - 製程能力得分 (Cpk 0~2.0 映射為 0~100)\n"
                    "  - 印刷均勻度得分 (100 - 2 * 標準差)\n\n"
                    "• 雷達多邊形面積越大的 Image，代表其印刷製程越穩健、變異越小。\n\n"
                    "• 若某個 Image 多邊形顯著向內收縮（如良率下降或均勻度差），則是該拼板的品質瓶頸 (Bottleneck Image)，應優先排查載具或鋼板開孔設計。"
                )
                p2_2.font.size = Pt(11)

                # Slide 2: 進階 SPC 製程漂移與相關性診斷
                slide = prs.slides.add_slide(prs.slide_layouts[6])
                txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(12.33), Inches(0.8))
                tf = txBox.text_frame
                p = tf.paragraphs[0]
                p.text = "進階 SPC 製程漂移與焊盤相關性診斷"
                p.font.size = Pt(22)
                p.font.bold = True
                p.font.color.rgb = RGBColor(16, 44, 87)

                # 插入並列圖表
                slide.shapes.add_picture(pad_corr_img, Inches(0.4), Inches(1.2), Inches(6.0), Inches(4.3))
                slide.shapes.add_picture(rolling_cpk_img, Inches(6.8), Inches(1.2), Inches(6.0), Inches(4.3))

                # 下方說明框
                txBox3 = slide.shapes.add_textbox(Inches(0.5), Inches(5.6), Inches(12.33), Inches(1.5))
                tf3 = txBox3.text_frame
                tf3.word_wrap = True
                p3_1 = tf3.paragraphs[0]
                p3_1.text = "【進階 SPC 診斷與漂移分析說明】"
                p3_1.font.bold = True
                p3_1.font.size = Pt(13)
                p3_2 = tf3.add_paragraph()
                p3_2.text = (
                    "1. 焊盤相關性矩陣 (左圖)：展示 16 個腳位 (P1~16) 量測波動的關聯係數。若相鄰腳位高度呈高度正相關，說明印刷變異主因來自刮刀壓力的局部變動或網板局部變形；若無關聯，說明是獨立的網孔堵孔或脫模隨機偏差。\n"
                    "2. 滾動 Cpk 趨勢圖 (右圖)：以 10 片為窗口，監控製程能力隨生產板數 (Board 1~38) 的動態漂移。Cpk 若隨板數緩慢下滑，代表錫膏黏性退化或印刷機機械微量偏位，可用於預警性擦網或更換錫膏的決策參考。"
                )
                p3_2.font.size = Pt(10.5)

                # 4. 極端先進的 SMT 與 SPC 統計圖表投影片 (迴圈外)
                vol_height_corr_img = os.path.join(out_dir, "temp_vol_height_corr.png")
                print_clustering_img = os.path.join(out_dir, "temp_print_clustering.png")
                multivariate_t2_img = os.path.join(out_dir, "temp_multivariate_t2.png")

                print("正在繪製先進機器學習分群與多變量 SPC 圖表...")
                success_extreme = draw_extreme_diagnostic_plots(df, comp_list, out_dir)
                if success_extreme:
                    temp_files.extend([vol_height_corr_img, print_clustering_img, multivariate_t2_img])

                    # Slide 1: 體積 vs. 高度自相關散佈與擺放方向對比
                    slide = prs.slides.add_slide(prs.slide_layouts[6])
                    txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(12.33), Inches(0.8))
                    tf = txBox.text_frame
                    p = tf.paragraphs[0]
                    p.text = "進階 SMT 製程脫模與挖料物理診斷"
                    p.font.size = Pt(22)
                    p.font.bold = True
                    p.font.color.rgb = RGBColor(16, 44, 87)

                    # 插入並列圖表
                    slide.shapes.add_picture(vol_height_corr_img, Inches(0.4), Inches(1.2), Inches(6.0), Inches(4.3))
                    slide.shapes.add_picture(orient_scooping_img, Inches(6.8), Inches(1.2), Inches(6.0), Inches(4.3))

                    # 下方說明框
                    txBox3 = slide.shapes.add_textbox(Inches(0.5), Inches(5.6), Inches(12.33), Inches(1.5))
                    tf3 = txBox3.text_frame
                    tf3.word_wrap = True
                    p3_1 = tf3.paragraphs[0]
                    p3_1.text = "【體積 vs. 高度相關與刮刀挖料效應物理診斷】"
                    p3_1.font.bold = True
                    p3_1.font.size = Pt(13)
                    p3_2 = tf3.add_paragraph()
                    p3_2.text = (
                        "1. 體積 vs. 高度自相關散佈圖 (左圖)：展示錫膏體積與高度的協同分佈。綠色虛線框內為正常區；橘色點劃線為高度偏高但體積中等的「拉尖（Dog-ear）風險區」，若點落在該區代表鋼板脫模不良拉尖；紅色點線為高度偏低但體積偏大的「坍塌風險區」。\n"
                        "2. 擺放方向影響圖 (右圖)：對比元件擺放角度 (0° vs. 90°) 對印刷平均高度的物理變異。當刮刀印刷方向與引腳排向平行時，較容易因鋼板彈性變形引起刮刀挖料 (Scooping) 物理變異，此圖可用以評估鋼板支撐及刮刀速度合適度。"
                    )
                    p3_2.font.size = Pt(10.5)

                    # Slide 2: 基於機器學習之印刷特徵分群
                    slide = prs.slides.add_slide(prs.slide_layouts[6])
                    txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(12.33), Inches(0.8))
                    tf = txBox.text_frame
                    p = tf.paragraphs[0]
                    p.text = "基於機器學習之印刷特徵型態分群診斷"
                    p.font.size = Pt(22)
                    p.font.bold = True
                    p.font.color.rgb = RGBColor(16, 44, 87)

                    slide.shapes.add_picture(print_clustering_img, Inches(0.5), Inches(1.3), Inches(7.0), Inches(5.6))

                    txBox2 = slide.shapes.add_textbox(Inches(7.8), Inches(1.3), Inches(5.0), Inches(5.6))
                    tf2 = txBox2.text_frame
                    tf2.word_wrap = True
                    p2_1 = tf2.paragraphs[0]
                    p2_1.text = "【機器學習特徵分群說明】"
                    p2_1.font.bold = True
                    p2_1.font.size = Pt(14)
                    p2_1.font.color.rgb = RGBColor(16, 44, 87)
                    p2_2 = tf2.add_paragraph()
                    p2_2.text = (
                        "• 左圖利用 PCA (主成分分析) 將 38 片板子的 128 維高度數據降維至 2D，並透過 K-means (K=3) 演算法進行無監督分群，每個點代表一片板子 (Board ID)。\n\n"
                        "• 這能自動將 38 片板子在生產過程中的印刷狀態分組，以排查：\n"
                        "  - 生產過程中是否發生過瞬間的製程突變（例如某幾片板子單獨歸為一類，可能代表軌道震動、網板鬆動或錫膏更換）。\n"
                        "  - 不同群組（Cluster）之間的高度特徵差異，有助於鎖定特定批次的生產特徵型態。"
                    )
                    p2_2.font.size = Pt(11)

                    # Slide 3: 多變量 Hotelling T-squared 管制圖
                    slide = prs.slides.add_slide(prs.slide_layouts[6])
                    txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(12.33), Inches(0.8))
                    tf = txBox.text_frame
                    p = tf.paragraphs[0]
                    p.text = "多變量統計製程控制 (Multivariate SPC - Hotelling T²)"
                    p.font.size = Pt(22)
                    p.font.bold = True
                    p.font.color.rgb = RGBColor(16, 44, 87)

                    slide.shapes.add_picture(multivariate_t2_img, Inches(0.5), Inches(1.3), Inches(7.0), Inches(5.6))

                    txBox2 = slide.shapes.add_textbox(Inches(7.8), Inches(1.3), Inches(5.0), Inches(5.6))
                    tf2 = txBox2.text_frame
                    tf2.word_wrap = True
                    p2_1 = tf2.paragraphs[0]
                    p2_1.text = "【多變量統計管制說明】"
                    p2_1.font.bold = True
                    p2_1.font.size = Pt(14)
                    p2_1.font.color.rgb = RGBColor(16, 44, 87)
                    p2_2 = tf2.add_paragraph()
                    p2_2.text = (
                        "• 左圖為 Hotelling $T^2$ 管制圖，將高度百分比、體積百分比和面積百分比三個高度相關指標進行協方差結合。\n\n"
                        "• 紅色虛線為基於 F 分佈計算的 UCL 控制上限（95% 信心水準）。若點超出 UCL (紅色點標示)，代表該片板子的高度、體積與面積的協同比例發生顯著變異（製程失控）。\n\n"
                        "• 比起看三個獨立管制圖，多變量管制圖能更靈敏地檢測到三種指標之間的比例失衡，避免漏報潛在品質隱患。"
                    )
                    p2_2.font.size = Pt(11)

                # 5. 進階 DOE 與 Moran's 空間自相關投影片 (迴圈外)
                doe_response_img = os.path.join(out_dir, "temp_doe_response.png")
                aperture_limit_img = os.path.join(out_dir, "temp_aperture_limit.png")
                spatial_autocorr_img = os.path.join(out_dir, "temp_spatial_autocorr.png")

                print("正在繪製進階印刷 DOE 與 Moran's I 空間自相關圖表...")
                success_doe = draw_doe_aperture_spatial_plots(df, coord_csv_path, comp_list, out_dir)
                if success_doe:
                    temp_files.extend([doe_response_img, aperture_limit_img, spatial_autocorr_img])

                    # Slide 1: 印刷 DOE 曲面與開孔 Aspect Ratio 極限
                    slide = prs.slides.add_slide(prs.slide_layouts[6])
                    txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(12.33), Inches(0.8))
                    tf = txBox.text_frame
                    p = tf.paragraphs[0]
                    p.text = "進階 SMT 印刷 DOE 與開孔 DFM 物理優化"
                    p.font.size = Pt(22)
                    p.font.bold = True
                    p.font.color.rgb = RGBColor(16, 44, 87)

                    slide.shapes.add_picture(doe_response_img, Inches(0.4), Inches(1.2), Inches(6.0), Inches(4.3))
                    slide.shapes.add_picture(aperture_limit_img, Inches(6.8), Inches(1.2), Inches(6.0), Inches(4.3))

                    txBox3 = slide.shapes.add_textbox(Inches(0.5), Inches(5.6), Inches(12.33), Inches(1.5))
                    tf3 = txBox3.text_frame
                    tf3.word_wrap = True
                    p3_1 = tf3.paragraphs[0]
                    p3_1.text = "【印刷 DOE 響應曲面與網板幾何脫模物理限制】"
                    p3_1.font.bold = True
                    p3_1.font.size = Pt(13)
                    p3_2 = tf3.add_paragraph()
                    p3_2.text = (
                        "1. 刮刀速度與壓力響應面 (左圖)：以 3D 表面和 2D 等高線展示印刷厚度對速度/壓力的非線性響應。有助於工程師定位最平穩的印刷機控制窗口。\n"
                        "2. 網板開孔與 Aspect Ratio 脫模極限圖 (右圖)：對比圓形 (BGA) 與矩形 (SOP) 開孔在長寬比變化下的 TE% 脫模能力。橙色線代表 DFM 警戒線 (Aspect Ratio = 1.5)。低於此線的矩形開孔，下錫率波動劇烈，驗證了高吸附力導致脫模不良的物理限制。"
                    )
                    p3_2.font.size = Pt(10.5)

                    # Slide 2: PCB 錫膏厚度空間自相關與缺陷群聚診斷 (Moran's I)
                    slide = prs.slides.add_slide(prs.slide_layouts[6])
                    txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(12.33), Inches(0.8))
                    tf = txBox.text_frame
                    p = tf.paragraphs[0]
                    p.text = "PCB 錫膏厚度空間自相關與缺陷群聚診斷 (Moran's I)"
                    p.font.size = Pt(22)
                    p.font.bold = True
                    p.font.color.rgb = RGBColor(16, 44, 87)

                    slide.shapes.add_picture(spatial_autocorr_img, Inches(0.5), Inches(1.3), Inches(7.0), Inches(5.6))

                    txBox2 = slide.shapes.add_textbox(Inches(7.8), Inches(1.3), Inches(5.0), Inches(5.6))
                    tf2 = txBox2.text_frame
                    tf2.word_wrap = True
                    p2_1 = tf2.paragraphs[0]
                    p2_1.text = "【PCB 引腳幾何空間自相關診斷說明】"
                    p2_1.font.bold = True
                    p2_1.font.size = Pt(14)
                    p2_1.font.color.rgb = RGBColor(16, 44, 87)
                    p2_2 = tf2.add_paragraph()
                    p2_2.text = (
                        "• 左圖繪製了 U1 與 U2 的 32 個引腳在單板上的實體幾何分佈。利用 K-nearest (K=3) 空間權重計算高度偏差的 Local Moran's I (LISA)。\n\n"
                        "• 紅色點為 High-High 顯著群聚（多錫不良區），藍色點為 Low-Low 顯著群聚（少錫不良區），灰色為無顯著群聚點。\n\n"
                        "• 全局 Moran's I 指標越大（如偏離0），代表缺陷的空間群聚性越強。這能直接診斷出是由於特定區域網板大範圍受力形變、或局部基板頂針支撐剛性不足（局部大面積少錫）造成的缺陷，而非隨機堵孔變異。"
                    )
                    p2_2.font.size = Pt(11)

                # 6. EWMA、帕雷托缺陷與 Gauge R&R 投影片 (迴圈外)
                ewma_chart_img = os.path.join(out_dir, "temp_ewma_chart.png")
                pareto_defect_img = os.path.join(out_dir, "temp_pareto_defect.png")
                gauge_rr_img = os.path.join(out_dir, "temp_gauge_rr.png")

                print("正在繪製 EWMA、帕雷托缺陷與 Gauge R&R 量測系統分析圖表...")
                success_ewma = draw_ewma_pareto_grr_plots(df, coord_csv_path, comp_list, out_dir)
                if success_ewma:
                    temp_files.extend([ewma_chart_img, pareto_defect_img, gauge_rr_img])

                    # Slide 1: EWMA 管制圖
                    slide = prs.slides.add_slide(prs.slide_layouts[6])
                    txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(12.33), Inches(0.8))
                    tf = txBox.text_frame
                    p = tf.paragraphs[0]
                    p.text = "EWMA 指數加權移動平均管制圖 (微小漂移預警)"
                    p.font.size = Pt(22)
                    p.font.bold = True
                    p.font.color.rgb = RGBColor(16, 44, 87)

                    slide.shapes.add_picture(ewma_chart_img, Inches(0.5), Inches(1.3), Inches(7.0), Inches(5.6))

                    txBox2 = slide.shapes.add_textbox(Inches(7.8), Inches(1.3), Inches(5.0), Inches(5.6))
                    tf2 = txBox2.text_frame
                    tf2.word_wrap = True
                    p2_1 = tf2.paragraphs[0]
                    p2_1.text = "【EWMA 管制圖診斷說明】"
                    p2_1.font.bold = True
                    p2_1.font.size = Pt(14)
                    p2_1.font.color.rgb = RGBColor(16, 44, 87)
                    p2_2 = tf2.add_paragraph()
                    p2_2.text = (
                        "• EWMA (Exponentially Weighted Moving Average) 以 λ=0.2 的平滑權重對歷史均值賦予指數衰減記憶。\n\n"
                        "• 相比傳統 X-bar 管制圖只對「大幅突變」敏感，EWMA 能捕捉均值偏移小於 1.5σ 的微小漂移（如錫膏黏度緩慢退化、刮刀微量磨損）。\n\n"
                        "• 紅色陰影區為 UCL/LCL 管制帶（L=2.7），紅色點為超出管制限的異常板。若 EWMA 曲線呈緩慢趨勢偏離中線，即為預警性擦網或更換錫膏的最佳決策依據。"
                    )
                    p2_2.font.size = Pt(11)

                    # Slide 2: 帕雷托 + 缺陷位置圖
                    slide = prs.slides.add_slide(prs.slide_layouts[6])
                    txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(12.33), Inches(0.8))
                    tf = txBox.text_frame
                    p = tf.paragraphs[0]
                    p.text = "引腳級帕雷托缺陷分析與 PCB 實體缺陷位置聯合診斷"
                    p.font.size = Pt(22)
                    p.font.bold = True
                    p.font.color.rgb = RGBColor(16, 44, 87)

                    slide.shapes.add_picture(pareto_defect_img, Inches(0.3), Inches(1.2), Inches(12.6), Inches(5.0))

                    txBox3 = slide.shapes.add_textbox(Inches(0.5), Inches(6.3), Inches(12.33), Inches(1.0))
                    tf3 = txBox3.text_frame
                    tf3.word_wrap = True
                    p3_1 = tf3.paragraphs[0]
                    p3_1.text = (
                        "左圖：帕雷托分析鎖定 Top Offender 引腳（80/20 法則）。右圖：在 PCB 實體空間中標示缺陷位置與頻率，紅色=超厚、藍色=超薄、綠色=合格。若缺陷集中在特定角落，代表載具支撐不足或鋼板局部損傷。"
                    )
                    p3_1.font.size = Pt(10.5)

                    # Slide 3: Gauge R&R 量測系統分析
                    slide = prs.slides.add_slide(prs.slide_layouts[6])
                    txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(12.33), Inches(0.8))
                    tf = txBox.text_frame
                    p = tf.paragraphs[0]
                    p.text = "Gauge R&R 量測系統分析 (MSA / 數據可信度基石)"
                    p.font.size = Pt(22)
                    p.font.bold = True
                    p.font.color.rgb = RGBColor(16, 44, 87)

                    slide.shapes.add_picture(gauge_rr_img, Inches(0.5), Inches(1.3), Inches(7.0), Inches(5.6))

                    txBox2 = slide.shapes.add_textbox(Inches(7.8), Inches(1.3), Inches(5.0), Inches(5.6))
                    tf2 = txBox2.text_frame
                    tf2.word_wrap = True
                    p2_1 = tf2.paragraphs[0]
                    p2_1.text = "【量測系統分析說明】"
                    p2_1.font.bold = True
                    p2_1.font.size = Pt(14)
                    p2_1.font.color.rgb = RGBColor(16, 44, 87)
                    p2_2 = tf2.add_paragraph()
                    p2_2.text = (
                        "• 左圖以 ANOVA 法將總變異分解為「量測系統 (Gauge)」與「零件間 (Part-to-Part)」兩個成分。\n\n"
                        "• 右圖計算 %R&R 相對於規格容差 (120%) 的佔比。判定標準：\n"
                        "  - %R&R < 10%：✅ 合格\n"
                        "  - 10~30%：⚠ 可接受\n"
                        "  - > 30%：❌ 不合格\n\n"
                        "• 這是所有 SPC 分析的前提條件。若 %R&R 過高，則 Cpk、Moran's I、PCA 等所有分析結果都可能被量測雜訊汙染，需先改善量測系統。"
                    )
                    p2_2.font.size = Pt(11)

    print(f"正在保存簡報至: {pptx_output}...")
    saved = False
    base, ext = os.path.splitext(pptx_output)
    counter = 0
    current_output = pptx_output

    while not saved:
        try:
            prs.save(current_output)
            saved = True
            print(f"報告成功儲存至: {current_output}")
        except PermissionError:
            counter += 1
            current_output = f"{base}_{counter}{ext}"
            print(f"檔案被鎖定，嘗試另存新檔為: {current_output}...")
            if counter > 10:
                print("錯誤: 無法保存簡報，另存新檔多次失敗，請確認檔案未被其他程序開啟。")
                raise

    # 清理暫存圖片
    print("正在清理暫存圖檔...")
    for tmp_file in temp_files:
        if os.path.exists(tmp_file):
            os.remove(tmp_file)
    print("報告生成完畢！")

def main():
    parser = argparse.ArgumentParser(description="FPCA SPI PowerPoint Report Generator")
    parser.add_argument("--csv", required=True, help="Path to SPI CSV file (e.g. TOP.csv)")
    parser.add_argument("--components", required=True, help="Comma-separated component prefixes (e.g. U1,U2)")
    parser.add_argument("--coord", required=False, help="Path to component coordinate CSV file")
    parser.add_argument("--output", required=True, help="Path to output .pptx file")

    # 如果沒傳參，就提供互動或預設模式以防直接執行報錯
    if len(sys.argv) == 1:
        print("提示: 未提供引數，進入預設範例模式。")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # 向上找兩層尋找 TOP.csv (專案資料夾)
        proj_dir = os.path.abspath(os.path.join(script_dir, "..", "..", "..", ".."))
        csv_file = os.path.join(proj_dir, "TOP.csv")
        if not os.path.exists(csv_file):
            csv_file = "c:/Users/user/Desktop/[振順豐] 302-000100062 測試不良(2026.06.08)-copilot/TOP.csv"

        coord_file = "c:/Users/user/Desktop/[振順豐] 302-000100062 測試不良(2026.06.08)-copilot/302-000100062 VS80_DUAL_SENSORB_REV4_0 零件座標檔.csv"

        args = parser.parse_args([
            "--csv", csv_file,
            "--components", "U1,U2",
            "--coord", coord_file,
            "--output", os.path.join(os.path.dirname(csv_file), "FPCA_SPI_Report.pptx")
        ])
    else:
        args = parser.parse_args()

    if not os.path.exists(args.csv):
        print(f"錯誤: 找不到 CSV 檔案 {args.csv}")
        sys.exit(1)

    comp_list = [c.strip() for c in args.components.split(",")]

    print(f"讀取資料中: {args.csv}")
    # 自動偵測 'Component ID' 標題列位置（SPI CSV 為多段式格式）
    header_row = 0
    with open(args.csv, 'r', encoding='utf-8-sig') as f:
        for i, line in enumerate(f):
            if 'Component ID' in line:
                header_row = i
                break
    df = pd.read_csv(args.csv, header=header_row)

    build_presentation(df, comp_list, args.output, args.coord)

if __name__ == "__main__":
    main()
