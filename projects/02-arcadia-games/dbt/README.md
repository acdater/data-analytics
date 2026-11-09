# Future dbt workspace

Reserved for learner-built dbt Core integration. No models, macros, sources, or analyses are implemented.

When ready, add a compatible `dbt-postgres` dependency group, initialize dbt here, and point a local environment-backed profile at the Arcadia connection in `.env`. Use source schema `arcadia` and a separate target schema such as `arcadia_analytics`. Keep secrets outside version control. Decide staging, intermediate, and mart grains and tests independently. Do not overwrite source tables.
