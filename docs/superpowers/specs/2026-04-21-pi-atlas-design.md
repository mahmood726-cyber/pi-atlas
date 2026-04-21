# PI Atlas — Design Specification v1.0

**Project:** PI Atlas (Prediction Interval Calibration Atlas on Pairwise70)
**Author:** Mahmood Ahmad
**Date:** 2026-04-21
**Status:** DRAFT v1.0 — awaiting user approval before implementation plan
**Spec locked by:** Zenodo DOI + OpenTimestamps + Internet Archive (prior to any compute)

---

## 1. Executive summary

One-year, dedicated-compute simulation + real-data study of **prediction-interval (PI) calibration** in random-effects meta-analysis, evaluated against the Cochrane Pairwise70 corpus (7,545 MAs, 595 reviews). The headline question is whether **published-standard 95% prediction intervals actually cover new-study true effects at nominal rate when confronted with real Cochrane heterogeneity structure**. Primary analysis uses leave-one-out coverage on the real corpus; secondary analysis uses an empirically-anchored synthetic twin to attribute any miscoverage to specific heterogeneity mechanisms.

---

## 2. Background and motivation

The Higgins-Thompson-Spiegelhalter (HTS) PI — the one Cochrane reviews most commonly publish — assumes normal random effects and uses `t_{k-2}` as the critical value. Known failure modes:

- **Small k:** PI undefined for k<3; unstable for k∈{3,4,5}.
- **τ² estimation noise:** DL-estimated τ² under small k is biased (see `advanced-stats.md`, rule 1).
- **Non-normal heterogeneity:** t-distributed, skewed, or contaminated heterogeneity breaks the normal-RE assumption.
- **HKSJ-floor requirement:** if `Q < k-1`, naive HKSJ narrows CI below DL — must floor to `max(1, Q/(k-1))`.

Existing PI literature (HTS 2009, Partlett-Riley 2017, Nagashima-Noma 2019) evaluates these failure modes on idealised DGPs. **No one has audited PI calibration against the real Cochrane corpus at scale.** That audit is this project's primary contribution.

---

## 3. Research questions

### 3.1 Primary

**Q1.** What is the empirical LOO coverage of the 95% HTS prediction interval with DL τ² estimator (the single most commonly published PI in Cochrane reviews) across the Pairwise70 corpus, and how does it vary by k, outcome type (binary / continuous / GIV), and empirical heterogeneity (τ̂² quartile)?

### 3.2 Secondary

**Q2.** Across 10 preregistered PI methods × 6 τ² levels × 4 DGP misspecification families × 1,500 empirically-anchored synthetic MAs × 2,000 replicates, which method–condition combinations achieve nominal coverage?

**Q3.** What is the **misspecification gap** — the systematic difference between real-corpus LOO coverage and well-specified synthetic-twin coverage — and what does it imply about published PI reliability?

**Q4.** For the same factorial, how do the 10 methods rank on μ̂ bias, μ̂ CI coverage, τ̂² bias, and τ̂² RMSE?

---

## 4. Design

### 4.1 Data source

- **Corpus:** Pairwise70 (7,545 meta-analyses, 595 Cochrane reviews). Same corpus as `repro-floor-atlas` and `cochrane-modern-re`.
- **Filter:** k ≥ 3 (PI requires it). Expected ≈ 6,386 MAs post-filter (cross-check with `cochrane-modern-re` count).
- **Stratification variables:** k (3, 4, 5–9, 10–19, 20+), outcome type (binary via OR/RR/RD, continuous via SMD/MD, GIV), SE-magnitude quartile.

### 4.2 Primary experiment — real-data leave-one-out (LOO)

For each MA with k ≥ 3:
- For each study j ∈ {1..k}:
  - Refit the meta-analysis on the k−1 remaining studies with each of 10 PI methods.
  - Record: `(method, ma_id, k, held_out_study_id, pi_lower, pi_upper, held_out_effect, held_out_se, coverage_indicator)`.

**Per-method LOO coverage** = mean of `coverage_indicator` over all (MA, j) pairs, with 95% Clopper-Pearson CIs (respecting `advanced-stats.md` rule: `qbeta(alpha/2, x, n-x+1)`).

Stratified coverage reported by k bucket, outcome type, and empirical τ̂² quartile.

