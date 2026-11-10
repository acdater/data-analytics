# Generator 1.1.0: behavior and timing assumptions

Maintainer documentation, including generation ground truth. These are illustrative design assumptions for a fictional game, not fitted estimates from real mobile-game telemetry. Numerical parameters and QA tolerances live in `config/behavior.toml`.

## What changed

Version 1.0.0 fixed every session to two or three attempts and consequently to 470 or 650 seconds. Version 1.1.0 draws a continuous, truncated log-normal **intended play budget**, schedules sequential actions, and derives the actual authoritative session end from the last action. Seconds are integer-quantized to match the existing schema. No completed row is assigned an independent random duration.

The base play-budget median is 280 seconds with log-scale sigma 0.75. Persistent engagement scales the median smoothly; progression adds a modest experience effect, and a first-session multiplier of 0.75 allows shorter newcomer play. Prior-session failure fraction reduces the next intended budget modestly. Within-player random variation is large, so casual players can have long sessions and highly engaged players can have short ones.

The play-budget lower bounds are 50 seconds for returning sessions and 100 seconds for first sessions. The upper bound reserves room beneath a one-hour total-session limit for browsing, checkout, and exit. Bounds use rejection sampling, not clipping; this avoids accumulating values at a maximum. Interrupted sessions can be much shorter than the intended budget. First-time players finish onboarding before the combat-interruption mechanism becomes active.

Login, tutorial, combat, between-attempt menus, browsing, checkout, and exit each have their own variable duration. Combat uses a log-normal distribution with baseline median 90 seconds and sigma 0.38, modified by difficulty, skill, and outcome; attempts are bounded by the catalog time limit. A subsequent attempt is launched only if its sampled duration fits the remaining budget. A first attempt may overrun a short intention, so short sessions still contain coherent gameplay. Attempt duration is never compressed to fill a leftover time slot. The total maximum remains below one hour, including these first-attempt overruns.

Attempts are scheduled until the budget or a stochastic exit decision ends play. Success unlocks only one subsequent level; failures and abandonment preserve the level. Repeated failures can cause early voluntary exit, affect later time budgets, and modestly lengthen return gaps. Continuation hazard now uses failure **fraction**, so simply having more attempts does not mechanically create excessive churn. Stars use a noisy skill/difficulty-dependent draw instead of a uniform distribution. Each player still shares one persistent engagement factor across duration, frequency, continuation, and purchase propensity.

Same-day return intervals now have continuous log-normal variation rather than whole-hour offsets. Across-day returns retain weekday and hour-of-day seasonality, with a longer possible absence tail. Registration timing, attribution, catalog prices, and campaign models remain unchanged in this revision. Country and platform are categorical assumptions, not targets for this duration fix.

## Interruptions and monetization

A release-specific exponential clock measures **active combat seconds** to interruption. At the sampled interruption, the current attempt becomes abandoned, the authoritative session ends, and no shop or session-end event follows. Longer combat exposure creates more opportunity for interruption; there is no independent fixed-duration interrupted template. This version models combat interruptions, not background disconnections during menus or tutorial abandonment.

Normal exit and telemetry loss are separate mechanisms. A completed session may still lack its end event; telemetry delivery/loss has a separate RNG and cannot change authoritative actions. Receipt timestamps may remain delayed beyond the session or observation window.

Shop probability depends on the same engagement/payer profile and accumulated play time, with a saturating time factor. Shops remain post-gameplay in this schema's `session_summary` flow. Browsing, payment initiation, resolution, and exit have individually sampled delays. Transactions are no longer pinned to session-end minus 40 seconds with a universal five-second checkout. One purchase attempt per session remains an intentional scope limit. Revenue status, currency conversion, and pending semantics are unchanged.

The player history uses only prior state when sampling the next session. Assignment remains independently randomized at registration, before tutorial exposure, and treatment affects later early continuation only. No future duration, survival, or purchase outcome is used for eligibility.

## Quality thresholds and interpretation

| Check | Configured acceptance | Rationale |
| --- | --- | --- |
| Distinct durations | At least 300 | Detects templates with a few values in a population of at least 1,000 sessions; permits integer seconds. |
| Coefficient of variation | 0.45–1.6 | Allows broad within-player variation while rejecting near-constant or overwhelmingly extreme sessions. |
| Mean / median | At least 1.12 | Requires an appreciable right tail rather than merely adding symmetric jitter. |
| P90 / median | At least 1.8 | Independently checks upper-tail spread. |
| P99 / maximum | At most 3,300 / 3,600 seconds | Keeps the upper tail plausible under the one-hour design cap. |
| Most common duration | At most 3% | Detects clipping pileups or prominent fixed templates. |
| Short / long presence | At least 3% ≤180 seconds; at least 2% ≥900 seconds | Requires varied usage occasions without prescribed mixture clusters. |
| Returning / first median | 1.05–3.5 | Broad sanity band for the intended newcomer tendency; requires 250 observations per group. Returning means session number ≥5. |
| Attempt variation | At least 6 distinct per-session counts and 80 duration values | Rejects fixed-count schedules and duration templates. |
| Checkout variation | At least 12 distinct delays in ≥50 resolved purchases | Rejects universal fixed payment delays. |

These thresholds are versioned acceptance criteria, not empirical business benchmarks. They are not significance tests and should be recalibrated deliberately when design assumptions change. Small samples explicitly skip population or segment checks. Observed first/returning differences include both progression and survival selection; a separate controlled timing test checks the engagement mechanism with matched history. Its configurable 20% relative tolerance around the untruncated log-normal median ratio allows truncation and finite-sample variation. Tests also deliberately inject the old two-duration pattern, constant durations, and a uniform distribution to ensure the checks fail.

A fixed seed reproduces all draws within this version. Changing the behavior model necessarily changes histories and checksums. Stable IDs remain independent of batch size; attempt IDs now use `session_id * 1000 + attempt_number` to accommodate variable attempt counts. The schema is unchanged. One-session planning and bounded quality histograms preserve streaming memory use.

Only sessions starting with sufficient room for the configured maximum duration are simulated near the observation cutoff. This avoids clipping or extending sessions beyond the window; a late registration can have no observed session. The final hour is consequently not representative for session-start analysis. Portfolio row-count targets are still provisional under the revised model; the full portfolio profile has not been generated.
