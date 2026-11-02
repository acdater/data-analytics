# Synthetic Data Seed

The [Python generator](../../src/northstar_retail_analytics/seed.py) creates the synthetic PostgreSQL dataset used in this project. A fixed seed (`20261025`) makes the results repeatable; no real customer data is used.

After the [project setup](../../README.md), run `make seed` from the project root, then `make validate`. Seeding replaces rows in all eight Northstar tables and preserves the database volume.

Raw data is generated locally. The notebook's reporting exports are included in [data/processed](../../data/processed/).