Expected fit count: ~6,386 × average-k (≈6) × 10 methods ≈ **400K fits**. Cheap; runs in days.

### 4.3 Secondary experiment — synthetic twin factorial

**MA pool:** stratified random sample of 1,500 MAs from the filtered corpus (stratified by k × outcome type × SE-magnitude quartile).

**Factor grid (the Standard grid — preregistered):**

| Factor | Levels | Values |
|---|---|---|
| True μ | 1 | 0 (null-only; PI coverage is translation-invariant) |
| True τ² | 6 | {0, 0.01, 0.05, 0.15, 0.35, 0.75} |
| DGP family | 4 | Normal RE, t₃ RE, skewed RE (log-normal shifted), mixture RE (5% contamination) |
| Real MA pool | 1,500 | stratified sample (above) |
| Replicates/cell | 2,000 | (MC SE on 95% coverage ≈ 0.5%) |
| Methods | 10 | (see §5) |

**Per replicate:** given (k, {SE_i}, τ², DGP family):
1. Draw k random-effects offsets `b_i ~ DGP(0, τ²)`.
2. Draw k observed effects `y_i ~ N(b_i, SE_i²)`.
3. Fit each of 10 PI methods → get (PI lower, PI upper, μ̂, CI μ̂, τ̂²).
4. Draw ONE new-study true effect `μ_new ~ DGP(0, τ²)`.
5. Draw ONE new-study observed effect `y_new = μ_new + ε, ε ~ N(0, SE_new²)` where `SE_new` is drawn from the empirical SE distribution of the parent MA (bootstrap from `{SE_i}`).
6. Record BOTH coverage indicators:
   - `coverage_true = 1{pi_lower ≤ μ_new ≤ pi_upper}` (classical PI estimand — for Q2 & literature comparison)
   - `coverage_obs = 1{pi_lower ≤ y_new ≤ pi_upper}` (observed-effect estimand — for Q3 / misspecification gap vs LOO)
7. Record bias: `μ̂ − 0`, RMSE contribution: `(μ̂)²`, τ̂² error: `τ̂² − τ²`.

**Total synthetic fits:** 1,500 × 1 × 6 × 4 × 2,000 × 10 = **720 million fits**. At ~10ms/fit (Python) on 8 cores, ~2,000 core-hours ≈ 10 weeks of wall clock. Comfortable fit in a year with 40× headroom.

### 4.4 Misspecification gap (the headline)

For each of 1,500 sampled MAs and each of 10 methods:

- Compute `real_coverage_MA = 1/k · Σ_j 1{y_j ∈ PI_{-j}}` (real LOO coverage for that MA, using observed held-out effect `y_j`).
- Compute `synth_coverage_MA_observed = mean over replicates of 1{y_new ∈ PI}` where `y_new = μ_new + ε_new, ε_new ~ N(0, SE_j²)` — i.e. the synthetic twin matched to the **observed-effect estimand**, not the true-effect estimand.
- Report `gap_MA = real_coverage_MA − synth_coverage_MA_observed` distribution.

**Estimand note (important):** Because LOO observes `y_j`, not the unobservable true effect `μ_j`, the primary comparison uses the *observed-effect* estimand throughout. A parallel secondary analysis reports synthetic-twin coverage of `μ_new` (true-effect estimand) for comparison with the classical PI literature (HTS 2009). This dual reporting prevents apples-to-oranges comparison between LOO and synthetic.

**If the median gap is significantly negative (real < synthetic under well-specified model, observed-effect estimand) → published PIs are structurally under-covering** because real heterogeneity is non-normal. This is the paper's single-sentence headline.

---

## 5. Methods under test — preregistered list (10)

