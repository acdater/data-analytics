# Reference seeds

`arcadia.generator.catalog` generates the level, release, item, campaign, experiment, and exchange-rate catalogs deterministically. They load through the same transactional COPY path as operational records. There are no raw data files or separate manual SQL seeds to synchronize. Run `make seed` from the project root.
