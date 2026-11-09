# Event taxonomy

Each row is one **received source event**. Required envelope fields are `event_id`, `session_id`, `event_sequence`, `event_timestamp`, `received_at`, `event_type`, and `properties`. Every payload includes integer `schema_version: 1`. Extra payload keys are rejected by the version-1 validator. Payload IDs must match their referenced operational rows.

`event_id = session_id * 1000 + event_sequence` is stable for the fixed generator/configuration. Sequence is assigned before optional telemetry loss. It starts at one for each session, increases in emission order, and may contain gaps. Sequence breaks ties at equal timestamps; `received_at` and IDs must not be used to infer source order across sessions.

| Event | Additional required JSON properties | Reference | Semantics |
| --- | --- | --- | --- |
| `session_start` | `network_type`: `wifi`, `cellular`, or null | None | First source event, at authoritative session start. |
| `session_end` | `reason`: `normal` | None | At authoritative end of a completed session; can be lost. Never emitted for interruption. |
| `tutorial_started` | `tutorial_id`: `first_journey` | None | First session only, before level gameplay; experiment exposure trigger when eligible. |
| `tutorial_completed` | `tutorial_id`: `first_journey` | None | After tutorial start, before level gameplay. |
| `level_retry` | `level_id`: positive integer | `attempt_id` | New attempt immediately follows a failed attempt on the same level, possibly in a later session. Emitted before its `level_start`. |
| `level_start` | `level_id`: positive integer | `attempt_id` | At the attempt's start. |
| `level_complete` | `level_id`: positive integer; `stars`: integer 1–3 | `attempt_id` | At the end of a completed attempt. |
| `level_failed` | `level_id`: positive integer; `reason`: `health_depleted` | `attempt_id` | At the end of a failed attempt. |
| `player_died` | `cause`: `enemy` | `attempt_id` | Immediately before `level_failed`, at the same timestamp. |
| `reward_claimed` | `reward_type`: `coins`; `quantity`: positive integer | `attempt_id` | After completion, at the same timestamp; can be lost. Coins are not real-money revenue. |
| `shop_opened` | `entry_point`: `session_summary` | None | Shop visit after level gameplay; may not lead to a transaction. |
| `purchase_started` | `item_id`: positive integer | `purchase_id` | At transaction initiation, following a shop visit. |
| `purchase_completed` | `item_id`: positive integer | `purchase_id` | At successful resolution only. Pending and failed transactions have no completion event. |

All attempt events require `attempt_id` and null `purchase_id`. Purchase events require `purchase_id` and null `attempt_id`. Other events have both references null. IDs refer to objects in the same session. JSON numeric identifiers are integers, never strings or booleans. Payload validation is implemented in `src/arcadia/common/events.py`; cross-record assertions live in `database/validation/integrity.sql`.

Within a normal session, tutorial events (first session only) precede attempts, then an optional shop visit and transaction, then session end. Failed attempts have death/failure events; completed attempts have completion/reward events; abandoned attempts have only their start and optional retry. No success/failure event is emitted for an abandoned attempt. Several events can share a timestamp but always have distinct source sequences.

Authoritative purchase statuses include unsuccessful and unresolved attempts. Telemetry alone cannot classify all missing purchase completions without consulting the transaction table. See [data quality](data-quality.md) for event loss, late receipt, and observation-window semantics.
