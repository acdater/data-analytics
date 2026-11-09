# Maintainer-only generation design — spoilers

This file and `src/arcadia/generator/scenarios.py` expose ground truth. They are not required learning materials.

The simulation uses independent NumPy streams keyed by `(seed, player_id, purpose)` for behavior, telemetry, and assignment. Faker gets a per-player seed. Catalogs are deterministic functions of the observation window. Player state contains engagement, skill, payer propensity, current unlocked level, prior attempt outcome, release-adoption delay, and past exposure. These are simulation internals, not stored lifecycle metrics. Churn is a stochastic stop decision after a session; the dataset does not label churn or last seen.

Acquisition channel selects a daily registration distribution weighted by that campaign's synthetic spend. Organic volume has its own smooth calendar pattern. Channel quality slightly shifts an overlapping engagement distribution. Repeated activity depends on engagement, weekend weighting, evening preferences, and probabilistic continuation. Early-session exit probability exceeds the established-player baseline. End-of-window truncation limits observable follow-up.

Embedded scenarios: a modest channel-quality difference; early-life attrition; a level-12 difficulty increase partly revised in version 1.3.0; a version-1.2.0 interruption increase; heterogeneous purchase propensity and a small high-spend segment; a small early continuation effect from the first-journey treatment. These are intended causal knobs inside the synthetic system, not precomputed empirical findings. Realized effects remain noisy and must not be presented as business conclusions. Model relationships are simplified and do not establish external validity.

Eligibility is new registration during the experiment window. Allocation is independent of the behavior RNG and fixed at registration. First exposure is the first tutorial start while enrollment is open. Only exposed treatment players receive a change to their subsequent early exit probability. Assignment does not use future activity, purchases, or survival. Analysis choices such as intention-to-treat versus exposure conditioning remain the learner's responsibility.

Each session has two or three sequential attempts. A success advances one level; a failure or abandonment retains the level. The terminal level permits replay. An interruption abandons the final attempt. Purchases occur only after gameplay in completed sessions and are more likely for persistent payer profiles; heavy payers also choose higher-priced items. Country maps to a supported currency, but rates and prices are synthetic.

Telemetry loss applies only to selected session-end and reward events. Delivery lag and network metadata use the separate telemetry stream. Loss never alters authoritative gameplay or financial state. IDs encode player/session/action identity and remain independent of ingestion buffering. Generation traversal is player-major, not global time order.

The loader flushes a total-row budget in dependency order using COPY. Parents precede children in the stream, so immediate FK checks work even at batch size one. One transaction provides atomic replacement; a transaction-scoped advisory lock serializes generator runs. Large database transactions require sufficient disk/WAL and can hold locks for the load duration. No client-side all-player state, full event DataFrame, or generated raw data file is retained.

Scalability is architectural and tested through bounded-buffer assertions; the full portfolio dataset is intentionally not generated in this implementation pass. Do not claim measured 50,000-player performance. Row-count bounds are development smoke checks and portfolio targets, not guaranteed totals for arbitrary seeds.
