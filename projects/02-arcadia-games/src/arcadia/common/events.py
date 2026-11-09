"""Public telemetry contract, shared by generator tests and database validation."""
EVENT_FIELDS = {
    "session_start": {"network_type": (str, type(None))},
    "session_end": {"reason": str},
    "level_start": {"level_id": int}, "level_complete": {"level_id": int, "stars": int},
    "level_failed": {"level_id": int, "reason": str}, "player_died": {"cause": str},
    "level_retry": {"level_id": int}, "reward_claimed": {"reward_type": str, "quantity": int},
    "shop_opened": {"entry_point": str}, "purchase_started": {"item_id": int},
    "purchase_completed": {"item_id": int}, "tutorial_started": {"tutorial_id": str},
    "tutorial_completed": {"tutorial_id": str},
}
ATTEMPT_EVENTS = {"level_start", "level_complete", "level_failed", "player_died", "level_retry", "reward_claimed"}
PURCHASE_EVENTS = {"purchase_started", "purchase_completed"}


def validate_event(row):
    kind, props = row["event_type"], row["properties"]
    if kind not in EVENT_FIELDS or not isinstance(props, dict):
        raise ValueError("Unknown event or non-object payload")
    required = {"schema_version": int, **EVENT_FIELDS[kind]}
    if props.keys() != required.keys() or props["schema_version"] != 1:
        raise ValueError("Incorrect payload keys or schema version")
    for key, expected in required.items():
        if not isinstance(props[key], expected) or isinstance(props[key], bool):
            raise ValueError(f"Incorrect type for {kind}.{key}")
    if (row["attempt_id"] is not None) != (kind in ATTEMPT_EVENTS):
        raise ValueError("Incorrect attempt reference")
    if (row["purchase_id"] is not None) != (kind in PURCHASE_EVENTS):
        raise ValueError("Incorrect purchase reference")
    if row["received_at"] < row["event_timestamp"]:
        raise ValueError("Receipt precedes event")
    allowed = {"network_type": {None,"wifi","cellular"}, "stars": {1,2,3}, "cause": {"enemy"},
               "reward_type": {"coins"}, "entry_point": {"session_summary"}, "tutorial_id": {"first_journey"}}
    for key, options in allowed.items():
        if key in props and props[key] not in options:
            raise ValueError(f"Invalid {key}")
    for key in ("quantity", "level_id", "item_id"):
        if key in props and props[key] <= 0:
            raise ValueError(f"Nonpositive {key}")
    if "reason" in props and props["reason"] != ("normal" if kind == "session_end" else "health_depleted"):
        raise ValueError("Invalid reason")
