import pandas as pd

from app.data.relation.join_engine import JoinEngine


def test_join_by_refdes():
    coord = pd.DataFrame({"RefDes": ["R1"], "X": [1], "Y": [2]})
    meas = pd.DataFrame({"RefDes": ["R1", "R2"], "Volume": [100, 110]})
    joined, report = JoinEngine.join(coord, meas)
    assert len(joined) == 2
    assert report["match_count"] == 1
    assert "match_rate" in report
