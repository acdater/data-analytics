# Northstar Retail Analytics

An end-to-end profitability investigation for a fictional e-commerce company. I used PostgreSQL, SQL, Python and Tableau to understand why sales grew in 2025 while gross profit fell.

## Business Problem

Northstar Retail wanted to understand how COGS, pricing, discounts and product categories affected profitability across 2024-2025. The goal was to identify margin pressure and support pricing, procurement and product portfolio decisions.

## Work Completed

- Built a reproducible PostgreSQL dataset and checked data quality with SQL.
- Used Python to investigate sales, costs, discounts, category mix and returns.
- Exported monthly and category profitability datasets for Tableau.
- Built a dashboard with YoY KPIs, monthly trends and category comparisons.

## Key Findings

| Metric | 2025 | Change vs 2024 |
| --- | --- | --- |
| Net sales | 980.7K | +8.14% |
| COGS | 697.4K | +14.69% |
| Gross profit | 283.3K | -5.19% |
| Gross margin | 28.89% | -4.06 pp |

Costs grew faster than sales. The exploratory category analysis suggests that most margin pressure came from within categories, rather than a shift in sales mix. Next steps: compare prices and costs for the same products, review discount effectiveness and prioritize categories with margin improvement potential.

These are scenario results: delivered orders only, refunds assigned to the original order period, and an assumed 80% recovery of returned inventory cost. Taxes and shipping are excluded. The data is synthetic, not real company performance.

## Review the Project

1. Start with the [organized Python notebook](notebooks/01-profitability-eda-organized.ipynb) for the analysis, checks and conclusions.
2. Open the [Tableau dashboard](tableau/01-northstart-retail-dashboard.twbx) in Tableau Desktop to review KPIs, trends and category performance.
3. Review the [SQL analysis](sql/exercises/README.md), [exported datasets](data/processed/) and [data dictionary](database/DATA_DICTIONARY.md) for supporting work.

## Quick Start

Requirements: Docker Desktop with Compose, `uv`, and Python 3.12 (uv can install the version selected by `.python-version`).

```sh
cp .env.example .env
uv sync --locked
make start
make init
make seed
make validate
uv run jupyter lab
```

Select the project Python environment in Jupyter and run the organized notebook from top to bottom. `make seed` replaces rows in all eight project tables with the same generated dataset; it preserves the Docker volume.

## Database Commands

| Command | Effect |
| --- | --- |
| `make setup` | Install the locked environment. |
| `make start` / `make stop` | Start or stop PostgreSQL, keeping its data. |
| `make logs` | Follow database logs. |
| `make init` | Apply the repeatable schema. |
| `make seed` | Replace project data with the fixed-seed dataset. |
| `make validate` | Check row counts, relationships and financial arithmetic. |
| `make reset` | Permanently remove the project database and its volume. |

## Connection Details

For pgAdmin or Tableau's PostgreSQL connector, use host `127.0.0.1`, port `5433`, database `northstar_retail`, and the credentials in `.env`. Install Tableau's PostgreSQL driver if prompted. This database is for local use only; do not expose it to a network or commit credentials.

## Project Notes

PostgreSQL 18 holds eight related tables covering orders, products, customers, payments, returns and marketing spend. The generator uses seed `20261025` for repeatable results. Raw database rows are generated locally; the two reporting CSVs are included in [data/processed](data/processed/).