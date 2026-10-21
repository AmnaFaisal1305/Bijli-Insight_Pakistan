"""
Location: ml/quantile_model.py
Purpose: Multi-quantile forecasting using LightGBM pinball loss (q=0.10, 0.50, 0.90).
"""

from pathlib import Path
from typing import Dict, Tuple, Any, List
import numpy as np
import pandas as pd
import lightgbm as lgb


class QuantileEnergyForecaster:
    """
    Trains and generates calibrated multi-quantile energy forecasts.
    """

    QUANTILES: List[float] = [0.10, 0.50, 0.90]
    
    FEATURE_COLS: List[str] = [
        "hour",
        "day_of_week",
        "humidity_pct",
        "wind_speed_kmh",
        "temp_lag_1",
        "temp_lag_24",
        "temp_lag_168",
        "temp_rolling_24"
    ]
    TARGET_COL: str = "temperature_c"

    def __init__(self, models_dir: Path = Path("models")):
        self.models_dir = Path(models_dir)
        self.fitted_models: Dict[float, lgb.Booster] = {}

    def prepare_time_based_split(
        self,
        df: pd.DataFrame,
        train_ratio: float = 0.80
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """
        Splits data chronologically to strictly prevent future data leakage.
        """
        needed_cols = [c for c in self.FEATURE_COLS if c in df.columns] + [self.TARGET_COL]
        df_clean = df.dropna(subset=needed_cols).copy()
        if "timestamp_utc" in df_clean.columns:
            df_clean = df_clean.sort_values("timestamp_utc").reset_index(drop=True)
        else:
            df_clean = df_clean.reset_index(drop=True)

        split_idx = int(len(df_clean) * train_ratio)
        
        X = df_clean[self.FEATURE_COLS]
        y = df_clean[self.TARGET_COL]

        X_train = X.iloc[:split_idx].copy()
        X_test = X.iloc[split_idx:].copy()
        y_train = y.iloc[:split_idx].copy()
        y_test = y.iloc[split_idx:].copy()

        return X_train, X_test, y_train, y_test

    def train_quantile_estimators(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series
    ) -> Dict[float, lgb.Booster]:
        """
        Trains 3 distinct LightGBM boosters using pinball loss objective (q=0.10, 0.50, 0.90).
        """
        self.models_dir.mkdir(parents=True, exist_ok=True)
        dtrain = lgb.Dataset(X_train, label=y_train)

        for q in self.QUANTILES:
            params = {
                "objective": "quantile",
                "alpha": q,
                "metric": "quantile",
                "learning_rate": 0.05,
                "max_depth": 6,
                "num_leaves": 31,
                "verbose": -1,
                "seed": 42
            }
            booster = lgb.train(params, dtrain, num_boost_round=100)
            self.fitted_models[q] = booster
            model_file = self.models_dir / f"lgb_quantile_{int(q*100)}.txt"
            booster.save_model(str(model_file))

        return self.fitted_models

    def predict_intervals(self, X_eval: pd.DataFrame) -> Dict[str, np.ndarray]:
        """
        Generates lower bound (q10), median (q50), and upper bound (q90) forecasts.
        Enforces monotonic non-crossing ordering: q10 <= q50 <= q90.
        """
        # If models not in memory, try loading or training default
        if not self.fitted_models:
            for q in self.QUANTILES:
                model_file = self.models_dir / f"lgb_quantile_{int(q*100)}.txt"
                if model_file.exists():
                    self.fitted_models[q] = lgb.Booster(model_file=str(model_file))

        if not self.fitted_models:
            raise RuntimeError("Models not fitted or loaded yet. Call train_quantile_estimators first.")

        q_low = self.fitted_models[0.10].predict(X_eval)
        q_mid = self.fitted_models[0.50].predict(X_eval)
        q_high = self.fitted_models[0.90].predict(X_eval)

        # Enforce non-crossing constraint
        q_mid = np.maximum(q_low, q_mid)
        q_high = np.maximum(q_mid, q_high)

        return {"q_low": q_low, "q_mid": q_mid, "q_high": q_high}
