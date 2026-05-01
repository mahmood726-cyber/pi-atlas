## 3. Research questions

### 3.1 Primary

**Q1.** What is the empirical LOO coverage of the 95% HTS prediction interval with DL Ï„Â² estimator (the single most commonly published PI in Cochrane reviews) across the Pairwise70 corpus, and how does it vary by k, outcome type (binary / continuous / GIV), and empirical heterogeneity (Ï„Ì‚Â² quartile)?

### 3.2 Secondary

**Q2.** Across 10 preregistered PI methods Ã— 6 Ï„Â² levels Ã— 4 DGP misspecification families Ã— 1,500 empirically-anchored synthetic MAs Ã— 2,000 replicates, which methodâ€“condition combinations achieve nominal coverage?

**Q3.** What is the **misspecification gap** â€” the systematic difference between real-corpus LOO coverage and well-specified synthetic-twin coverage â€” and what does it imply about published PI reliability?

**Q4.** For the same factorial, how do the 10 methods rank on Î¼Ì‚ bias, Î¼Ì‚ CI coverage, Ï„Ì‚Â² bias, and Ï„Ì‚Â² RMSE?

---

## 4. Design

### 4.1 Data source

- **Corpus:** Pairwise70 (7,545 meta-analyses, 595 Cochrane reviews). Same corpus as `repro-floor-atlas` and `cochrane-modern-re`.
- **Filter:** k â‰¥ 3 (PI requires it). Expected â‰ˆ 6,386 MAs post-filter (cross-check with `cochrane-modern-re` count).
- **Stratification variables:** k (3, 4, 5â€“9, 10â€“19, 20+), outcome type (binary via OR/RR/RD, continuous via SMD/MD, GIV), SE-magnitude quartile.

### 4.2 Primary experiment â€” real-data leave-one-out (LOO)

For each MA with k â‰¥ 3:
- For each study j âˆˆ {1..k}:
  - Refit the meta-analysis on the kâˆ’1 remaining studies with each of 10 PI methods.
  - Record: `(method, ma_id, k, held_out_study_id, pi_lower, pi_upper, held_out_effect, held_out_se, coverage_indicator)`.

**Per-method LOO coverage** = mean of `coverage_indicator` over all (MA, j) pairs, with 95% Clopper-Pearson CIs (respecting `advanced-stats.md` rule: `qbeta(alpha/2, x, n-x+1)`).

Stratified coverage reported by k bucket, outcome type, and empirical Ï„Ì‚Â² quartile.

Expected fit count: ~6,386 Ã— average-k (â‰ˆ6) Ã— 10 methods â‰ˆ **400K fits**. Cheap; runs in days.

### 4.3 Secondary experiment â€” synthetic twin factorial

**MA pool:** stratified random sample of 1,500 MAs from the filtered corpus (stratified by k Ã— outcome type Ã— SE-magnitude quartile).

**Factor grid (the Standard grid â€” preregistered):**

| Factor | Levels | Values |
|---|---|---|
| True Î¼ | 1 | 0 (null-only; PI coverage is translation-invariant) |
| True Ï„Â² | 6 | {0, 0.01, 0.05, 0.15, 0.35, 0.75} |
| DGP family | 4 | Normal RE, tâ‚ƒ RE, skewed RE (log-normal shifted), mixture RE (5% contamination) |
| Real MA pool | 1,500 | stratified sample (above) |
| Replicates/cell | 2,000 | (MC SE on 95% coverage â‰ˆ 0.5%) |
| Methods | 10 | (see Â§5) |

**Per replicate:** given (k, {SE_i}, Ï„Â², DGP family):
1. Draw k random-effects offsets `b_i ~ DGP(0, Ï„Â²)`.
2. Draw k observed effects `y_i ~ N(b_i, SE_iÂ²)`.
3. Fit each of 10 PI methods â†’ get (PI lower, PI upper, Î¼Ì‚, CI Î¼Ì‚, Ï„Ì‚Â²).
4. Draw ONE new-study true effect `Î¼_new ~ DGP(0, Ï„Â²)`.
5. Draw ONE new-study observed effect `y_new = Î¼_new + Îµ, Îµ ~ N(0, SE_newÂ²)` where `SE_new` is drawn from the empirical SE distribution of the parent MA (bootstrap from `{SE_i}`).
6. Record BOTH coverage indicators:
   - `coverage_true = 1{pi_lower â‰¤ Î¼_new â‰¤ pi_upper}` (classical PI estimand â€” for Q2 & literature comparison)
   - `coverage_obs = 1{pi_lower â‰¤ y_new â‰¤ pi_upper}` (observed-effect estimand â€” for Q3 / misspecification gap vs LOO)
