# Data dictionary

All tables are in PostgreSQL schema `arcadia`. `TIMESTAMPTZ` values represent instants and are displayed in UTC by the project connection. Dates are UTC calendar dates. All columns are required unless explicitly marked nullable below. PKs imply NOT NULL; composite FKs preserve session ownership and release consistency. No cascading deletion is configured.

Operational records are authoritative simulated state; `events` is imperfect received telemetry. Last-seen, retention, churn, and payer segmentation are not independently generated attributes or supplied metrics.

Money uses exact NUMERIC values and Python Decimal arithmetic. Supported source currencies USD, EUR, and GBP have two decimal places. Daily rates are fully synthetic: USD = 1; EUR and GBP follow fixed smooth illustrative paths around 1.09 and 1.28 USD per unit. These are not historical market rates. `revenue_usd = round(amount × usd_per_unit, 2)` only for completed transactions, using initiation-date rates and half-up rounding. Non-completed transactions have zero revenue. Campaign spend is already USD. Catalog prices are reference USD prices; converting to local cents and back can differ by a cent. Fees, taxes, refunds, and FX gains/losses are outside scope.

## `campaigns`

One named acquisition campaign. PK: campaign_id.

| Column | Type | Nullable | Business meaning |
| --- | --- | --- | --- |
| `campaign_id` | `INTEGER` | No | Campaign identifier; optional only on players. |
| `name` | `TEXT` | No | Human-readable synthetic name. |
| `channel` | `TEXT` | No | paid_social, paid_search, or creator. |
| `starts_on` | `DATE` | No | First active campaign date, inclusive. |
| `ends_on` | `DATE` | No | Last active campaign date, inclusive. |

## `campaign_daily_spend`

One campaign on one UTC calendar date. Composite PK: campaign_id, spend_date. FK: campaign_id → campaigns.

| Column | Type | Nullable | Business meaning |
| --- | --- | --- | --- |
| `campaign_id` | `INTEGER` | No | Campaign identifier; optional only on players. |
| `spend_date` | `DATE` | No | UTC date of advertising delivery. |
| `spend_usd` | `NUMERIC(12,2)` | No | Synthetic advertising spend in USD. |
| `impressions` | `INTEGER` | No | Nonnegative daily impression count. |
| `clicks` | `INTEGER` | No | Nonnegative clicks, no greater than impressions. |

## `game_releases`

One game version for one platform. PK: release_id. Unique: version, platform.

| Column | Type | Nullable | Business meaning |
| --- | --- | --- | --- |
| `release_id` | `INTEGER` | No | Platform-specific release identifier. |
| `version` | `TEXT` | No | Semantic version label. |
| `platform` | `TEXT` | No | ios or android. |
| `released_at` | `TIMESTAMPTZ` | No | First availability for this platform; sessions cannot use it earlier. |

## `levels`

One sequentially unlocked level. PK: level_id.

| Column | Type | Nullable | Business meaning |
| --- | --- | --- | --- |
| `level_id` | `INTEGER` | No | Sequential level number, starting at one. |
| `name` | `TEXT` | No | Human-readable synthetic name. |
| `chapter` | `INTEGER` | No | Positive chapter number. |

## `level_configurations`

One level configuration for one platform release. Composite PK: level_id, release_id. FKs: level_id → levels; release_id → game_releases.

| Column | Type | Nullable | Business meaning |
| --- | --- | --- | --- |
| `level_id` | `INTEGER` | No | Sequential level number, starting at one. |
| `release_id` | `INTEGER` | No | Platform-specific release identifier. |
| `difficulty` | `NUMERIC(5,3)` | No | Dimensionless design configuration; not an observed failure rate. |
| `time_limit_seconds` | `INTEGER` | No | Configured attempt time limit in seconds. |

## `items`

One purchasable item in the catalog. PK: item_id. Unique: sku.

| Column | Type | Nullable | Business meaning |
| --- | --- | --- | --- |
| `item_id` | `INTEGER` | No | Catalog item identifier. |
| `sku` | `TEXT` | No | Unique stable product code. |
| `name` | `TEXT` | No | Human-readable synthetic name. |
| `category` | `TEXT` | No | currency, booster, or cosmetic. |
| `base_price_usd` | `NUMERIC(10,2)` | No | Reference USD price before synthetic local-currency rounding. |

## `exchange_rates`

One currency-to-USD rate on one UTC date. Composite PK: rate_date, currency.

| Column | Type | Nullable | Business meaning |
| --- | --- | --- | --- |
| `rate_date` | `DATE` | No | UTC date used to select the synthetic daily exchange rate. |
| `currency` | `CHAR(3)` | No | Original transaction currency: USD, EUR, or GBP. |
| `usd_per_unit` | `NUMERIC(12,6)` | No | USD per one original-currency unit; USD itself is 1.000000. |

## `players`

One registered synthetic player. PK: player_id. FK: campaign_id → campaigns. Display names are not identity keys and may repeat.

