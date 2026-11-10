import re
from psycopg import sql
from arcadia.common.config import ROOT, load_config
from arcadia.common.events import validate_event
from .load import TABLES
from arcadia.generator.quality import validate_distributions


def validate(connection, check_ranges=True):
    checks = {}
    source = (ROOT / "database/validation/integrity.sql").read_text()
    for name, query in re.findall(r"-- check: (\w+)\n(.*?);", source, re.S):
        checks[name] = connection.execute(query).fetchone()[0]
    counts = {table: connection.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier("arcadia", table))).fetchone()[0]
              for table in TABLES}
    run = connection.execute("SELECT profile, player_count, row_counts FROM generation_runs WHERE run_id=1").fetchone()
    checks["manifest_present"] = int(run is None)
    if run:
        profile, player_count, expected = run
        checks["manifest_counts"] = sum(counts[t] != expected.get(t, 0) for t in TABLES)
        checks["player_count"] = int(counts["players"] != player_count)
        if check_ranges:
            config = load_config(profile)
            for table, stem in (("sessions", "sessions"), ("events", "events"), ("level_attempts", "attempts"), ("purchases", "purchases")):
                low, high = config.ranges[f"{stem}_per_player_range"]
                checks[f"range_{table}"] = int(not low*player_count <= counts[table] <= high*player_count)
    checks["event_payloads"] = 0
    # Server-side cursor keeps validation memory bounded too.
    with connection.cursor(name="arcadia_payload_validation") as cursor:
        cursor.execute("SELECT event_type, properties, attempt_id, purchase_id, event_timestamp, received_at FROM events")
        for values in cursor:
            row = dict(zip(("event_type", "properties", "attempt_id", "purchase_id", "event_timestamp", "received_at"), values))
            try:
                validate_event(row)
            except ValueError:
                checks["event_payloads"] += 1
    # PK/UNIQUE/FK constraints are active on COPY; check no constraint was left unvalidated.
    checks["unvalidated_constraints"] = connection.execute("""SELECT count(*) FROM pg_constraint c
        JOIN pg_namespace n ON n.oid=c.connamespace WHERE n.nspname='arcadia' AND NOT c.convalidated""").fetchone()[0]
    distribution_quality = validate_distributions(connection)
    return {"row_counts": counts, "checks": checks, "distribution_quality": distribution_quality,
            "passed": all(value == 0 for value in checks.values()) and distribution_quality["passed"] is not False}
