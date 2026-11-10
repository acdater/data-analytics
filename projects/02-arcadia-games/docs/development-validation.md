# Development verification — generator 1.1.0

Verified on November 9, 2026 with Python 3.12.14, locked dependencies, and the isolated PostgreSQL 18 Docker service. Profile: development; 1,000 players; seed: 20261109; observation window: `[2025-01-01, 2026-01-01)` UTC.

This generator QA record supersedes the version 1.0.0 verification. It contains the requested distribution diagnostics, not a business analysis. The original two-duration session template has been replaced by a sequential time-budget simulation. The database schema is unchanged.

## Table counts

| Table | Rows |
| --- | ---: |
| `campaigns` | 3 |
| `campaign_daily_spend` | 1,095 |
| `game_releases` | 8 |
| `levels` | 100 |
| `level_configurations` | 800 |
| `items` | 5 |
| `exchange_rates` | 1,095 |
| `experiments` | 1 |
| `experiment_variants` | 2 |
| `players` | 1,000 |
| `sessions` | 12,809 |
| `level_attempts` | 45,761 |
| `purchases` | 721 |
| `events` | 181,594 |
| `experiment_assignments` | 512 |
| `experiment_exposures` | 512 |
| `generation_runs` | 1 |

## Session-duration diagnostics

All durations are seconds. Percentiles use linear interpolation; fractional percentiles do not imply sub-second stored durations.

| Statistic | Value |
| --- | ---: |
| Mean | 412.62 |
| Median | 303.00 |
| P25 | 174.00 |
| P75 | 524.00 |
| P90 | 830.00 |
| P99 | 1,805.84 |
| Minimum | 9 |
| Maximum | 3,273 |
| Distinct values | 1,506 |

## Verification

- All **38 integrity checks** passed with zero violations, including all previous checks plus attempt time limits, shop-after-gameplay, and tutorial-before-gameplay timing.
- All **14 distribution-quality checks** passed. No segment or purchase check was skipped for the development profile.
- All **18 automated tests** passed. Coverage includes temporal invariants, fixed-seed reproducibility, telemetry independence, batch-size independence, corruption rejection, interrupted-load rollback, and regressions for constant, two-valued, and uniform duration distributions.
- The controlled engagement test uses a configurable tolerance and was rechecked after moving that tolerance into the configuration file.
- Two complete development loads with batch sizes 5,000 and 997 produced identical row counts, duration diagnostics, and source-content checksum:

```text
fc344fbdc5c8c37bf3fbe6174481a4dae0c4f773a4e0efc49a13a03bdce5da68
```

## Measured performance

| Measurement | 5,000-row buffer | 997-row buffer |
| --- | ---: | ---: |
| Generation and ingestion (seconds) | 8.055 | 9.131 |
| Validation including distribution checks (seconds) | 2.203 | 2.891 |
| Total including commit (seconds) | 10.266 | 12.039 |
| Peak Python RSS (MiB) | 76.75 | 74.72 |
| Maximum pending ingestion rows | 5000 | 997 |

Memory figures cover the Python client, not PostgreSQL or host-wide memory. Session planning holds only one session; loading uses bounded COPY buffers; quality checks stream primitive fields into bounded histograms. No raw dataset files are retained in the repository.

## Changed assumptions

Intended play time is log-normal with within-player variation and shared engagement, progression, newcomer, and prior-failure effects. Attempts and pauses vary, and attempts are no longer squeezed into fixed slots. Interruption probability depends on active combat exposure. Shop browsing, checkout, and exit are individually timed. Repeated-failure continuation uses a fraction rather than raw failure count; same-day return delays are continuous; star outcomes depend noisily on skill and difficulty.

See the maintainer-only [timing assumptions and QA thresholds](maintainer/behavior-and-timing.md) for parameters and limitations. No claim is made that these parameters were estimated from real game telemetry. The 50,000-player portfolio profile remains ungenerated and unbenchmarked, and its row-count targets need separate qualification under this model. The learner's SQL, notebooks, dbt workspace, dashboards, and Northstar project were not modified.
