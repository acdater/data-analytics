"""All test writes roll back. Opt in against the dedicated Arcadia database only."""
from dataclasses import replace
import os
import psycopg
import pytest
from arcadia.common.config import load_config, ROOT
from arcadia.common.db import engine
from arcadia.generator.simulate import generate
from arcadia.ingestion.load import load
from arcadia.ingestion.validate import validate

pytestmark = [pytest.mark.integration, pytest.mark.skipif(os.getenv("ARCADIA_TEST_DATABASE") != "1", reason="Integration opt-in required")]

@pytest.fixture
def connection():
    db = engine()
    raw = db.raw_connection()
    conn = raw.driver_connection
    conn.execute((ROOT / "database/schema/001_schema.sql").read_text())
    yield conn
    conn.rollback()
    raw.close()
    db.dispose()


def test_copy_batch_independence_and_integrity(connection):
    config = replace(load_config(), players=12)
    first = load(connection, config, generate(config), batch_size=1, replace=True)
    assert validate(connection, check_ranges=False)["passed"]
    # Database row digests detect ingestion differences, in addition to the source checksum.
    before = connection.execute("SELECT md5(string_agg(row_to_json(e)::text, '' ORDER BY event_id)) FROM events e").fetchone()[0]
    second = load(connection, config, generate(config), batch_size=731, replace=True)
    after = connection.execute("SELECT md5(string_agg(row_to_json(e)::text, '' ORDER BY event_id)) FROM events e").fetchone()[0]
    assert first["content_sha256"] == second["content_sha256"]
    assert first["row_counts"] == second["row_counts"]
    assert before == after
    assert second["max_buffered_rows"] <= 731
    assert validate(connection, check_ranges=False)["passed"]


def test_constraints_and_validator_detect_corruption(connection):
    config = replace(load_config(), players=12)
    load(connection, config, generate(config), replace=True)
    for query in ("INSERT INTO players SELECT * FROM players LIMIT 1",
                  "UPDATE sessions SET player_id=-1 WHERE session_id=(SELECT min(session_id) FROM sessions)",
                  "UPDATE sessions SET duration_seconds=-1 WHERE session_id=(SELECT min(session_id) FROM sessions)",
                  "UPDATE purchases SET amount=-1 WHERE purchase_id=(SELECT min(purchase_id) FROM purchases)"):
        with pytest.raises(psycopg.IntegrityError):
            with connection.transaction():
                connection.execute(query)
    connection.execute("UPDATE events SET properties='{}'::jsonb WHERE event_id=(SELECT min(event_id) FROM events)")
    assert validate(connection, check_ranges=False)["checks"]["event_payloads"] == 1


def test_interrupted_replacement_preserves_previous_dataset(connection):
    config = replace(load_config(), players=4)
    initial = load(connection, config, generate(config), replace=True)
    def broken_stream():
        for i, row in enumerate(generate(config)):
            if i == 500:
                raise RuntimeError("Simulated interruption")
            yield row
    with pytest.raises(RuntimeError, match="interruption"):
        with connection.transaction():
            load(connection, config, broken_stream(), batch_size=23, replace=True)
    assert connection.execute("SELECT content_sha256 FROM generation_runs").fetchone()[0] == initial["content_sha256"]
    assert validate(connection, check_ranges=False)["passed"]
    with pytest.raises(ValueError, match="already contains data"):
        load(connection, config, generate(config))
