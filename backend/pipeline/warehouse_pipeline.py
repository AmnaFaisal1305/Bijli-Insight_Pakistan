"""
Location: pipeline/warehouse_pipeline.py
Purpose: Reproducible 3-layer DuckDB warehouse engine (make data).
         Enforces cryptographic verification before populating cleaned and gold tables.
"""

from pathlib import Path
from typing import Dict, Any, List
import hashlib
import duckdb
import pandas as pd


class DataWarehousePipeline:
    """
    Orchestrates the make data lifecycle:
    Layer 1 (Raw Verification) -> Layer 2 (Cleaned DuckDB) -> Layer 3 (Gold DuckDB)
    """

    def __init__(self, db_path: Path, raw_dir: Path):
        self.db_path = db_path
        self.raw_dir = raw_dir
        self.manifest_path = raw_dir / "manifest.csv"

    def verify_raw_manifest(self) -> bool:
        """
        LAYER 1 VERIFICATION:
        Reads manifest.csv and validates SHA-256 checksums for all raw files on disk.
        
        Returns:
            bool: True if all raw files pass checksum checks.
            
        Raises:
            FileNotFoundError: If manifest.csv or raw files are missing.
            ValueError: If a file hash does not match manifest.csv.
        """
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Missing manifest: {self.manifest_path}")

        df_manifest = pd.read_csv(self.manifest_path)
        for row in df_manifest.itertuples(index=False):
            target_file = self.raw_dir / row.filename
            if not target_file.exists():
                raise FileNotFoundError(f"Missing raw file: {target_file}")
            hasher = hashlib.sha256()
            with target_file.open("rb") as handle:
                while chunk := handle.read(8192):
                    hasher.update(chunk)
            if hasher.hexdigest() != row.sha256_hash:
                raise ValueError("Checksum Mismatch! File was tampered with.")
        return True

    def build_cleaned_layer(self, conn: duckdb.DuckDBPyConnection) -> None:
        """
        LAYER 2 (CLEANED):
        Connects to DuckDB and creates the normalized table: `cleaned_weather`.
        - Standardizes column names
        - Parses ISO timestamps into UTC timestamps
        - Converts metrics into 32-bit floats
        - Initializes is_imputed and is_anomalous tracking booleans
        """
        frames: List[pd.DataFrame] = []
        weather_files = [
            path for path in sorted(self.raw_dir.glob("*.csv"))
            if path.name != "manifest.csv"
        ]
        for path in weather_files:
            df = self._read_weather_csv(path)
            df["filename"] = path.name
            frames.append(df)

        if not frames:
            raise FileNotFoundError(f"No weather CSVs found in {self.raw_dir}")

        raw = pd.concat(frames, ignore_index=True)
        renamed = raw.rename(columns=self._column_map(raw.columns))
        renamed["timestamp_utc"] = pd.to_datetime(renamed["time"], utc=True)
        cleaned = renamed[[
            "filename",
            "timestamp_utc",
            "temperature_c",
            "humidity_pct",
            "wind_speed_kmh",
        ]].copy()
        cleaned["temperature_c"] = cleaned["temperature_c"].astype("float32")
        cleaned["humidity_pct"] = cleaned["humidity_pct"].astype("float32")
        cleaned["wind_speed_kmh"] = cleaned["wind_speed_kmh"].astype("float32")
        cleaned["is_imputed"] = False
        cleaned["is_anomalous"] = False

        conn.register("_cleaned_stage", cleaned)
        conn.execute("CREATE OR REPLACE TABLE cleaned_weather AS SELECT * FROM _cleaned_stage")
        conn.unregister("_cleaned_stage")

    def build_processed_gold_layer(self, conn: duckdb.DuckDBPyConnection) -> None:
        """
        LAYER 3 (PROCESSED / GOLD):
        Builds the production-ready feature table: `gold_weather_features`.
        - Generates immutable primary key: row_id = md5(filename || timestamp_utc)
        - Computes temporal lag features: temp_lag_1, temp_lag_24, temp_lag_168
        - Computes rolling statistics: temp_rolling_24 (24-hour moving window)
        """
        conn.execute(
            """
            CREATE OR REPLACE TABLE gold_weather_features AS
            SELECT
                md5(filename || timestamp_utc::VARCHAR) AS row_id,
                filename,
                timestamp_utc,
                temperature_c,
                humidity_pct,
                wind_speed_kmh,
                EXTRACT(HOUR FROM timestamp_utc) AS hour,
                EXTRACT(DOW FROM timestamp_utc) AS day_of_week,
                LAG(temperature_c, 1) OVER (
                    PARTITION BY filename ORDER BY timestamp_utc
                ) AS temp_lag_1,
                LAG(temperature_c, 24) OVER (
                    PARTITION BY filename ORDER BY timestamp_utc
                ) AS temp_lag_24,
                LAG(temperature_c, 168) OVER (
                    PARTITION BY filename ORDER BY timestamp_utc
                ) AS temp_lag_168,
                AVG(temperature_c) OVER (
                    PARTITION BY filename ORDER BY timestamp_utc
                    ROWS BETWEEN 24 PRECEDING AND CURRENT ROW
                ) AS temp_rolling_24
            FROM cleaned_weather
            """
        )

    def run_make_data(self) -> None:
        """
        Master CLI command coordinating the make data lifecycle from scratch.
        """
        self.verify_raw_manifest()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = duckdb.connect(str(self.db_path))
        try:
            self.build_cleaned_layer(conn)
            self.build_processed_gold_layer(conn)
        finally:
            conn.close()

    @staticmethod
    def _read_weather_csv(file_path: Path) -> pd.DataFrame:
        for encoding in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                with file_path.open(encoding=encoding) as handle:
                    first_line = handle.readline()
                if first_line.startswith("latitude"):
                    return pd.read_csv(file_path, skiprows=3, encoding=encoding)
                return pd.read_csv(file_path, comment="#", encoding=encoding)
            except UnicodeDecodeError:
                continue
        raise ValueError(f"Could not decode weather CSV: {file_path}")

    @staticmethod
    def _column_map(columns: pd.Index) -> Dict[str, str]:
        mapping: Dict[str, str] = {}
        for column in columns:
            name = str(column).lower()
            if "temp" in name:
                mapping[column] = "temperature_c"
            elif "humid" in name:
                mapping[column] = "humidity_pct"
            elif "wind" in name:
                mapping[column] = "wind_speed_kmh"
        return mapping


if __name__ == "__main__":
    pipeline = DataWarehousePipeline(
        db_path=Path("data/warehouse.duckdb"),
        raw_dir=Path("data/raw")
    )
    pipeline.run_make_data()