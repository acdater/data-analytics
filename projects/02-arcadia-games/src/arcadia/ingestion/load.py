from collections import Counter
from hashlib import sha256
import json
from psycopg import sql
from psycopg.types.json import Jsonb
from arcadia.common.config import VERSION
from arcadia.common.events import validate_event

# Parent-first flush order allows immediate FK checks even at a one-row batch size.
TABLES = ("campaigns", "campaign_daily_spend", "game_releases", "levels", "level_configurations", "items",
          "exchange_rates", "players", "experiments", "experiment_variants", "experiment_assignments",
          "sessions", "experiment_exposures", "level_attempts", "purchases", "events")


def canonical(table, row):
    return (json.dumps([table, row], default=str, sort_keys=True, separators=(",", ":"))+"\n").encode()


def load(connection, config, rows, batch_size=5000, replace=False):
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    # Caller owns a transaction; interruption rolls back all changes, including replacement.
    connection.execute("SELECT pg_advisory_xact_lock(20261109)")
    populated = any(connection.execute(sql.SQL("SELECT EXISTS (SELECT 1 FROM arcadia.{})").format(sql.Identifier(t))).fetchone()[0]
                    for t in (*TABLES, "generation_runs"))
    if populated and not replace:
        raise ValueError("Arcadia already contains data; use --replace to regenerate it atomically")
    if populated:
        connection.execute(sql.SQL("TRUNCATE {} ").format(sql.SQL(",").join(
            sql.Identifier("arcadia", t) for t in (*TABLES, "generation_runs"))))
    buffers = {table: [] for table in TABLES}
    counts = Counter()
    digest = sha256()
    buffered = 0
    max_buffered = 0

    def flush():
        for table in TABLES:
            chunk = buffers[table]
            if not chunk:
                continue
            columns = list(chunk[0])
            query = sql.SQL("COPY {} ({}) FROM STDIN").format(sql.Identifier("arcadia", table),
                     sql.SQL(",").join(map(sql.Identifier, columns)))
            with connection.cursor().copy(query) as copy:
                for row in chunk:
                    copy.write_row([Jsonb(row[key]) if isinstance(row[key], dict) else row[key] for key in columns])
            chunk.clear()

    for table, row in rows:
        if table == "events":
            validate_event(row)
        digest.update(canonical(table, row))
        buffers[table].append(row)
        counts[table] += 1
        buffered += 1
        max_buffered = max(max_buffered, buffered)
        if buffered >= batch_size:
            flush()
            buffered = 0
    flush()
    checksum = digest.hexdigest()
    connection.execute("""INSERT INTO arcadia.generation_runs VALUES (1,%s,%s,%s,%s,%s,%s,%s,%s)""",
                       (VERSION, config.profile, config.seed, config.players, config.start, config.end, checksum, Jsonb(dict(counts))))
    return dict(row_counts=dict(counts), content_sha256=checksum, max_buffered_rows=max_buffered)