| # | PI method | τ² estimator | CI/PI formula | Implementation |
|---|---|---|---|---|
| 1 | HTS + DL | DerSimonian-Laird | `μ̂ ± t_{k-2} × √(τ̂² + SE(μ̂)²)` | numpy baseline |
| 2 | HTS + REML | REML | same | `statsmodels` / custom |
| 3 | HTS + PM | Paule-Mandel | same | custom (iterative) |
| 4 | HKSJ-adjusted | DL | HKSJ variance with floor `max(1, Q/(k-1))`, `t_{k-1}` df | custom (per `advanced-stats.md`) |
| 5 | Partlett-Riley | REML | Partlett-Riley bootstrap-improved PI (RSM 2017) | R `metafor::predict.rma` wrapper OR custom |
| 6 | Nagashima-Noma | REML | parametric bootstrap PI, 1,000 inner boots | R `pimeta` via subprocess OR Python port |
| 7 | Bayesian posterior predictive | Half-normal τ prior (scale=0.5) | MCMC via `bayesmeta`-equivalent | R `bayesmeta` via subprocess |
| 8 | Bayesian + MAP prior | MAP-prior τ (from MAPriors project) | MCMC | leverages MAPriors shipped code |
| 9 | Non-parametric cluster bootstrap | empirical | 10K bootstrap study resamples, quantile PI | custom |
| 10 | HTS + SJ | Sidik-Jonkman | `t_{k-2}` | custom |

**Implementation language:** Python primary; R via `rpy2` or subprocess for methods 5, 6, 7 (where the R implementation is the canonical reference). All fits validated against `metafor` to tolerance 1e-6 on a 5-cell baseline fixture.

**Frozen at preregistration** — no method added or removed after Zenodo DOI is minted.

---

## 6. Preregistration

### 6.1 Stack

1. **Zenodo DOI** — primary citable record via GitHub release `preregistration-v1.0.0`.
2. **OpenTimestamps attestation** — `ots stamp preregistration/PROTOCOL.md` committed to repo, anchored in Bitcoin blockchain within ~6 hours.
3. **Internet Archive snapshot** — `web.archive.org/save/<github-url>` on the frozen commit.

### 6.2 Contents of `preregistration/PROTOCOL.md`

- All content of §3, §4, §5 of this design doc (verbatim).
- Hash of the 5-cell numerical baseline fixture.
- Explicit list of non-goals (§10).
- Explicit list of deviations policy (see §6.3).

### 6.3 Deviations policy

Any departure from the preregistered protocol must be:
1. Recorded in `DEVIATIONS.md` with timestamp, reason, and commit SHA.
2. Classified as *forced* (software bug, bad data, dependency failure) or *elective* (scope reduction, method substitution).
3. Elective deviations flag the affected result as *post-hoc exploratory* in the final paper.

---

## 7. Compute architecture

### 7.1 Platform

- **Host:** dedicated Windows 11 PC, 16GB RAM, 8 cores (assumed).
- **Runtime:** WSL2 Ubuntu 22.04 (not bare Windows). Rationale: survives Windows Update reboots via systemd-user services; full POSIX tooling; `rpy2` stable.
- **Auto-restart:** systemd-user services (`pi-atlas-worker@.service`) with `Restart=always`, `RestartSec=30`.
- **Windows-side:** Windows Update configured with active-hours + `Defer feature updates`. WSL auto-starts on boot via scheduled task.

### 7.2 Work queue

- **Backend:** DuckDB file (`pi-atlas-queue.duckdb`), single-writer + WAL.
- **Schema:** `cells(cell_id PRIMARY KEY, phase TEXT, method TEXT, factor_json TEXT, seed_hex TEXT, status TEXT, claimed_at TIMESTAMP, completed_at TIMESTAMP)`.
- **Worker loop:** atomic `UPDATE ... RETURNING cell_id WHERE status='pending' ORDER BY cell_id LIMIT 1` to claim; set status=`running`; execute fit; write result to Parquet; set status=`done`.
- **Crash-safety:** a `running` cell idle for >1 hour is reset to `pending` by a watchdog service.

### 7.3 Seeding

`seed_hex = sha256(json.dumps(cell_config, sort_keys=True) + str(replicate_id)).hexdigest()[:16]`

Seeds are **deterministic from cell config**. Resuming from a checkpoint produces bit-identical results.

### 7.4 Storage

- **Format:** Parquet, partitioned by `(phase, method, tau2_level, dgp_family)`.
- **Buffer:** in-memory DataFrame, flushed to a new partition file every 60 minutes OR on 100K-row threshold, whichever comes first.
- **Rotation:** atomic — write to `.tmp` file, rename to final name.
- **Schema versioning:** `schema_version` column; schema frozen at preregistration.
- **Integrity:** SHA-256 of each Parquet file written to `manifest.csv`, verified weekly by a watchdog job.

