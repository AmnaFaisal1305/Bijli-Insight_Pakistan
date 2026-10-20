"""
Location: pipeline/generate_manifest.py
Purpose: Scans local raw files in data/raw/, imports hashing logic from data_fetcher.py,
         and writes the official manifest.csv audit ledger.
"""

from pathlib import Path
from typing import Dict, List, Any
import pandas as pd

# Reusing the master hashing function from data_fetcher (Zero Code Duplication)
from pipeline.data_fetcher import PakistanDataFetcher


class ManifestBuilder:
    """
    Auditing service that scans local disk storage and builds manifest.csv.
    """

    def __init__(self, raw_dir: Path):
        self.raw_dir = raw_dir
        self.manifest_file = raw_dir / "manifest.csv"
        # Instantiate fetcher to access its hashing method
        self.hasher_service = PakistanDataFetcher(raw_data_dir=raw_dir)

    def scan_raw_files(self) -> List[Path]:
        """
        Discovers all weather CSVs in data/raw/ while explicitly ignoring
        any pre-existing manifest.csv file.
        
        Returns:
            List[Path]: Paths to raw data CSV files.
        """
        # ALGORITHM:
        # 1. files = list(self.raw_dir.glob("pk_*_weather_*.csv"))
        # 2. filter out any file where file.name == "manifest.csv"
        # 3. return files
        raise NotImplementedError

    def build_file_record(self, file_path: Path) -> Dict[str, Any]:
        """
        Constructs an audit dictionary for a single file.
        
        Inputs:
            file_path (Path): Path to a raw CSV on disk.
            
        Outputs:
            Dict containing:
                - filename: str
                - source_url: str
                - publisher: str
                - fetch_timestamp_utc: ISO timestamp string
                - sha256_hash: 64-character hash string
                - licence: str
                - row_count: int
        """
        # ALGORITHM:
        # 1. sha_hash = self.hasher_service.compute_sha256(file_path)
        # 2. df = pd.read_csv(file_path, comment="#")
        # 3. return {
        #        "filename": file_path.name,
        #        "source_url": "https://archive-api.open-meteo.com/v1/archive",
        #        "publisher": "Open-Meteo / PMD Weather Archive",
        #        "fetch_timestamp_utc": pd.Timestamp.now("UTC").isoformat(),
        #        "sha256_hash": sha_hash,
        #        "licence": "CC-BY 4.0 / Open Access",
        #        "row_count": len(df)
        #    }
        raise NotImplementedError

    def generate_manifest(self) -> Path:
        """
        Executes scanning, constructs records for all raw files,
        and writes out the verified manifest.csv.
        
        Returns:
            Path: Path to created data/raw/manifest.csv
        """
        # ALGORITHM:
        # 1. raw_files = self.scan_raw_files()
        # 2. records = [self.build_file_record(f) for f in raw_files]
        # 3. df_manifest = pd.DataFrame(records)
        # 4. df_manifest.to_csv(self.manifest_file, index=False)
        # 5. return self.manifest_file
        raise NotImplementedError


if __name__ == "__main__":
    builder = ManifestBuilder(raw_dir=Path("data/raw"))
    builder.generate_manifest()