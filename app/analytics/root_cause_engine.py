"""
Root cause inference engine: rule-based engineering hints from SPC patterns,
heatmap clustering, correlation, trend, and capability analysis.
Read-only from payload — no side effects.

每條規則的 hint 字串包含實際量測數值，讓診斷頁面可直接顯示具體發現。
"""
from typing import Dict, Any, List
from app.analytics.ipc_reference_library import get_ipc_references_by_rule


def infer_root_cause_hints(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generate engineering hints from analysis payload.
    Returns list of { hint, rule_id, severity, evidence, confidence, priority,
    ipc_refs, observable_charts }.

    hint 字串直接包含量測數值（均值、比率、板次數等），提供具體診斷依據。
    observable_charts 列出使用者可在哪些圖表中直接觀察到該異常。
    """
    if not payload:
        return []
    hints: List[Dict[str, Any]] = []

    def _append(
        *,
        hint: str,
        rule_id: str,
        severity: str,
        evidence: Dict[str, Any],
        confidence: float,
        priority: str,
        observable_charts: List[str],
    ) -> None:
        hints.append({
            "hint": hint,
            "rule_id": rule_id,
            "severity": severity,
            "evidence": evidence,
            "confidence": confidence,
            "priority": priority,
            "ipc_refs": get_ipc_references_by_rule(rule_id),
            "observable_charts": observable_charts,
        })

    import numpy as np

    # ── Rule 1: Volume 板序下降 → 錫膏乾涸 ─────────────────────────────
    run_data = (payload.get("run_chart") or {}).get("data", {})
    values = np.array(run_data.get("values", []), dtype=float)
    valid_vals = values[np.isfinite(values)]

    if len(valid_vals) >= 10:
        n3 = len(valid_vals) // 3
        first_third = float(np.mean(valid_vals[:n3]))
        last_third  = float(np.mean(valid_vals[-n3:]))
        if first_third > 0 and last_third < first_third * 0.95:
            decline_ratio = 1.0 - (last_third / first_third)
            _append(
                hint=(
                    f"板序趨勢下降：前段均值 {first_third:.2f} → 後段均值 {last_third:.2f}，"
                    f"累計下降 {decline_ratio:.0%}（門檻 5%）。"
                    f"符合錫膏乾涸 (paste drying) 隨時間流失錫膏體積的漂移特徵。"
                ),
                rule_id="volume_decline_along_board",
                severity="warning",
                evidence={
                    "first_third_mean": round(first_third, 3),
                    "last_third_mean":  round(last_third, 3),
                    "decline_ratio":    round(decline_ratio, 4),
                    "sample_n":         len(valid_vals),
                    "threshold":        "last_third < first_third × 0.95",
                },
                confidence=min(0.95, 0.55 + decline_ratio),
                priority="high",
                observable_charts=["趨勢圖 (Run Chart)", "CUSUM 圖", "EWMA 圖"],
            )

    # ── Rule 2: OOS 邊緣聚集 → 對位偏移 / 鋼板張力 ─────────────────────
    spatial_data = (payload.get("spatial") or {}).get("data", {})
    x_vals  = spatial_data.get("x", [])
    y_vals  = spatial_data.get("y", [])
    oos_vals = (
        (payload.get("spatial") or {})
        .get("modes", {})
        .get("oos_density", {})
        .get("values", [])
    )
    if x_vals and y_vals and oos_vals and len(x_vals) == len(oos_vals):
        xs, ys = np.array(x_vals), np.array(y_vals)
        oos = np.array(oos_vals)
        if np.any(oos > 0):
            edge_x = float(np.max(xs) - np.min(xs))
            edge_y = float(np.max(ys) - np.min(ys))
            if edge_x > 0 and edge_y > 0:
                outlying = (
                    (np.abs(xs - np.mean(xs)) > 0.4 * edge_x) |
                    (np.abs(ys - np.mean(ys)) > 0.4 * edge_y)
                )
                edge_sum  = float(np.sum(oos[outlying]))
                total_sum = float(np.sum(oos))
                if edge_sum > 0.5 * total_sum:
                    edge_ratio = edge_sum / total_sum if total_sum > 0 else 0.0
                    _append(
                        hint=(
                            f"空間分析：PCB 邊緣區域 OOS 佔全域 {edge_ratio:.0%}"
                            f"（邊緣 {edge_sum:.0f} / 全域 {total_sum:.0f} 點，門檻 50%）。"
                            f"OOS 呈系統性邊緣聚集，符合印刷機對位偏移或鋼板張力鬆弛特徵。"
                        ),
                        rule_id="edge_spatial_cluster",
                        severity="warning",
                        evidence={
                            "edge_oos_sum":   round(edge_sum, 1),
                            "total_oos_sum":  round(total_sum, 1),
                            "edge_oos_ratio": round(edge_ratio, 4),
                            "threshold":      "edge_oos_sum > 50 % total_oos_sum",
                        },
                        confidence=min(0.95, 0.6 + edge_ratio * 0.35),
                        priority="high",
                        observable_charts=["空間熱圖 (Spatial Heatmap)", "散佈圖 (Scatter)"],
                    )

    # ── Rule 3: Footprint 變異不均 → 鋼板開孔設計 ───────────────────────
    box_stats = (payload.get("box") or {}).get("statistics", {}).get("variance_by_label", {})
    if box_stats and len(box_stats) >= 2:
        vars_list = list(box_stats.values())
        min_var = min(vars_list)
        max_var = max(vars_list)
        if max_var > 2 * min_var and min_var >= 0:
            ratio = (max_var / min_var) if min_var > 0 else float("inf")
            ratio_str = f"{ratio:.1f}×" if ratio != float("inf") else "∞（min_var ≈ 0）"
            _append(
                hint=(
                    f"Footprint 變異不均：最大/最小比 {ratio_str}"
                    f"（max={max_var:.4f}，min={min_var:.4f}，門檻 2×）。"
                    f"特定足印位置變異顯著偏高，符合鋼板開孔設計不一致或局部磨損特徵。"
                ),
                rule_id="footprint_variance_imbalance",
                severity="info",
                evidence={
                    "min_variance":  round(min_var, 6),
                    "max_variance":  round(max_var, 6),
                    "variance_ratio": round(ratio, 3) if ratio != float("inf") else "inf",
                    "footprint_count": len(box_stats),
                    "threshold":     "max_variance > 2 × min_variance",
                },
                confidence=0.62 if ratio == float("inf") else min(0.9, 0.5 + ratio / 10.0),
                priority="medium",
                observable_charts=["箱型圖 (Boxplot)", "散佈圖 (Scatter)"],
            )

    # ── Rule 4 & 5: 整體均值系統性偏高/偏低 → overprint / underprint ────
    cap = payload.get("cap") or {}
    if cap.get("metadata", {}).get("is_valid"):
        cap_stat = cap.get("statistics", {})
        mean_val = cap_stat.get("mean")
        meta     = cap.get("metadata", {})
        usl, lsl = meta.get("usl"), meta.get("lsl")
        if usl is not None and lsl is not None:
            target_val = (float(usl) + float(lsl)) / 2.0
        else:
            target_val = None

        if mean_val is not None and target_val is not None and target_val != 0:
            ratio = mean_val / target_val
            spec_str = (
                f"規格 [{float(lsl):.2f}, {float(usl):.2f}]，中心 {target_val:.2f}"
                if (usl is not None and lsl is not None) else f"規格中心 {target_val:.2f}"
            )

            if ratio > 1.08:
                _append(
                    hint=(
                        f"整體系統性偏高：均值 {mean_val:.3f}，{spec_str}，"
                        f"均值/中心 = {ratio:.0%}（門檻 108%）。"
                        f"符合鋼板開孔偏大或刮刀速度過慢（overprint）造成錫膏體積持續偏高特徵。"
                    ),
                    rule_id="consistent_volume_high",
                    severity="info",
                    evidence={
                        "mean":              round(mean_val, 4),
                        "target_mid_spec":   round(target_val, 4),
                        "mean_target_ratio": round(ratio, 4),
                        "threshold":         "mean / target > 1.08",
                    },
                    confidence=min(0.9, 0.5 + (ratio - 1.08) * 4.0),
                    priority="medium",
                    observable_charts=["製程能力圖 (Capability)", "直方圖 (Histogram)", "趨勢圖 (Run Chart)"],
                )
            elif ratio < 0.92:
                _append(
                    hint=(
                        f"整體系統性偏低：均值 {mean_val:.3f}，{spec_str}，"
                        f"均值/中心 = {ratio:.0%}（門檻 92%）。"
                        f"符合鋼板開孔偏小或刮刀壓力不足（underprint）造成錫膏體積持續偏低特徵。"
                    ),
                    rule_id="consistent_volume_low",
                    severity="info",
                    evidence={
                        "mean":              round(mean_val, 4),
                        "target_mid_spec":   round(target_val, 4),
                        "mean_target_ratio": round(ratio, 4),
                        "threshold":         "mean / target < 0.92",
                    },
                    confidence=min(0.9, 0.5 + (0.92 - ratio) * 4.0),
                    priority="medium",
                    observable_charts=["製程能力圖 (Capability)", "直方圖 (Histogram)", "趨勢圖 (Run Chart)"],
                )

    # ── Rule 6 & 7: CUSUM 持續漂移 / 局部偏移 ───────────────────────────
    cusum_data  = (payload.get("cusum") or {}).get("data", {})
    cusum_stats = (payload.get("cusum") or {}).get("statistics", {})
    cusum_ooc   = cusum_data.get("out_of_control_indices", [])
    cusum_n     = cusum_stats.get("n", 0)

    if cusum_ooc and cusum_n > 0:
        ooc_ratio = len(cusum_ooc) / cusum_n

        if ooc_ratio >= 0.10:
            # When most samples are out of control, escalate to fatal severity.
            severity = "error" if ooc_ratio >= 0.50 else "warning"
            _append(
                hint=(
                    f"CUSUM 持續漂移：{len(cusum_ooc)}/{cusum_n} 點（{ooc_ratio:.0%}）超出 ±h 管制界線"
                    f"（門檻 10%）。累積偏移連續超標，顯示製程中心發生系統性漂移，非隨機波動。"
                ),
                rule_id="cusum_trend_drift",
                severity=severity,
                evidence={
                    "ooc_count":  len(cusum_ooc),
                    "total_n":    cusum_n,
                    "ooc_ratio":  round(ooc_ratio, 4),
                    "threshold":  "ooc_ratio ≥ 10 %",
                },
                confidence=min(0.95, 0.6 + ooc_ratio),
                priority="high",
                observable_charts=["CUSUM 圖", "趨勢圖 (Run Chart)"],
            )
        elif len(cusum_ooc) > 0:
            _append(
                hint=(
                    f"CUSUM 局部偏移：{len(cusum_ooc)}/{cusum_n} 點（{ooc_ratio:.0%}）超出 ±h 界線"
                    f"（< 10%）。偏移呈局部集中而非連續漂移，建議對應板次進行人工複核。"
                ),
                rule_id="cusum_local_shift",
                severity="info",
                evidence={
                    "ooc_count":  len(cusum_ooc),
                    "total_n":    cusum_n,
                    "ooc_ratio":  round(ooc_ratio, 4),
                    "threshold":  "0 < ooc_ratio < 10 %",
                },
                confidence=min(0.85, 0.45 + ooc_ratio),
                priority="medium",
                observable_charts=["CUSUM 圖", "趨勢圖 (Run Chart)"],
            )

    # ── Rule 8: 空間單側偏離 → 鋼板磨損 / 刮刀壓力不均 ────────────────
    spatial_modes = (payload.get("spatial") or {}).get("modes", {})
    dev_data = spatial_modes.get("volume_deviation", {}).get("values", [])
    if len(dev_data) >= 10:
        arr = np.array(dev_data, dtype=float)
        valid_mask = ~np.isnan(arr)
        if np.any(valid_mask):
            valid_count = int(np.sum(valid_mask))
            pos_share = float(np.nansum(arr > 0)) / valid_count
            neg_share = float(np.nansum(arr < 0)) / valid_count
            if pos_share > 0.6 or neg_share > 0.6:
                dominant      = max(pos_share, neg_share)
                dominant_dir  = "偏高" if pos_share > neg_share else "偏低"
                _append(
                    hint=(
                        f"空間偏離：{dominant_dir}方向佔 {dominant:.0%}"
                        f"（偏高 {pos_share:.0%}，偏低 {neg_share:.0%}，N={valid_count}，門檻 60%）。"
                        f"呈單側系統性空間傾向，符合鋼板局部磨損或刮刀壓力前後不均特徵。"
                    ),
                    rule_id="localized_deviation_bias",
                    severity="info",
                    evidence={
                        "positive_share":  round(pos_share, 4),
                        "negative_share":  round(neg_share, 4),
                        "dominant_share":  round(dominant, 4),
                        "dominant_dir":    dominant_dir,
                        "valid_n":         valid_count,
                        "threshold":       "single_side_share > 60 %",
                    },
                    confidence=min(0.88, 0.5 + dominant * 0.45),
                    priority="medium",
                    observable_charts=["空間熱圖 (Spatial Heatmap)", "箱型圖 (Boxplot)"],
                )

    # ── Rule 9: Cpk 低於門檻 → 製程能力不足 ────────────────────────────
    if cap.get("metadata", {}).get("is_valid"):
        cap_stat = cap.get("statistics", {})
        cpk = cap_stat.get("cpk")
        cp  = cap_stat.get("cp")
        mean_v   = cap_stat.get("mean")
        sigma_st = cap_stat.get("sigma_st")
        meta = cap.get("metadata", {})
        usl, lsl = meta.get("usl"), meta.get("lsl")

        if cpk is not None and cpk < 1.33:
            level = "製程不合格" if cpk < 1.0 else "製程能力不足，不符 1.33 最低要求"
            sigma_str = f"σ(短期)={sigma_st:.4f}" if sigma_st else ""
            spec_str2 = (
                f"規格 [{float(lsl):.2f}, {float(usl):.2f}]"
                if (usl is not None and lsl is not None) else "規格未知"
            )
            cp_str = f"，Cp={cp:.3f}" if cp else ""
            _append(
                hint=(
                    f"製程能力不足：Cpk = {cpk:.3f}{cp_str}（{level}）。"
                    f"均值={mean_v:.3f}，{sigma_str}，{spec_str2}。"
                    f"{'Cpk < 1.0 表示製程規格外產出率顯著偏高。' if cpk < 1.0 else 'Cpk 介於 1.0–1.33 屬邊界狀態，建議持續改善。'}"
                ),
                rule_id="cpk_below_threshold",
                severity="error" if cpk < 1.0 else "warning",
                evidence={
                    "cpk":      round(cpk, 4),
                    "cp":       round(cp, 4) if cp else None,
                    "mean":     round(mean_v, 4) if mean_v else None,
                    "sigma_st": round(sigma_st, 4) if sigma_st else None,
                    "threshold": "Cpk < 1.33（合格）；< 1.0（不合格）",
                },
                confidence=min(0.98, 0.70 + max(0.0, 1.33 - cpk) * 0.5),
                priority="high" if cpk < 1.0 else "medium",
                observable_charts=["製程能力圖 (Capability)", "直方圖 (Histogram)", "常態機率圖 (Normality)"],
            )

    # ── Rule 10: 常態性檢驗失敗 → Cpk 解釋需謹慎 ───────────────────────
    norm = payload.get("normality") or {}
    if norm.get("metadata", {}).get("is_valid"):
        norm_stat = norm.get("statistics", {})
        p_value  = norm_stat.get("p_value")
        is_normal = norm_stat.get("is_normal")
        total_n   = norm_stat.get("total_n", 0)
        test_name = norm_stat.get("test_name", "常態性檢驗")
        r_sq      = norm_stat.get("r_squared")

        if p_value is not None and not is_normal:
            r_sq_str = f"，R²={r_sq:.3f}" if r_sq is not None else ""
            _append(
                hint=(
                    f"常態性檢驗失敗：{test_name} p = {p_value:.4f} < 0.05"
                    f"（N={total_n}{r_sq_str}）。"
                    f"資料分布顯著偏離常態，Cpk 的常態性假設不成立，"
                    f"能力指標可能低估實際不合格率。"
                ),
                rule_id="normality_test_fail",
                severity="warning",
                evidence={
                    "p_value":   float(p_value),
                    "is_normal": False,
                    "test_name": test_name,
                    "total_n":   total_n,
                    "r_squared": round(r_sq, 4) if r_sq else None,
                    "threshold": "p < 0.05 → 拒絕常態假設",
                },
                confidence=min(0.97, 0.75 + max(0.0, 0.05 - p_value) * 5.0),
                priority="medium",
                observable_charts=["常態機率圖 (Normality)", "直方圖 (Histogram)"],
            )

    # ── Rule 11: 高變異係數 → 製程穩定性不足 ────────────────────────────
    if cap.get("metadata", {}).get("is_valid"):
        cap_stat = cap.get("statistics", {})
        mean_v2  = cap_stat.get("mean")
        sigma_st2 = cap_stat.get("sigma_st")
        if mean_v2 and sigma_st2 and abs(mean_v2) > 1e-9:
            cv = abs(sigma_st2 / mean_v2)
            if cv > 0.15:
                _append(
                    hint=(
                        f"高變異係數：CV = {cv:.1%}（σ={sigma_st2:.4f}，均值={mean_v2:.4f}，門檻 15%）。"
                        f"製程穩定性不足，高 CV 通常源於設備漂移、材料批次差異或操作變異疊加。"
                    ),
                    rule_id="high_cv",
                    severity="warning" if cv > 0.25 else "info",
                    evidence={
                        "cv":       round(cv, 4),
                        "sigma_st": round(sigma_st2, 4),
                        "mean":     round(mean_v2, 4),
                        "threshold": "CV > 15 %",
                    },
                    confidence=min(0.90, 0.55 + cv * 1.2),
                    priority="medium",
                    observable_charts=["趨勢圖 (Run Chart)", "箱型圖 (Boxplot)", "製程能力圖 (Capability)"],
                )

    return hints