### 7.5 Checkpoint contract (tested weekly)

The following invariant must hold, verified by an automated test:

> *At any point in time, killing all workers, rebooting the host, and restarting the systemd service must produce, within 60 minutes, a system in which (a) no cell is running, (b) no cell is lost, (c) no cell is duplicated, and (d) the next fit produced is bit-identical to the fit that would have been produced without the kill.*

---

## 8. Metrics and analysis plan

### 8.1 Primary (Q1)

- **LOO coverage** per method, overall + stratified by k bucket × outcome type × τ̂² quartile.
- **95% CI:** Clopper-Pearson exact binomial (`qbeta(alpha/2, x, n-x+1)`).
- **Primary result sentence:** *"Across N = [count] held-out (MA, study) pairs from 6,386 Cochrane meta-analyses, the HTS 95% PI with DL τ² achieved empirical LOO coverage of [X.X]% (95% CI: [L, U]) — a shortfall of [5−X.X] percentage points from nominal."*

### 8.2 Secondary (Q2-Q4)

- **Synthetic coverage heatmap:** method × τ² × DGP family. MC SE ~0.5% per cell.
- **Misspecification gap:** paired real vs synthetic coverage per MA, reported as median + IQR + Wilcoxon signed-rank test.
- **Estimator metrics:** bias, Monte Carlo SE, RMSE for μ̂ and τ̂² per method per cell.

### 8.3 Monte Carlo SE (MCSE) discipline

Every reported quantity gets an MCSE. Following `advanced-stats.md` (Monte Carlo tests): use 3-σ bounds for assertions, not tight point estimates. Acceptance: `MCSE(coverage) < 0.5%` ⇒ replicate count adequate.

### 8.4 Reproducibility

- Seeds logged; results regeneratable.
- Random number generator: `numpy.random.default_rng(int(seed_hex, 16))` for Python; `set.seed` + `xoshiro` for R via `rpy2`.

---

## 9. Output artifacts

### 9.1 During the year

- **Public dashboard** on GitHub Pages — read-only progress view, updated hourly (cells completed, current MCSE per cell, misspecification-gap interim estimate with caveat banner).
- **Monthly interim report** committed to repo as `reports/YYYY-MM.md`.
- **Sentinel pre-push hook** installed on the repo from day 1.

### 9.2 At year end

- **Paper** — targeting *Research Synthesis Methods* primary; *BMJ Methods* or *Nature Methods* as stretch.
- **E156 Synthēsis companion** — 7-sentence summary following E156 format.
- **Zenodo results DOI** — full Parquet dataset + analysis notebooks + final dashboard HTML.
- **Crossref DOI** on publication.
- **All code MIT licensed.**

---

## 10. Non-goals (preregistered)

- **No NMA methods.** Single pairwise comparisons only.
- **No DTA methods.** Continuous/binary/GIV effect sizes only.
- **No IPD meta-analysis.** Aggregate-data MA only.
- **No publication-bias modelling as a separate factor.** Captured indirectly via DGP misspecification (mixture family).
- **No post-hoc methods.** Methods discovered during the year → follow-up paper only; marked exploratory.
- **No new Pairwise70 data ingestion.** Using frozen corpus as-shipped by `repro-floor-atlas`.
- **No GPU/distributed compute.** Single-node CPU only.

---

## 11. Success criteria

### 11.1 Scientific

- Primary LOO coverage (Q1) reported with Clopper-Pearson 95% CI.
- Misspecification gap (Q3) reported with sign, magnitude, Wilcoxon p-value.
- Method ranking table (Q4) with MCSE on every cell.
- Primary headline expressible as a single-sentence finding with numbers.

### 11.2 Infrastructure

- Uptime ≥ 95% over the 12-month compute window (after accounting for Windows Updates).
- Zero silent result corruption (manifest.csv SHA-256 verification passes weekly).
- Resume-from-checkpoint integrity test passes weekly.
- Numerical baseline fixture reproduces to 1e-6 tolerance at final checkpoint.

### 11.3 Process

- Preregistration DOI minted **before** any compute.
- No scope creep: method list frozen, grid frozen, non-goals respected.
- All deviations logged and classified per §6.3.

---

## 12. Preconditions (P0 gates before main compute)

