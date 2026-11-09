from collections import defaultdict
from dataclasses import replace
from hashlib import sha256
import copy
import pytest
from arcadia.common.config import load_config
from arcadia.common.events import validate_event
from arcadia.generator.simulate import generate
from arcadia.generator import scenarios
from arcadia.ingestion.load import canonical

@pytest.fixture(scope="module")
def sample():
    tables = defaultdict(list)
    for table, row in generate(replace(load_config(), players=80)):
        tables[table].append(row)
    return tables


def fingerprint(config):
    digest = sha256()
    for table, row in generate(config):
        digest.update(canonical(table, row))
    return digest.hexdigest()


def test_deterministic_and_seed_sensitive():
    config = replace(load_config(), players=8)
    assert fingerprint(config) == fingerprint(config)
    assert fingerprint(config) != fingerprint(replace(config, seed=config.seed+1))


def test_authoritative_state_independent_of_telemetry_quality(monkeypatch):
    config = replace(load_config(), players=8)
    before = [(t, r) for t, r in generate(config) if t != "events"]
    monkeypatch.setattr(scenarios, "END_LOSS_RATE", 1)
    monkeypatch.setattr(scenarios, "REWARD_LOSS_RATE", 1)
    monkeypatch.setattr(scenarios, "LATE_RATE", 1)
    after = [(t, r) for t, r in generate(config) if t != "events"]
    assert before == after


def test_player_histories_and_event_sequences(sample):
    players = {r["player_id"]: r for r in sample["players"]}
    sessions = {r["session_id"]: r for r in sample["sessions"]}
    attempts = {r["attempt_id"]: r for r in sample["level_attempts"]}
    previous_session = {}
    previous_event = {}
    event_ids = set()
    for session in sessions.values():
        pid = session["player_id"]
        assert session["started_at"] >= players[pid]["registered_at"]
        assert session["ended_at"] > session["started_at"]
        assert session["started_at"] >= previous_session.get(pid, players[pid]["registered_at"])
        previous_session[pid] = session["ended_at"]
    level = defaultdict(lambda: 1)
    for attempt in attempts.values():
        session = sessions[attempt["session_id"]]
        pid = session["player_id"]
        assert session["started_at"] <= attempt["started_at"] < attempt["ended_at"] <= session["ended_at"]
        assert attempt["level_id"] == level[pid]
        if attempt["outcome"] == "completed":
            level[pid] = min(100, level[pid]+1)
        if attempt["outcome"] == "abandoned":
            assert session["status"] == "interrupted"
    for event in sample["events"]:
        validate_event(event)
        session = sessions[event["session_id"]]
        assert event["event_id"] not in event_ids
        event_ids.add(event["event_id"])
        assert session["started_at"] <= event["event_timestamp"] <= session["ended_at"]
        prior = previous_event.get(event["session_id"])
        if prior:
            assert event["event_sequence"] > prior["event_sequence"]
            assert event["event_timestamp"] >= prior["event_timestamp"]
        previous_event[event["session_id"]] = event
        if event["event_type"] == "session_end":
            assert session["status"] == "completed"


def test_experiment_assignment_precedes_exposure(sample):
    assignments = {a["player_id"]: a for a in sample["experiment_assignments"]}
    sessions = {r["session_id"]: r for r in sample["sessions"]}
    for exposure in sample["experiment_exposures"]:
        assert assignments[exposure["player_id"]]["assigned_at"] < exposure["exposed_at"]
        assert sessions[exposure["session_id"]]["session_number"] == 1
    assert {a["variant"] for a in assignments.values()} == {"control", "treatment"}


def test_currency_normalization(sample):
    from arcadia.generator.catalog import money
    rates = {(r["rate_date"], r["currency"]): r["usd_per_unit"] for r in sample["exchange_rates"]}
    for purchase in sample["purchases"]:
        expected = money(purchase["amount"]*rates[(purchase["rate_date"], purchase["currency"])]) if purchase["status"] == "completed" else 0
        assert purchase["revenue_usd"] == expected


def test_payload_contract_rejects_bad_properties(sample):
    event = copy.deepcopy(sample["events"][0])
    event["properties"]["schema_version"] = True
    with pytest.raises(ValueError):
        validate_event(event)
    event["properties"] = {"schema_version": 1}
    with pytest.raises(ValueError):
        validate_event(event)


def test_controlled_imperfections_and_behavioral_diversity(sample):
    sessions = sample["sessions"]
    events = sample["events"]
    ends = {e["session_id"] for e in events if e["event_type"] == "session_end"}
    assert any(s["status"] == "interrupted" for s in sessions)
    assert any(s["status"] == "completed" and s["session_id"] not in ends for s in sessions)
    assert any((e["received_at"]-e["event_timestamp"]).total_seconds() > 3600 for e in events)
    assert any(p["country"] is None for p in sample["players"])
    assert any(s["session_number"] > 20 for s in sessions)
    assert {a["outcome"] for a in sample["level_attempts"]} == {"completed", "failed", "abandoned"}
    assert len({p["player_id"] for p in sample["purchases"]}) < len(sample["players"])/2


def test_config_rejects_invalid_inputs():
    with pytest.raises(ValueError):
        replace(load_config(), players=0)
    with pytest.raises(ValueError):
        replace(load_config(), start=load_config().start.replace(tzinfo=None))
