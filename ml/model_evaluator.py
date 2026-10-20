"""
Location: ml/model_evaluator.py
Purpose: Benchmarks model against Persistence Baseline (t - 168), evaluates
         quantile interval non-crossing and coverage, and breaks down group errors.
"""

from typing import Dict, Any
import numpy as np
import pandas as pd


class ModelFairnessEvaluator:
    """
    Evaluates baseline superiority, uncertainty calibration, and operational fairness.
    """

    def compute_declared_baseline(
        self,
        y_true: np.ndarray,
        y_lag_168: np.ndarray
    ) -> Dict[str, float]:
        """
        Persistence Baseline: y_hat_t = y_(t - 168).
        Calculates baseline Mean Absolute Error and Root Mean Squared Error.
        """
        abs_errors = np.abs(y_true - y_lag_168)
        mae_baseline = float(np.mean(abs_errors))
        rmse_baseline = float(np.sqrt(np.mean((y_true - y_lag_168) ** 2)))
        return {"baseline_mae": mae_baseline, "baseline_rmse": rmse_baseline}

    def evaluate_quantile_calibration(
        self,
        y_true: np.ndarray,
        q_low: np.ndarray,
        q_mid: np.ndarray,
        q_high: np.ndarray
    ) -> Dict[str, Any]:
        """
        Validates mathematical interval integrity:
        1. Non-crossing constraint: q_low <= q_mid <= q_high for all time steps.
        2. Empirical coverage percentage: target is approximately 80% for [q10, q90].
        """
        order_valid = bool(np.all((q_low <= q_mid) & (q_mid <= q_high)))
        inside = (y_true >= q_low) & (y_true <= q_high)
        empirical_coverage = float(np.mean(inside) * 100.0)
        return {
            "intervals_valid": order_valid,
            "empirical_coverage_pct": empirical_coverage,
            "target_coverage_pct": 80.0,
        }

    def compute_group_error_slices(
        self,
        df_eval: pd.DataFrame
    ) -> Dict[str, Dict[str, float]]:
        """
        Partitions evaluation set into Pakistan operational slices:
        - Time Slice: Peak Hours (18:00 - 22:00 PKT) vs. Off-Peak
        - Day Slice: Weekdays vs. Weekends
        - Weather Slice: Heatwave (Temp >= 35C) vs. Moderate
        """
        def _mae(mask: pd.Series) -> float:
            if not mask.any():
                return float("nan")
            return float(
                np.mean(
                    np.abs(
                        df_eval.loc[mask, "y_true"] - df_eval.loc[mask, "y_pred"]
                    )
                )
            )

        peak_mask = df_eval["hour"].between(18, 22)
        weekend_mask = df_eval["day_of_week"].isin([5, 6])
        heat_mask = df_eval["temperature_c"] >= 35.0
        return {
            "peak": {"mae": _mae(peak_mask)},
            "off_peak": {"mae": _mae(~peak_mask)},
            "weekend": {"mae": _mae(weekend_mask)},
            "weekday": {"mae": _mae(~weekend_mask)},
            "heatwave": {"mae": _mae(heat_mask)},
            "moderate": {"mae": _mae(~heat_mask)},
        }