7. Record bias: `Î¼Ì‚ âˆ’ 0`, RMSE contribution: `(Î¼Ì‚)Â²`, Ï„Ì‚Â² error: `Ï„Ì‚Â² âˆ’ Ï„Â²`.

**Total synthetic fits:** 1,500 Ã— 1 Ã— 6 Ã— 4 Ã— 2,000 Ã— 10 = **720 million fits**. At ~10ms/fit (Python) on 8 cores, ~2,000 core-hours â‰ˆ 10 weeks of wall clock. Comfortable fit in a year with 40Ã— headroom.

### 4.4 Misspecification gap (the headline)

For each of 1,500 sampled MAs and each of 10 methods:

- Compute `real_coverage_MA = 1/k Â· Î£_j 1{y_j âˆˆ PI_{-j}}` (real LOO coverage for that MA, using observed held-out effect `y_j`).
- Compute `synth_coverage_MA_observed = mean over replicates of 1{y_new âˆˆ PI}` where `y_new = Î¼_new + Îµ_new, Îµ_new ~ N(0, SE_jÂ²)` â€” i.e. the synthetic twin matched to the **observed-effect estimand**, not the true-effect estimand.
- Report `gap_MA = real_coverage_MA âˆ’ synth_coverage_MA_observed` distribution.

**Estimand note (important):** Because LOO observes `y_j`, not the unobservable true effect `Î¼_j`, the primary comparison uses the *observed-effect* estimand throughout. A parallel secondary analysis reports synthetic-twin coverage of `Î¼_new` (true-effect estimand) for comparison with the classical PI literature (HTS 2009). This dual reporting prevents apples-to-oranges comparison between LOO and synthetic.

**If the median gap is significantly negative (real < synthetic under well-specified model, observed-effect estimand) â†’ published PIs are structurally under-covering** because real heterogeneity is non-normal. This is the paper's single-sentence headline.

---

## 5. Methods under test â€” preregistered list (10)

| # | PI method | Ï„Â² estimator | CI/PI formula | Implementation |
|---|---|---|---|---|
| 1 | HTS + DL | DerSimonian-Laird | `Î¼Ì‚ Â± t_{k-2} Ã— âˆš(Ï„Ì‚Â² + SE(Î¼Ì‚)Â²)` | numpy baseline |
| 2 | HTS + REML | REML | same | `statsmodels` / custom |
| 3 | HTS + PM | Paule-Mandel | same | custom (iterative) |
| 4 | HKSJ-adjusted | DL | HKSJ variance with floor `max(1, Q/(k-1))`, `t_{k-1}` df | custom (per `advanced-stats.md`) |
| 5 | Partlett-Riley | REML | Partlett-Riley bootstrap-improved PI (RSM 2017) | R `metafor::predict.rma` wrapper OR custom |
| 6 | Nagashima-Noma | REML | parametric bootstrap PI, 1,000 inner boots | R `pimeta` via subprocess OR Python port |
| 7 | Bayesian posterior predictive | Half-normal Ï„ prior (scale=0.5) | MCMC via `bayesmeta`-equivalent | R `bayesmeta` via subprocess |
| 8 | Bayesian + MAP prior | MAP-prior Ï„ (from MAPriors project) | MCMC | leverages MAPriors shipped code |
| 9 | Non-parametric cluster bootstrap | empirical | 10K bootstrap study resamples, quantile PI | custom |
| 10 | HTS + SJ | Sidik-Jonkman | `t_{k-2}` | custom |

**Implementation language:** Python primary; R via `rpy2` or subprocess for methods 5, 6, 7 (where the R implementation is the canonical reference). All fits validated against `metafor` to tolerance 1e-6 on a 5-cell baseline fixture.

**Frozen at preregistration** â€” no method added or removed after Zenodo DOI is minted.

---

## 10. Non-goals (preregistered)

- **No NMA methods.** Single pairwise comparisons only.
- **No DTA methods.** Continuous/binary/GIV effect sizes only.
- **No IPD meta-analysis.** Aggregate-data MA only.
- **No publication-bias modelling as a separate factor.** Captured indirectly via DGP misspecification (mixture family).
- **No post-hoc methods.** Methods discovered during the year â†’ follow-up paper only; marked exploratory.
- **No new Pairwise70 data ingestion.** Using frozen corpus as-shipped by `repro-floor-atlas`.
- **No GPU/distributed compute.** Single-node CPU only.

---

### 6.3 Deviations policy

Any departure from the preregistered protocol must be:
1. Recorded in DEVIATIONS.md with timestamp, reason, and commit SHA.
2. Classified as *forced* (software bug, bad data, dependency failure) or *elective* (scope reduction, method substitution).
3. Elective deviations flag the affected result as *post-hoc exploratory* in the final paper.

## Baseline Fixture Hash

SHA-256: 5909a2359e37d5e20f0d9d20294ba685040942b60b12cf3ca0c36105bb27a7d5

