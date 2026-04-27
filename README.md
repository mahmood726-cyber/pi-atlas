# PI Atlas

> Year-long, dedicated-compute calibration study of **prediction-interval (PI) coverage** in random-effects meta-analysis, evaluated against the Cochrane Pairwise70 corpus (7,545 MAs / 595 reviews).

## Status

**PREREGISTRATION PHASE — no compute has run, no results exist.**

This repository currently holds the design spec and Plan 1 only. Code, baselines, and results will be added on a dedicated compute machine over the next year per the spec's deviations policy. Any departure from the preregistered protocol will be recorded in `DEVIATIONS.md` with timestamp, reason, and commit SHA.

The preregistration anchor is the tag `preregistration-v1.0.0` (also targeted at Zenodo DOI + OpenTimestamps + Internet Archive once compute begins).

## Headline question

Does the 95% prediction interval that Cochrane reviews most commonly publish (HTS + DerSimonian-Laird, `μ̂ ± t_{k-2} √(τ̂² + SE(μ̂)²)`) actually cover new-study true effects at nominal rate when confronted with real Cochrane heterogeneity structure?

Primary analysis: leave-one-out coverage on the real corpus (~6,386 MAs with k≥3, ~400K fits).

Secondary analysis: 720M-fit synthetic factorial (10 PI methods × 6 τ² levels × 4 DGP families × 1,500 empirically-anchored MAs × 2,000 replicates) to attribute miscoverage to specific heterogeneity mechanisms.

## Documents

- **Spec v1.0:** [`docs/superpowers/specs/2026-04-21-pi-atlas-design.md`](docs/superpowers/specs/2026-04-21-pi-atlas-design.md)
- **Plan 1 (Foundation + Preregistration):** [`docs/superpowers/plans/2026-04-21-pi-atlas-p1-foundation.md`](docs/superpowers/plans/2026-04-21-pi-atlas-p1-foundation.md)

## Sister projects (same Pairwise70 corpus)

- [repro-floor-atlas](https://github.com/mahmood726-cyber/repro-floor-atlas) — 14.3% non-reproducible at |Δ|>0.005
- [cochrane-modern-re](https://github.com/mahmood726-cyber/cochrane-modern-re) — DL→REML+HKSJ+PI flip-rate analysis

## Compute boundary

- Source corpus, intermediate parquets, MCMC chain dumps, and per-replicate scratch files are NOT committed (see `.gitignore`). Only summary CSVs, figures, baselines, and manuscripts get committed back from the compute machine.
- Storage budget on the compute PC: ~2 TB scratch expected; ~10 GB committed back to this repo by end of project.

## License

MIT — see [LICENSE](LICENSE).
