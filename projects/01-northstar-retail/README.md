# Northstar Retail Analytics

Northstar Retail is a fictional multi-category e-commerce business. Use its local PostgreSQL dataset to investigate management's concern that revenue is growing while profitability may be changing. The dataset is synthetic and deterministic; it contains no real customer information.

## Quick Start

Requirements: Docker Desktop with Compose, `uv`, and Python 3.12 (uv can install the version selected by `.python-version`).

```sh
cp .env.example .env
uv sync --locked
make start
make init
make seed
make validate
```

`make seed` also starts the database and reapplies the idempotent schema. Seeding replaces the rows in all eight Northstar tables with the same generated dataset each time. It does not recreate or delete the Docker volume.

## Lifecycle Commands

| Command | Effect |
| --- | --- |
| `make setup` | Install the locked project environment with uv. |
| `make start` | Start PostgreSQL and wait for its health check. |
| `make stop` | Stop the database while preserving its volume. |
| `make logs` | Follow PostgreSQL logs. Press Ctrl-C to stop following logs. |
| `make init` | Apply the repeatable schema to the running database. |
| `make seed` | Replace training rows with the fixed-seed dataset. |
| `make validate` | Check connectivity, row counts, relationships and financial arithmetic. |
| `make reset` | Stop and remove this Compose project and its named database volume. |

`make reset` permanently removes the Northstar database data. It is intentionally separate from `make stop` and `make seed`. The Compose project and volume are named for Northstar; these commands do not target other Compose projects.

## External Connections

The database is available only on the local machine at `127.0.0.1:5433`.

**pgAdmin:** Register a server using host `127.0.0.1`, port `5433`, database `northstar_retail`, and the username/password in `.env`. Set maintenance database to `northstar_retail`; SSL can be disabled for this local simulation.

**Tableau Desktop:** Choose the PostgreSQL connector and use the same host, port, database, username, and password. Install Tableau's PostgreSQL driver separately if Tableau prompts for it. Do not expose this development database to a network.

## Database

PostgreSQL 18 stores eight related tables. `database/schema.sql` defines primary keys, foreign keys, checks, uniqueness constraints and indexes. See [the data dictionary](database/DATA_DICTIONARY.md) for table and field descriptions.

The schema covers customers, product categories and products, orders and order lines, payment events, returns, and monthly marketing spend. Prices and costs on order lines are snapshots; product catalog values represent the current catalog. Timestamps span January 2024 through December 2025.

## Reproducibility

The generator uses NumPy seed `20261025`; generated rows are created in Python and inserted transactionally. Rerunning `make seed` produces the same row content and keys. No generated dataset is stored in Git. Runtime credentials belong in ignored `.env`; `.env.example` contains local-only sample values. Change the sample password before using the setup outside a private development machine.

## Learning Materials

- [SQL exercise prompts](sql/exercises/README.md)
- [Notebook workspace](notebooks/README.md)
- [Reports workspace](reports/README.md)
- [Tableau workspace](tableau/README.md)

The prompts are intentionally open-ended. There are no completed analytical queries, report conclusions, dashboards, or notebook solutions in this project.