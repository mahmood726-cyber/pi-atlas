"""Plan 3: LOO Coverage Evaluation

This plan defines the aggregation and reporting of the Prediction Interval coverage.

Primary Goals:
1. Aggregate the distributed Parquet result files into a single master summary dataframe.
2. Calculate the empirical LOO coverage for the `hts_dl` baseline (Q1).
3. Calculate empirical LOO coverage for the remaining 9 methods (Q2-Q4).
4. Break down coverage by meta-analysis characteristics:
   - Sample size `k` (e.g., k < 5, 5 <= k < 10, k >= 10)
   - Estimated heterogeneity `I^2` or `tau^2` percentiles.
   - Clinical domain / outcome type.

Steps to Implement:
1. `src/pi_atlas/analysis/aggregate.py`: Reads the `results/` Parquet partition and computes overall metrics (mean coverage, width, etc.).
2. `src/pi_atlas/analysis/report.py`: Generates the figures/tables for the manuscript (forest plots of coverage, calibration curves).
"""
