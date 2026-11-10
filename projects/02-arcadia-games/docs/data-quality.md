# Data quality and observation boundaries

## Authoritative state versus telemetry

`players`, `sessions`, `level_attempts`, `purchases`, experiment records, and catalogs are authoritative simulator records. They do not inherit event loss. `events` is the observed, deduplicated telemetry stream. Source event identifiers remain stable and unique; deliberate duplicate deliveries are not included in this version.

Both completed and interrupted sessions have authoritative `ended_at` and positive duration. For an interrupted session, this timestamp is the simulator's termination boundary, not a received logout event. Its final attempt is abandoned and has no completion or failure event. An interrupted session never has `session_end`. Some otherwise completed sessions also lack `session_end` because of telemetry loss. Therefore, absence of an end event alone cannot determine authoritative interruption or exact duration.

Selected reward and completed-session end events can be lost. Gaps in `event_sequence` are allowed. Core attempt lifecycle, purchase lifecycle, and tutorial events are retained so their semantics remain unambiguous. Event sequence reflects source order within one session; IDs and physical row order do not imply global chronological order.

Most receipts follow emission promptly; a small fraction is delayed up to 72 hours. Receipts can arrive out of order and after the observation window ends. `event_timestamp` remains within its session; `received_at` is when the collector sees it. This is an event-time snapshot with a 72-hour collection grace period, not an ingestion-time cutoff. Client-clock skew is not simulated.

## Intentional missing values

| Field | Meaning of null |
| --- | --- |
| `players.country` | Registration country attribution unavailable. |
| `players.campaign_id` | Organic player, or paid acquisition with unavailable campaign attribution. The channel can still be known. |
| `purchases.resolved_at` | Transaction remains pending; it has no recognized revenue. No subsequent reconciliation is modeled. |
| `events.attempt_id` / `purchase_id` | Event does not refer to that kind of object. |
| `session_start.properties.network_type` | Device network information unavailable. The property is present with JSON null. |

Nulls, late arrivals, and documented omissions are intentional imperfections. Invalid keys, contradictory lifecycle events, negative durations, purchases outside their sessions, and impossible progression are generator defects and must fail validation.

## Integrity validation

`make validate` checks chronology, nonoverlapping sessions, contiguous session and attempt numbering, level unlocks, interrupted outcomes, event source order and boundaries, payload contracts, required lifecycle events, monetary normalization, campaign dates, and experiment eligibility/assignment/exposure. Database PK, UNIQUE, CHECK, and FK constraints are active during COPY. Duplicate IDs and invalid references cannot be loaded. The validator also checks that constraints are validated, stored counts agree with the manifest, and profile count ranges hold.

The generator uses one transaction and validates before commit. The validator streams JSON payloads through a server-side cursor. Tests inject invalid values and malformed telemetry, compare repeated generation and multiple batch sizes, and simulate interruption during replacement.

Row-count ranges are broad smoke checks, not proof of behavioral realism or experiment significance. Small samples can lack statistical power. Observation-window censoring, incomplete attribution, and the distinction between assignment and exposure remain analysis decisions for the learner.

## Generator distribution checks

`make validate` also runs generation-quality checks from `config/behavior.toml`, using bounded histograms rather than loading every event into memory. These checks detect collapsed session durations, excessive repeated values, weak variation, missing short or long sessions, implausible tails, and fixed attempt/checkout timings. Duration statistics are reported in seconds. They describe generator output, not a business conclusion.

The population checks require at least 1,000 sessions. New-player versus established-session checks require at least 250 observations in each group; checkout variation requires 50 resolved transactions. Smaller samples explicitly report skipped checks, not evidence of a segment effect. The broad segment tolerance is a generator sanity check, not a statistical significance test. The controlled engagement test uses synthetic timing draws at matched progression and history, rather than interpreting observational segmentation as causal evidence.

The timing model draws continuous values then rounds to integer seconds to preserve the schema. Session ends follow the action timeline; there is no independent duration reassignment. Newly generated identifiers and content checksums are reproducible within generator version 1.1.0 and its fixed configuration, but are not intended to reproduce version 1.0.0 rows. The attempt identifier multiplier is now 1,000 to avoid collisions when long sessions have more than nine attempts.
