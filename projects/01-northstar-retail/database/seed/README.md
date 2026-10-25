# Synthetic Data Seed

The deterministic generator lives in `src/northstar_retail_analytics/seed.py`. It creates data in memory and writes it to PostgreSQL; it does not export or commit generated files. Run it with `make seed` from the project root. The command replaces rows only in the Northstar training tables.