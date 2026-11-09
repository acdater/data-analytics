# Development verification

Verified on November 9, 2026 with Python 3.12.14, locked dependencies, and the isolated PostgreSQL 18 Docker service. Observation window: `[2025-01-01, 2026-01-01)` UTC. Profile: development; seed: 20261109; generator version: 1.0.0.

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
| `sessions` | 13,625 |
| `events` | 133,074 |
| `level_attempts` | 31,409 |
| `purchases` | 676 |
| `experiment_assignments` | 512 |
| `experiment_exposures` | 512 |
| `generation_runs` | 1 |

## Checks and reproducibility

All **35 integrity checks passed with zero violations** on both full development loads. All **11 pytest tests passed**, including database constraint rejection, batch-size-independent ingestion, corruption detection, and interrupted-replacement rollback. Database tests run transactionally and preserve the loaded development data.

Two separate 1,000-player loads using batch sizes 5,000 and 997 produced identical row counts and canonical source-content SHA-256:

```text
290af5668ef7d6497113a6eaf95232bbdaaa2e2810c6441e66e2ffcf28f131a4
```

The integration test additionally compares stored event-row digests after loads with batch sizes 1 and 731. Event payloads and every required lifecycle relationship pass validation. Schema initialization succeeded on a fresh database and on repeated application.

## Measured performance

| Measurement | 5,000-row buffer | 997-row buffer |
| --- | ---: | ---: |
| Generation and ingestion (seconds) | 6.067 | 6.914 |
| Validation (seconds) | 2.183 | 1.9 |
| Total including commit (seconds) | 8.256 | 8.819 |
| Peak Python process RSS (MiB) | 75.7 | 74.23 |
| Maximum pending ingestion rows | 5000 | 997 |

Peak memory is measured for the Python client process, not the PostgreSQL container or total host memory. These are local development measurements, not a production benchmark. Indexed event references avoid repeated full-table scans during integrity checks.

The 50,000-player portfolio profile has **not been generated**. Full-scale performance and exact counts remain unverified. The loader and payload validator use bounded buffers/server-side streaming; PostgreSQL storage, indexes, and WAL will still grow with dataset size. The development population is suitable for checking the workflow, not guaranteed statistical power; reference campaign budgets are shared between profiles, so acquisition economics are not directly comparable across profile sizes.

Only the synthetic development data is stored locally in the dedicated Docker volume. No raw dataset files, solved analytical queries, notebooks, dbt models, Tableau dashboards, or business conclusions were added.
