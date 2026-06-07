# Chart PNG baselines

Used by [`tests/test_chart_baseline_png.py`](../test_chart_baseline_png.py) with `matplotlib.testing.compare.compare_images`.

The pytest must use `matplotlib.pyplot.rc_context(...)` for DejaVu + dpi so **global** `rcParams` are not left on `DejaVu Sans` (that would flood later tests with CJK glyph warnings). The one-off regenerate snippet below runs in a fresh process, so `plt.rcParams.update` there is fine.

## Regenerate (Python 3.12, CI parity)

From repo root, with `MPLBACKEND=Agg` and the same payload as the test:

```bash
python -c "
import os; os.environ.setdefault('QT_QPA_PLATFORM','offscreen'); os.environ['MPLBACKEND']='Agg'
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'figure.dpi': 100, 'savefig.dpi': 100, 'font.family': 'DejaVu Sans'})
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
from app.charts.density_chart import DensityChart
ch = DensityChart()
ch.draw_chart({'metadata': {'is_valid': True}, 'data': {'x': [98.,100.,101.,103.,105.], 'y': [108.,110.,111.,109.,107.], 'col_x': 'Area', 'col_y': 'Height'}, 'statistics': {'gridsize': 12}})
ch.figure.savefig('tests/baseline_images/density_chart_default.png', dpi=100, format='png', facecolor=ch.figure.get_facecolor())
print('updated density_chart_default.png')
"
```

Then run `python -m pytest tests/test_chart_baseline_png.py -q`.

CI/Linux keeps the strict canonical tolerance. Windows may need a wider local tolerance because constrained-layout and FreeType metrics shift the plot area even when the labels, colorbar, and plotted data are unchanged; keep the canonical baseline produced on **Ubuntu** to match GitHub Actions.
