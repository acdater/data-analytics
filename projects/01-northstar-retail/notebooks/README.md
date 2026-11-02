# Python Analysis

I used pandas and SQLAlchemy to investigate profitability across 2024-2025: data quality, sales and cost trends, category mix, discounts, order statuses and returns.

- [Organized notebook](01-profitability-eda-organized.ipynb): main review version with checks, findings and reporting exports.
- [Original notebook](01-profitability-eda.ipynb): initial exploration.

To rerun, follow the [project setup](../README.md), launch `uv run jupyter lab` from the project root and run the organized notebook top to bottom using the project environment. Database credentials are read from `.env`.

The final scenario uses delivered orders, refunds assigned to the original order period and assumed 80% inventory recovery. Monthly and category exports are in [data/processed](../data/processed/).