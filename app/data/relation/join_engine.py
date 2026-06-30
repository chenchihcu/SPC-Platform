import pandas as pd
from typing import Any, Dict, Tuple


def _empty_join_report(error: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    return pd.DataFrame(), {"error": error, "match_rate": 0.0, "can_do_spatial": False}


class JoinEngine:
    """
    Handles joining coordinate and measurement data on RefDes.
    Produces validation report outputting matching rate and duplicate warnings.
    """

    @staticmethod
    def join(coord_df: pd.DataFrame, meas_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Joins measurement data with coordinate data.
        Return joined dataframe and a join report.
        """
        # Return empty if either is invalid or missing RefDes
        if coord_df is None or meas_df is None or coord_df.empty or meas_df.empty:
            return _empty_join_report("Empty dataframe provided")

        if "RefDes" not in coord_df.columns or "RefDes" not in meas_df.columns:
            return _empty_join_report("Missing RefDes in one or both dataframes")

        # Check for duplicates in coordinate dataframe
        coord_refdes_counts = coord_df["RefDes"].value_counts()
        duplicates = coord_refdes_counts[coord_refdes_counts > 1].index.tolist()

        # MANDATORY: Deduplicate coordinate data before merge to prevent Cartesian explosion (Pass 122).
        # We keep the first occurrence of each RefDes.
        safe_coord_df = coord_df.drop_duplicates(subset=["RefDes"])

        # We perform a left join from measurement to coordinate
        # because measurement is the primary temporal fact table for SPC.
        # It preserves all measurements even if coordinates are missing.
        joined_df = pd.merge(meas_df, safe_coord_df, on="RefDes", how="left", indicator=True, suffixes=('', '_coord'))

        match_count = (joined_df["_merge"] == "both").sum()
        total_meas = len(meas_df)
        match_rate = (match_count / total_meas) * 100 if total_meas > 0 else 0.0

        # Fallback mechanism: If strict match fails terribly (e.g. SPI outputs 'C131_1' but CAD is 'C131')
        if match_rate < 10.0 and total_meas > 0:
            # Strip trailing strings like '_1', '-1', etc.
            stripped_meas_refdes = meas_df["RefDes"].astype(str).str.replace(r'[-_][0-9]+$', '', regex=True)

            # Use safe_coord_df and ensure fallback keys are also unique for O(N) merge
            fallback_joined = pd.merge(
                meas_df.assign(_JoinKey=stripped_meas_refdes),
                safe_coord_df.assign(_JoinKey=safe_coord_df["RefDes"].astype(str)).drop_duplicates(subset=["_JoinKey"]),
                on="_JoinKey",
                how="left",
                indicator=True,
                suffixes=('', '_coord')
            )

            fallback_match_count = (fallback_joined["_merge"] == "both").sum()
            if fallback_match_count > match_count:
                joined_df = fallback_joined.drop(columns=["_JoinKey"])
                match_count = fallback_match_count
                match_rate = (match_count / total_meas) * 100

        unmatch_count = total_meas - match_count

        # Extract unmatched RefDes
        unmatched_mask = joined_df["_merge"] == "left_only"
        unmatched_arr = joined_df.loc[unmatched_mask, "RefDes"].unique()
        unmatched_refdes = pd.Series(unmatched_arr).dropna().tolist()

        # Clean up indicator col
        joined_df = joined_df.drop(columns=["_merge"])

        # Normalize X/Y after fallback merge (fallback produces X_coord, Y_coord)
        if "X" not in joined_df.columns and "X_coord" in joined_df.columns:
            joined_df["X"] = joined_df["X_coord"]
        if "Y" not in joined_df.columns and "Y_coord" in joined_df.columns:
            joined_df["Y"] = joined_df["Y_coord"]

        can_do_spatial = match_count > 0 and "X" in joined_df.columns and "Y" in joined_df.columns

        report = {
            "total_measurements": int(total_meas),
            "match_count": int(match_count),
            "unmatch_count": int(unmatch_count),
            "match_rate": float(match_rate),
            "duplicate_coord_refdes": duplicates,
            "unmatched_refdes_sample": unmatched_refdes[:50],  # keep a sample to avoid huge lists
            "can_do_spatial": bool(can_do_spatial)
        }

        return joined_df, report
