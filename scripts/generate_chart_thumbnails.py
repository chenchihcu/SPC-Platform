import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# Ensure directory exists
out_dir = "assets/chart_legends"
os.makedirs(out_dir, exist_ok=True)

# Settings for thumbnails
plt.style.use('dark_background')  # Match the app's dark theme
FIG_SIZE = (6, 4)
DPI = 300

def save_fig(name):
    path = os.path.join(out_dir, f"{name}.png")
    plt.tight_layout(pad=0.5)
    plt.savefig(path, dpi=DPI, format='png', facecolor='#1e1e1e', edgecolor='#444444')
    plt.close()

def setup_ax(ax):
    # Hide ticks but keep spines
    ax.set_xticks([])
    ax.set_yticks([])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#555555')
    ax.spines['bottom'].set_color('#555555')
    ax.spines['left'].set_linewidth(2)
    ax.spines['bottom'].set_linewidth(2)
    ax.grid(True, color='#444444', linestyle='--', alpha=0.5)
    
def plot_control_chart(name, points=30):
    fig, ax = plt.subplots(figsize=FIG_SIZE)
    setup_ax(ax)
    x = np.arange(points)
    y = np.random.normal(0, 1, points)
    # Add an outlier
    y[points//2] = 3.5
    
    # limits
    ax.axhline(3, color='#fa5252', linestyle='--', lw=2, alpha=0.8)
    ax.axhline(-3, color='#fa5252', linestyle='--', lw=2, alpha=0.8)
    ax.axhline(0, color='#adb5bd', linestyle='-', lw=1.5, alpha=0.7)
    
    # line
    ax.plot(x, y, color='#4dabf7', marker='o', markersize=6, lw=2, markeredgecolor='white', markeredgewidth=1)
    # highlight outlier
    ax.plot(points//2, 3.5, color='#fa5252', marker='o', markersize=8)
    save_fig(name)

def plot_trend_chart(name, points=40):
    fig, ax = plt.subplots(figsize=FIG_SIZE)
    setup_ax(ax)
    x = np.arange(points)
    y = np.cumsum(np.random.normal(0, 0.5, points))
    ax.plot(x, y, color='#ff922b', lw=3, solid_capstyle='round')
    ax.fill_between(x, y, y.min(), alpha=0.1, color='#ff922b')
    save_fig(name)

def plot_histogram(name):
    fig, ax = plt.subplots(figsize=FIG_SIZE)
    setup_ax(ax)
    data = np.random.normal(0, 1, 2000)
    counts, bins, patches = ax.hist(data, bins=25, color='#3bc9db', alpha=0.85, edgecolor='black', linewidth=1)
    # Overlap a normal curve
    import scipy.stats as stats
    x = np.linspace(-4, 4, 100)
    pdf = stats.norm.pdf(x, 0, 1) * max(counts) / stats.norm.pdf(0, 0, 1)
    ax.plot(x, pdf, color='#fcc419', lw=3)
    # limits
    ax.axvline(2.5, color='#fa5252', linestyle='--', lw=2.5)
    ax.axvline(-2.5, color='#fa5252', linestyle='--', lw=2.5)
    ax.set_ylim(0, max(counts) * 1.1)
    save_fig(name)

def plot_boxplot(name):
    fig, ax = plt.subplots(figsize=FIG_SIZE)
    setup_ax(ax)
    data = [np.random.normal(0, std, 50) + offset for std, offset in zip([1, 1.5, 0.8, 1.2], [-0.5, 0, 0.5, 0])]
    boxprops = dict(facecolor='#845ef7', color='#d0bfff', linewidth=2)
    whiskerprops = dict(color='#d0bfff', linewidth=2)
    capprops = dict(color='#d0bfff', linewidth=2)
    medianprops = dict(color='#ffd43b', linewidth=3)
    flierprops = dict(marker='o', markerfacecolor='#fa5252', markersize=5, linestyle='none', markeredgecolor='none')
    
    ax.boxplot(data, patch_artist=True, boxprops=boxprops, vert=True,
               whiskerprops=whiskerprops, capprops=capprops,
               medianprops=medianprops, flierprops=flierprops)
    save_fig(name)

def plot_scatter(name):
    fig, ax = plt.subplots(figsize=FIG_SIZE)
    setup_ax(ax)
    x = np.random.normal(0, 1, 150)
    y = x * 0.7 + np.random.normal(0, 0.6, 150)
    ax.scatter(x, y, color='#51cf66', alpha=0.7, s=40, edgecolor='#2b8a3e', linewidth=1)
    # limit box
    rect = Rectangle((-1.5, -1.5), 3, 3, fill=False, color='#fa5252', lw=2.5, linestyle='--')
    ax.add_patch(rect)
    save_fig(name)

def plot_heatmap(name):
    fig, ax = plt.subplots(figsize=FIG_SIZE)
    ax.axis('off')
    # Generate smoothed spatial data
    x = np.linspace(-3, 3, 30)
    y = np.linspace(-3, 3, 30)
    X, Y = np.meshgrid(x, y)
    Z = np.exp(-(X**2 + Y**2)/2.0) + 0.1 * np.random.rand(30, 30)
    ax.imshow(Z, cmap='magma', interpolation='bicubic')
    # add border
    rect = Rectangle((-0.5, -0.5), 30, 30, fill=False, color='#555555', lw=4)
    ax.add_patch(rect)
    save_fig(name)

def plot_pareto(name):
    fig, ax = plt.subplots(figsize=FIG_SIZE)
    setup_ax(ax)
    counts = [60, 30, 15, 8, 4]
    x = np.arange(len(counts))
    # gradient bar colors
    colors = ['#f06595', '#e64980', '#c2255c', '#a61e4d', '#862e9c']
    ax.bar(x, counts, color=colors, edgecolor='black', linewidth=1)
    
    # line
    cum = np.cumsum(counts) / sum(counts) * max(counts)
    ax.plot(x, cum, color='#fcc419', marker='D', lw=3, markersize=8, markeredgecolor='black')
    save_fig(name)

def plot_multi_feature_heatmap(name):
    fig, ax = plt.subplots(figsize=FIG_SIZE)
    ax.axis('off')
    data = np.random.rand(8, 8)
    np.fill_diagonal(data, 1.0)
    ax.imshow(data, cmap='coolwarm', interpolation='nearest')
    for i in range(9):
        ax.axhline(i-0.5, color='#1e1e1e', lw=2)
        ax.axvline(i-0.5, color='#1e1e1e', lw=2)
    save_fig(name)

def plot_3f_chart(name, plot_type='line'):
    fig, axs = plt.subplots(3, 1, figsize=FIG_SIZE)
    plt.subplots_adjust(hspace=0.15)
    colors = ['#ff8787', '#63e6be', '#74c0fc']
    for i in range(3):
        setup_ax(axs[i])
        if plot_type == 'line':
            x = np.arange(30)
            y = np.random.normal(0, 1, 30)
            axs[i].plot(x, y, color=colors[i], marker='.', markersize=6, lw=1.5)
            axs[i].axhline(0, color='gray', lw=1, alpha=0.5)
        elif plot_type == 'box':
            boxprops = dict(facecolor=colors[i], color='white', linewidth=1.5)
            axs[i].boxplot([np.random.normal(0, 1, 50)], vert=False, patch_artist=True, boxprops=boxprops)
            axs[i].set_xlim(-3, 3)
    save_fig(name)

def plot_parallel_coord(name):
    fig, ax = plt.subplots(figsize=FIG_SIZE)
    setup_ax(ax)
    x = [0, 1, 2, 3]
    for _ in range(15):
        y = np.random.normal(0, 1, 4)
        ax.plot(x, y, color='#a9e34b', alpha=0.6, lw=2)
    for i in x:
        ax.axvline(i, color='#868e96', lw=2)
    save_fig(name)

def plot_pass_fail(name):
    fig, ax = plt.subplots(figsize=FIG_SIZE)
    setup_ax(ax)
    data = np.random.rand(5, 25) < 0.85
    cmap = plt.matplotlib.colors.ListedColormap(['#fa5252', '#40c057'])
    ax.imshow(data, cmap=cmap, aspect='auto', interpolation='nearest')
    for i in range(6):
        ax.axhline(i-0.5, color='#1e1e1e', lw=2)
    for i in range(26):
        ax.axvline(i-0.5, color='#1e1e1e', lw=1)
    save_fig(name)

def plot_quadrant(name):
    fig, ax = plt.subplots(figsize=FIG_SIZE)
    setup_ax(ax)
    x = np.random.normal(0, 1, 100)
    y = np.random.normal(0, 1, 100)
    ax.scatter(x, y, color='#20c997', s=30, alpha=0.8, edgecolor='black', lw=0.5)
    ax.axhline(0, color='#fcc419', lw=2.5, linestyle='--')
    ax.axvline(0, color='#fcc419', lw=2.5, linestyle='--')
    save_fig(name)

def plot_matrix(name):
    plot_multi_feature_heatmap(name)

def plot_normality(name):
    fig, ax = plt.subplots(figsize=FIG_SIZE)
    setup_ax(ax)
    x = np.linspace(-3, 3, 60)
    y = x + np.random.normal(0, 0.3, 60)
    ax.scatter(x, y, color='#4dabf7', s=25, alpha=0.9, edgecolor='black', lw=0.5)
    ax.plot([-3, 3], [-3, 3], color='#fa5252', lw=3, linestyle='-')
    save_fig(name)

# Map chart IDs to plotter functions
plot_map = {
    # 單變量管制圖
    "imr": lambda: plot_control_chart('imr'),
    "xbar_r": lambda: plot_control_chart('xbar_r', 15),
    "run_chart": lambda: plot_trend_chart('run_chart'),
    "ewma": lambda: plot_control_chart('ewma'),
    "cusum": lambda: plot_trend_chart('cusum'),
    "ooc_analysis": lambda: plot_control_chart('ooc_analysis'),
    "shift_detection": lambda: plot_trend_chart('shift_detection'),
    "drift_detection": lambda: plot_trend_chart('drift_detection'),
    "pattern_recognition": lambda: plot_control_chart('pattern_recognition'),
    
    # 製程能力與分布
    "histogram_spec": lambda: plot_histogram('histogram_spec'),
    "normality": lambda: plot_normality('normality'),
    "boxplot": lambda: plot_boxplot('boxplot'),
    "density": lambda: plot_heatmap('density'),
    
    # 比較與分析
    "subgroup": lambda: plot_boxplot('subgroup'),
    "anova_parttype": lambda: plot_boxplot('anova_parttype'),
    
    # 關聯分析
    "scatter_spec": lambda: plot_scatter('scatter_spec'),
    "correlation_matrix": lambda: plot_multi_feature_heatmap('correlation_matrix'),
    "correlation_heatmap": lambda: plot_multi_feature_heatmap('correlation_heatmap'),
    "quadrant": lambda: plot_quadrant('quadrant'),
    "bivariate_outlier": lambda: plot_scatter('bivariate_outlier'),
    
    # 柏拉圖與空間圖
    "pareto": lambda: plot_pareto('pareto'),
    "spatial_heatmap": lambda: plot_heatmap('spatial_heatmap'),
    "repeated_offender": lambda: plot_heatmap('repeated_offender'),
    "outlier_analysis": lambda: plot_scatter('outlier_analysis'),
    
    # 三特徵
    "imr_3f": lambda: plot_3f_chart('imr_3f'),
    "run_chart_3f": lambda: plot_3f_chart('run_chart_3f'),
    "ewma_3f": lambda: plot_3f_chart('ewma_3f'),
    "cusum_3f": lambda: plot_3f_chart('cusum_3f'),
    "boxplot_3f": lambda: plot_3f_chart('boxplot_3f', 'box'),
    "anomaly_3f": lambda: plot_scatter('anomaly_3f'),
    "consistency_3f": lambda: plot_scatter('consistency_3f'),
    "parallel_coord": lambda: plot_parallel_coord('parallel_coord'),
    "pass_fail_matrix": lambda: plot_pass_fail('pass_fail_matrix')
}

print("Generating chart thumbnails...")
for chart_id, plotter in plot_map.items():
    try:
        plotter()
        # print(f"Generated {chart_id}")
    except Exception as e:
        print(f"Error on {chart_id}: {e}")

print("Done.")