| Column | Type | Nullable | Business meaning |
| --- | --- | --- | --- |
| `player_id` | `BIGINT` | No | Synthetic stable player identifier. |
| `display_name` | `TEXT` | No | Faker-generated display name; not real identity data. |
| `registered_at` | `TIMESTAMPTZ` | No | Account registration timestamp, before any session. |
| `country` | `CHAR(2)` | Yes | Two-letter registration country or null when attribution is unavailable. |
| `platform` | `TEXT` | No | ios or android. |
| `acquisition_channel` | `TEXT` | No | organic, paid_social, paid_search, or creator. Channel can be known even if campaign is missing. |
| `campaign_id` | `INTEGER` | Yes | Campaign identifier; optional only on players. |

## `experiments`

One experiment definition. PK: experiment_id. Unique: name.

| Column | Type | Nullable | Business meaning |
| --- | --- | --- | --- |
| `experiment_id` | `INTEGER` | No | Experiment identifier. |
| `name` | `TEXT` | No | Human-readable synthetic name. |
| `starts_at` | `TIMESTAMPTZ` | No | Inclusive enrollment start. |
| `ends_at` | `TIMESTAMPTZ` | No | Exclusive enrollment and initial-exposure cutoff. |
| `eligibility_rule` | `TEXT` | No | Human-readable pre-assignment eligibility rule. |
| `exposure_trigger` | `TEXT` | No | Human-readable first-exposure action definition. |

## `experiment_variants`

One variant within an experiment. Composite PK: experiment_id, variant. FK: experiment_id → experiments.

| Column | Type | Nullable | Business meaning |
| --- | --- | --- | --- |
| `experiment_id` | `INTEGER` | No | Experiment identifier. |
| `variant` | `TEXT` | No | Assigned variant label: control or treatment. |
| `allocation` | `NUMERIC(5,4)` | No | Assignment probability; allocations sum to one within an experiment. |

## `experiment_assignments`

One immutable assignment per player and experiment. Composite PK: experiment_id, player_id. FKs: player_id → players; (experiment_id, variant) → experiment_variants.

| Column | Type | Nullable | Business meaning |
| --- | --- | --- | --- |
| `experiment_id` | `INTEGER` | No | Experiment identifier. |
| `player_id` | `BIGINT` | No | Synthetic stable player identifier. |
| `variant` | `TEXT` | No | Assigned variant label: control or treatment. |
| `assigned_at` | `TIMESTAMPTZ` | No | Time of assignment, equal to eligible registration; never based on future behavior. |

## `sessions`

One authoritative player session. PK: session_id. FKs: player_id → players; release_id → game_releases. Unique: (player_id, session_number), (session_id, player_id), and (session_id, release_id).

| Column | Type | Nullable | Business meaning |
| --- | --- | --- | --- |
| `session_id` | `BIGINT` | No | Stable session identifier: player_id × 1,000 + session_number. |
| `player_id` | `BIGINT` | No | Synthetic stable player identifier. |
| `session_number` | `INTEGER` | No | Contiguous, one-based chronological session count within player. |
| `release_id` | `INTEGER` | No | Platform-specific release identifier. |
| `started_at` | `TIMESTAMPTZ` | No | Authoritative start. |
| `ended_at` | `TIMESTAMPTZ` | No | Authoritative normal end or simulated interruption boundary; always present. |
| `duration_seconds` | `INTEGER` | No | Positive authoritative elapsed seconds; exactly ended_at minus started_at. |
| `status` | `TEXT` | No | completed or interrupted; independent of whether session_end telemetry was received. |

## `experiment_exposures`

First actual exposure for an assigned player and experiment. Composite PK: experiment_id, player_id. FKs: (experiment_id, player_id) → experiment_assignments; (session_id, player_id) → sessions.

| Column | Type | Nullable | Business meaning |
| --- | --- | --- | --- |
| `experiment_id` | `INTEGER` | No | Experiment identifier. |
| `player_id` | `BIGINT` | No | Synthetic stable player identifier. |
| `session_id` | `BIGINT` | No | Stable session identifier: player_id × 1,000 + session_number. |
| `exposed_at` | `TIMESTAMPTZ` | No | First tutorial-start exposure after assignment and before the exposure cutoff. |

## `level_attempts`

One authoritative attempt within a session. PK: attempt_id. FKs: (session_id, release_id) → sessions; (level_id, release_id) → level_configurations. Unique: (session_id, attempt_number) and (attempt_id, session_id).

| Column | Type | Nullable | Business meaning |
| --- | --- | --- | --- |
| `attempt_id` | `BIGINT` | No | Stable attempt identifier: session_id × 10 + attempt_number. |
| `session_id` | `BIGINT` | No | Stable session identifier: player_id × 1,000 + session_number. |
| `release_id` | `INTEGER` | No | Platform-specific release identifier. |
| `level_id` | `INTEGER` | No | Sequential level number, starting at one. |
| `attempt_number` | `INTEGER` | No | Contiguous one-based order within session. |
| `started_at` | `TIMESTAMPTZ` | No | Authoritative attempt start. |
| `ended_at` | `TIMESTAMPTZ` | No | Authoritative resolution or interruption time. |
| `outcome` | `TEXT` | No | completed, failed, or abandoned. Only completion advances progression. |