From the multi-persona review, these are non-negotiable before the year starts:

1. **Zenodo DOI minted** for preregistration-v1.0.0.
2. **OpenTimestamps attestation** committed + verified.
3. **Internet Archive snapshot** verified.
4. **WSL2 + systemd-user service test passes** (kill → reboot → restart → cells resume).
5. **DuckDB queue + Parquet output integration test passes** on 20-cell smoke run.
6. **Numerical baseline fixture** for 5 cells committed to git, reproduces to 1e-6.
7. **Sentinel pre-push hook** installed; zero BLOCK on `git push`.
8. **20-cell smoke run** completes end-to-end (queue → worker → Parquet → analysis notebook → dashboard).

Failing any of the above → main compute does **not** start.

---

## 13. Timeline (indicative, not preregistered)

- **Month 0 (≤ 4 weeks):** infra scaffold, 20-cell smoke run, preregistration DOI minted.
- **Months 1–10:** main compute. Monthly interim reports.
- **Month 11:** analysis, figure generation, paper draft.
- **Month 12:** paper submission, Zenodo results DOI, E156 companion submission to Synthēsis.

---

## 14. Out-of-scope considerations surfaced during brainstorming

- **Student digitization** (Makerere / SAARC / Fatiha networks) — not applicable to this project (aggregate-data only).
- **Option B (real-data resampling)** — rejected in favor of primary LOO (cleaner contract).
- **Option #4 (Guyot IPD Atlas)** — rejected on digitization-bottleneck grounds.
- **Option #8 (public benchmark platform)** — potential follow-up project, not in scope here.

---

## 15. Open points deliberately left to implementation plan

These are decisions that should *not* be preregistered because they're infrastructure-level:

- Exact Python version (3.11 vs 3.12) and lockfile strategy.
- Exact R version and `renv` lockfile.
- Specific CPU-affinity strategy for the 8 cores.
- Dashboard technology (static HTML + Parquet + `duckdb-wasm` vs server-rendered).
- CI strategy for the repo itself (GitHub Actions vs local pre-push only).

These go into the forthcoming `writing-plans` output.

---

## 16. Approval and next step

Upon user approval of this design:

1. Initialize `C:\Projects\pi-atlas\` as a git repo.
2. Commit this spec.
3. Invoke `superpowers:writing-plans` to produce an implementation plan with Task-0 preflight checks, infra scaffolding tasks, and smoke-run target.

**No code is written and no compute starts until the plan is approved and the P0 gates (§12) pass.**

---

## Appendix A — Pairwise70 empirical τ² quantiles (to be filled at preregistration)

*Computed from the 6,386 k≥3 MAs in the filtered corpus. Quantile values determine whether the Standard τ² grid {0, 0.01, 0.05, 0.15, 0.35, 0.75} is defensibly anchored.*

| Quantile | τ̂² value |
|---|---|
| 10% | TBD at prereg |
| 25% | TBD |
| 50% | TBD |
| 75% | TBD |
| 90% | TBD |
| 95% | TBD |

If the Pairwise70 95th percentile of τ̂² exceeds 0.75, the grid will be extended upward *before* preregistration (this is a pre-registration-time adjustment, not a post-hoc deviation).

---

## Appendix B — Cross-references to prior shipped work

- **Pairwise70 data origin:** `repro-floor-atlas` (v0.1.0, shipped 2026-04-21).
- **Corpus filtering convention (k ≥ 3):** matches `cochrane-modern-re` (v0.1.0, shipped 2026-04-21).
- **Bayesian MAP-prior (method #8):** leverages `MAPriors` (submission-ready, Cutting-Edge Trio).
- **Statistical rules adhered to:** `advanced-stats.md` (HKSJ floor, `t_{k-2}` PI, Clopper-Pearson `qbeta(alpha/2, ...)`, Fisher-z `1/(n-3)`).
- **Portfolio lessons applied:** `lessons.md` (no hardcoded paths, Parquet over CSV, per-cell seeds, numerical baseline contract, package-lock.json not applicable).
- **Pre-push integrity:** `Sentinel` hook installed day 1.
- **Publication format:** `E156` 7-sentence companion + full paper for primary journal.

---

**END OF DESIGN SPECIFICATION v1.0**
