"""
Location: ml/quantile_model.py
Purpose: Trains 3 LightGBM estimators using pinball/quantile loss (q=0.10, 0.50, 0.90)
         to output an 80% prediction interval without Gaussian assumptions.
"""

from pathlib import Path
from typing import Dict, Tuple, Any, List
import numpy as np
import pandas as pd
import lightgbm as lgb


class QuantileEnergyForecaster:
    """
    Trains and generates multi-quantile energy forecasts.
    """

    QUANTILES: List[float] = [0.10, 0.50, 0.90]

    def __init__(self, models_dir: Path):
        self.models_dir = models_dir
        self.fitted_models: Dict[float, lgb.Booster] = {}

    def prepare_time_based_split(
        self,
        df: pd.DataFrame,
        train_ratio: float = 0.80
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """
        Splits data chronologically (train on past, test on future).
        Strict rule: NO random shuffling to prevent data leakage.
        
        Returns:
            X_train, X_test, y_train, y_test
        """
        # ALGORITHM:
        # 1. df = df.sort_values("timestamp_utc").reset_index(drop=True)
        # 2. split_idx = int(len(df) * train_ratio)
        # 3. features = [c for c in df.columns if c not in ['target', 'timestamp_utc', 'row_id']]
        # 4. return X.iloc[:split_idx], X.iloc[split_idx:], y.iloc[:split_idx], y.iloc[split_idx:]
        raise NotImplementedError

    def train_quantile_estimators(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series
    ) -> Dict[float, lgb.Booster]:
        """
        Fits 3 separate LightGBM models with 'quantile' objective.
        
        Parameters:
            alpha = 0.10 (pinball loss for 10th percentile)
            alpha = 0.50 (median absolute error)
            alpha = 0.90 (pinball loss for 90th percentile)
        """
        # ALGORITHM:
        # for q in self.QUANTILES:
        #     params = {
        #         "objective": "quantile",
        #         "alpha": q,
        #         "metric": "quantile",
        #         "learning_rate": 0.05,
        #         "max_depth": 6,
        #         "verbose": -1
        #     }
        #     dtrain = lgb.Dataset(X_train, label=y_train)
        #     booster = lgb.train(params, dtrain, num_boost_round=300)
        #     self.fitted_models[q] = booster
        # return self.fitted_models
        raise NotImplementedError

    def predict_intervals(self, X_eval: pd.DataFrame) -> Dict[str, np.ndarray]:
        """
        Generates predictions for all 3 quantiles.
        
        Returns:
            Dict containing:
                - 'q_low': array (10th percentile floor)
                - 'q_mid': array (50th percentile median)
                - 'q_high': array (90th percentile ceiling)
        """
        # ALGORITHM:
        # 1. low = self.fitted_models[0.10].predict(X_eval)
        # 2. mid = self.fitted_models[0.50].predict(X_eval)
        # 3. high = self.fitted_models[0.90].predict(X_eval)
        # 4. return {"q_low": low, "q_mid": mid, "q_high": high}
        raise NotImplementedError