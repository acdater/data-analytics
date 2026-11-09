# Analytics backlog

Choose your own definitions and methods. Each deliverable should state its grain, time basis, exclusions, uncertainty, and limitations. These are questions, not prescribed conclusions.

| Domain | Difficulty | Business question | Expected deliverable |
| --- | --- | --- | --- |
| Discovery | Introductory | What does each source represent, and which joins preserve its grain? | Source map and join-risk notes. |
| Data quality | Introductory | Where are attribution or telemetry fields unavailable? | Quality audit with operational impact. |
| Engagement | Introductory | How does activity vary across the calendar and platforms? | Metric definitions and exploratory charts. |
| Progression | Intermediate | Where do players encounter progression friction? | Progression investigation and competing explanations. |
| Retention | Intermediate | How do cohort outcomes vary with available follow-up time? | Cohort definitions, censoring policy, and visualizations. |
| Lifecycle | Intermediate | How should inactivity, churn, and return be defined for this game? | Alternative definitions and sensitivity assessment. |
| Acquisition | Intermediate | How do channel outcomes compare after considering cohort mix and missing attribution? | Channel comparison with limitations. |
| Monetization | Intermediate | How is successful revenue distributed across players, items, and time? | Revenue definitions and a monetization report. |
| Currency | Intermediate | How does currency handling affect comparisons? | Reconciliation and exchange-rate assumptions. |
| Telemetry | Advanced | How would receipt-time versus event-time reporting differ? | Late-arrival assessment and update policy. |
| Reliability | Advanced | How should incomplete session telemetry be interpreted alongside authoritative state? | Reconciliation and measurement-risk assessment. |
| Releases | Advanced | Are differences around releases consistent with product changes or changing player composition? | Observational study design and caveats. |
| Experiments | Advanced | Was assignment implemented consistently, and which population should be analyzed? | Experiment validity audit and estimand specification. |
| Experiments | Advanced | What evidence would justify shipping or rejecting a treatment? | Hypotheses, guardrails, uncertainty estimates, and decision criteria. |
| Statistics | Advanced | How sensitive are conclusions to distributional assumptions and multiple comparisons? | Statistical methodology note and robustness checks. |
| Engineering | Advanced | How should operational records become reusable dimensional datasets? | Proposed model grains, keys, lineage, and tests. |
| Communication | Advanced | What should product leadership monitor and investigate next? | Your Tableau dashboard and decision memo. |

The SQL, notebook, Tableau, dbt, and report directories are intentionally empty apart from workspace instructions. Do not treat synthetic scenario parameters as evidence for your own findings.
