"""Aggregate Parquet results and compute coverage metrics."""
import pandas as pd
from pathlib import Path
import numpy as np

def aggregate_results(results_dir: Path | str) -> pd.DataFrame:
    """Read all result parquets and return a single dataframe."""
    p = Path(results_dir)
    # Recursively find all parquet files (excluding the baseline fixture if in a different path)
    # The actual results are in results_dir
    files = list(p.rglob("*.parquet"))
    if not files:
        return pd.DataFrame()
    
    # Read and concat
    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    return df

def compute_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Compute overall coverage and width metrics by method."""
    if df.empty:
        return pd.DataFrame()
        
    df["width"] = df["pi_upper"] - df["pi_lower"]
    
    metrics = df.groupby("method").agg(
        n_tasks=("cell_id", "count"),
        coverage=("coverage_obs", "mean"),
        mean_width=("width", "mean"),
        median_width=("width", "median")
    ).reset_index()
    
    # Calculate binomial confidence intervals for the coverage
    # Using normal approximation for simplicity here, can use exact CI if preferred
    z = 1.96
    metrics["se"] = np.sqrt(metrics["coverage"] * (1 - metrics["coverage"]) / metrics["n_tasks"])
    metrics["cov_ci_lower"] = metrics["coverage"] - z * metrics["se"]
    metrics["cov_ci_upper"] = metrics["coverage"] + z * metrics["se"]
    
    return metrics

def compute_metrics_by_k(df: pd.DataFrame) -> pd.DataFrame:
    """Compute coverage grouped by k_total."""
    if df.empty:
        return pd.DataFrame()
    
    df["width"] = df["pi_upper"] - df["pi_lower"]
    
    metrics = df.groupby(["method", "k"]).agg(
        n_tasks=("cell_id", "count"),
        coverage=("coverage_obs", "mean"),
        mean_width=("width", "mean")
    ).reset_index()
    
    return metrics
