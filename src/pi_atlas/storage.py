"""Parquet storage with atomic rename + SHA-256 manifest."""
from __future__ import annotations

import csv
import hashlib
import os
import uuid
from pathlib import Path
from typing import List, Mapping, Tuple

import pandas as pd


class ResultStore:
    MANIFEST_COLUMNS = ["relative_path", "sha256", "rows", "bytes"]

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.root / "manifest.csv"
        if not self.manifest_path.exists():
            self._write_manifest_header()

    def _write_manifest_header(self) -> None:
        with open(self.manifest_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(self.MANIFEST_COLUMNS)

    @staticmethod
    def _sha256_of_file(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()

    def _partition_dir(self, partition: Mapping[str, str]) -> Path:
        segments = [f"{k}={v}" for k, v in partition.items()]
        return self.root.joinpath(*segments)

    def flush(self, df: pd.DataFrame, *, partition: Mapping[str, str]) -> Path:
        """Write df to a Parquet file under partition/<uuid>.parquet atomically."""
        dirpath = self._partition_dir(partition)
        dirpath.mkdir(parents=True, exist_ok=True)
        fname = f"{uuid.uuid4().hex}.parquet"
        tmp = dirpath / (fname + ".tmp")
        final = dirpath / fname

        df.to_parquet(tmp, index=False, engine="pyarrow")
        os.replace(tmp, final)  # atomic on POSIX, works on Windows too for rename

        # Record in manifest
        rel = final.relative_to(self.root).as_posix()
        sha = self._sha256_of_file(final)
        size = final.stat().st_size
        with open(self.manifest_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([rel, sha, len(df), size])

        return final

    def read_manifest(self) -> pd.DataFrame:
        return pd.read_csv(self.manifest_path)

    def verify_manifest(self) -> Tuple[bool, List[Path]]:
        """Recompute SHA-256 for each file; return (all_ok, list_of_bad_files)."""
        manifest = self.read_manifest()
        bad: List[Path] = []
        for _, row in manifest.iterrows():
            path = self.root / row["relative_path"]
            if not path.exists():
                bad.append(path)
                continue
            actual = self._sha256_of_file(path)
            if actual != row["sha256"]:
                bad.append(path)
        return (len(bad) == 0, bad)