## `purchases`

One authoritative transaction attempt, including unsuccessful and pending attempts. PK: purchase_id. FKs: (session_id, player_id) → sessions; item_id → items; (rate_date, currency) → exchange_rates. Unique: purchase_id, session_id.

| Column | Type | Nullable | Business meaning |
| --- | --- | --- | --- |
| `purchase_id` | `BIGINT` | No | Transaction identifier; this generator allows at most one per session and uses session_id. |
| `session_id` | `BIGINT` | No | Stable session identifier: player_id × 1,000 + session_number. |
| `player_id` | `BIGINT` | No | Synthetic stable player identifier. |
| `item_id` | `INTEGER` | No | Catalog item identifier. |
| `initiated_at` | `TIMESTAMPTZ` | No | Transaction start, after shop entry and within its session. |
| `resolved_at` | `TIMESTAMPTZ` | Yes | Resolution timestamp; null only while pending. |
| `status` | `TEXT` | No | completed, failed, or pending. |
| `currency` | `CHAR(3)` | No | Original transaction currency: USD, EUR, or GBP. |
| `rate_date` | `DATE` | No | UTC date used to select the synthetic daily exchange rate. |
| `amount` | `NUMERIC(10,2)` | No | Positive original-currency attempted charge; not automatically recognized revenue. |
| `revenue_usd` | `NUMERIC(12,2)` | No | Completed charge × dated exchange rate, rounded half-up to cents; zero for failed/pending transactions. |

## `events`

One received, deduplicated source event. PK: event_id. FK: session_id → sessions; (attempt_id, session_id) → level_attempts; (purchase_id, session_id) → purchases. Unique: session_id, event_sequence.

| Column | Type | Nullable | Business meaning |
| --- | --- | --- | --- |
| `event_id` | `BIGINT` | No | Stable source event ID: session_id × 1,000 + event_sequence. |
| `session_id` | `BIGINT` | No | Stable session identifier: player_id × 1,000 + session_number. |
| `event_sequence` | `INTEGER` | No | Positive source order within session; gaps are allowed after event loss. |
| `event_timestamp` | `TIMESTAMPTZ` | No | UTC occurrence/emission time within its session. |
| `received_at` | `TIMESTAMPTZ` | No | UTC collector receipt, at or after event time; may be up to 72 hours later. |
| `event_type` | `TEXT` | No | One of the 13 documented event names. |
| `attempt_id` | `BIGINT` | Yes | Stable attempt identifier: session_id × 10 + attempt_number. |
| `purchase_id` | `BIGINT` | Yes | Transaction identifier; this generator allows at most one per session and uses session_id. |
| `properties` | `JSONB` | No | Versioned event payload; see event taxonomy for exact required keys and types. |

## `generation_runs`

One manifest for the currently loaded synthetic dataset. PK: run_id; constrained to 1. Operational reproducibility metadata, not a player fact.

| Column | Type | Nullable | Business meaning |
| --- | --- | --- | --- |
| `run_id` | `INTEGER` | No | Singleton identifier, always 1. |
| `generator_version` | `TEXT` | No | Semantic version of the generator implementation. |
| `profile` | `TEXT` | No | Named configuration profile. |
| `seed` | `BIGINT` | No | Nonnegative root seed. |
| `player_count` | `INTEGER` | No | Configured player count. |
| `observation_start` | `TIMESTAMPTZ` | No | Inclusive event-time window start. |
| `observation_end` | `TIMESTAMPTZ` | No | Exclusive event-time window end. |
| `content_sha256` | `TEXT` | No | SHA-256 of canonical source rows in deterministic generation order; excludes timing and this manifest. |
| `row_counts` | `JSONB` | No | Generated row counts keyed by table name; excludes this singleton manifest. |

## Relationship and constraint notes

Campaigns can acquire many players and have daily spend. Players have many sessions, transactions, and experiment assignments. Sessions own attempts and telemetry; releases select the applicable level configurations. Events reference attempts and purchases only when their type requires it. An assignment may have zero exposures; absence of exposure is not reassignment. There is one first exposure at most per assignment.

Local DDL constraints enforce allowed categories, positive amounts, nonnegative revenue, timestamp ordering within records, and uniqueness. Cross-record chronology, release availability, progression, payload consistency, experiment coverage, and money reconciliation are checked by `make validate`. A completed session can lack an end event; an interrupted session always lacks one. See [data quality](data-quality.md) for intentional missingness and [event taxonomy](event-taxonomy.md) for payload contracts.

`level_configurations.time_limit_seconds` bounds completed and failed attempts. Abandoned attempts end at the authoritative interruption boundary, which can include idle time; they do not imply time-limit completion. The generator currently caps histories at 400 sessions and the catalog at 100 levels; these are simulator limits, not inferred business rules.
