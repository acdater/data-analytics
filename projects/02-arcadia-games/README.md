# Arcadia Games — Dungeon Rush

A reproducible synthetic environment for practicing product analytics, game analytics, statistics, and analytics engineering. Dungeon Rush is a fictional mobile free-to-play dungeon game. Every player, transaction, campaign, and gameplay record is synthetic.

The project supplies operational data and imperfect event telemetry. You define the metrics, explore the data, test hypotheses, build dashboards, and make recommendations. No analytical exercises are solved here.

## Start locally

Requirements: Docker with Compose, uv, and Python 3.12+ (the project pins Python 3.12). Run commands from `projects/02-arcadia-games`.

```sh
cp .env.example .env
make setup
make start
make init
make test
make seed
make validate
make test-integration
```

`make seed` generates the **1,000-player development profile** for `[2025-01-01, 2026-01-01)` UTC. It refuses to overwrite populated tables. The command validates before committing and prints counts, a deterministic content checksum, elapsed time, and Python peak memory. Re-running `make init` is safe with this schema version; it does not migrate an existing schema to a different version.

To deliberately regenerate project data:

```sh
uv run --locked --env-file .env arcadia generate --profile development --replace
```

Replacement is atomic. Failure or interruption rolls back to the previous dataset; an initial failed load leaves empty tables. Restart the command from the beginning; partial-run resume is not implemented. `--replace` affects only the `arcadia` schema in the `arcadia_games` database. No automatic destructive reset occurs.

The separate `portfolio` configuration has 50,000 players and intended ranges of roughly 700,000 sessions, 5–8 million events, 1–2 million attempts, and 20,000–40,000 transaction attempts. It is available for later use; the full dataset has **not** been generated or benchmarked. Counts are stochastic outcomes, not padded quotas. See [development verification](docs/development-validation.md) for actual measured scope.

## Connect and work

| Setting | Default |
| --- | --- |
| Host / port | `127.0.0.1:5434` |
| Database / schema | `arcadia_games` / `arcadia` |
| Username / password | Values in local `.env` |
| Docker project / volume | `arcadia-games` / `arcadia_games_pgdata` |

Choose the `arcadia` schema in Tableau or your database client. Python connections created with `arcadia.common.db.engine()` set the search path and UTC automatically. Other clients should use UTC and schema-qualified table names. Use `uv run --locked --env-file .env jupyter lab` to start your own notebooks; select this project's Python environment. Tableau may require its PostgreSQL driver.

## Architecture

`config/profiles.toml` → deterministic Python simulation → bounded psycopg COPY batches → PostgreSQL operational tables and event telemetry → integrity validation.

- `database/schema/`: reproducible DDL and constraints.
- `database/seeds/`: catalog-seeding documentation; catalogs are generated in Python.
- `database/validation/`: data-quality assertions only.
- `src/arcadia/generator/`: catalog creation and chronological player simulation.
- `src/arcadia/ingestion/`: bounded loading and validation.
- `src/arcadia/common/`: configuration, connection setup, event contracts.
- `sql/`, `notebooks/`, `tableau/`, `reports/`: your empty analytics workspaces.
- `dbt/`: preparation notes for future learner-built models.

The generator keeps a single player's behavioral state and a bounded buffer in memory. Fixed reference catalogs cover the observation window. It does not create a full in-memory DataFrame or export raw datasets. `BATCH_SIZE=5000` controls the maximum number of pending ingestion rows across all tables, not per table. PostgreSQL disk, WAL, indexes, and transaction costs still grow with dataset size.

Authoritative sessions and attempts describe what occurred in the simulation. `events` represents received telemetry and can omit selected events or arrive late. All lifecycle metrics, including last activity and churn definitions, are left for you to derive. Experiment assignment and first exposure are distinct records.

## Commands

| Command | Effect |
| --- | --- |
| `make setup` | Install dependencies from `uv.lock`. |
| `make start` / `make stop` | Start/stop Arcadia PostgreSQL, preserving data. |
| `make init` | Start the service and apply repeatable schema creation. |
| `make seed` | Generate and validate development data into an empty schema. |
| `make validate` | Check stored data; return nonzero on a failure. |
| `make test` | Run generator tests without PostgreSQL. |
| `make test-integration` | Run database tests; all test mutations roll back. |
| `make logs` | Follow Arcadia database logs. |
| `make reset` | **Delete Arcadia's database volume and all its data.** |

An alternate seed is available through `arcadia generate --seed N`. Statistical range checks may reject unusually small or atypical populations. The supported profiles are configured in TOML; fixed dates and seed avoid dependence on the current clock. Reproducibility requires the same generator version, configuration, and locked dependencies. The manifest stores the source-content checksum and row counts; timings are reported separately because they vary between runs.

## Learning materials

Start with [business context](docs/business-context.md), [data dictionary](docs/data-dictionary.md), [event taxonomy](docs/event-taxonomy.md), [data quality](docs/data-quality.md), and the [analytics backlog](docs/analytics-backlog.md).

Generator internals and `docs/maintainer/` contain implementation ground truth and spoilers. They are separate from the learning materials; you do not need to read them to begin analysis.

Implementation references: [PostgreSQL timestamp types](https://www.postgresql.org/docs/18/datatype-datetime.html), [psycopg COPY](https://www.psycopg.org/psycopg3/docs/basic/copy.html), and [uv locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/).
