"""Streaming stateful simulation. No analytical metrics are persisted."""
from datetime import timedelta
from decimal import Decimal
import math
import numpy as np
from faker import Faker
from .catalog import money
from . import scenarios as s


def player_rows(config, catalog, player_id):
    rng = np.random.default_rng(np.random.SeedSequence([config.seed, player_id, 0]))
    telemetry = np.random.default_rng(np.random.SeedSequence([config.seed, player_id, 1]))
    assignment_rng = np.random.default_rng(np.random.SeedSequence([config.seed, player_id, 2]))
    fake = Faker("en_US")
    fake.seed_instance(config.seed + player_id)
    days = (config.end-config.start).days
    # Campaign and calendar jointly determine registration, using known spend only.
    channel = str(rng.choice(["organic", "paid_social", "paid_search", "creator"], p=[.35,.32,.20,.13]))
    campaign_id = {"paid_social": 1, "paid_search": 2, "creator": 3}.get(channel)
    day_weights = np.array([float(catalog["spend_lookup"][(campaign_id, config.start.date()+timedelta(days=d))])
                           if campaign_id else 1+.18*math.sin(d/50) for d in range(days)])
    day_weights /= day_weights.sum()
    registration_day = int(rng.choice(days, p=day_weights))
    registered = config.start + timedelta(days=registration_day, seconds=int(rng.integers(0, 86400-1800)))
    country = rng.choice(["US", "GB", "DE", "FR", "CA", None], p=[.37,.15,.14,.12,.19,.03])
    platform = str(rng.choice(["ios", "android"], p=[.44,.56]))
    yield "players", dict(player_id=player_id, display_name=fake.user_name(), registered_at=registered,
                          country=country, platform=platform, acquisition_channel=channel,
                          campaign_id=campaign_id if rng.random() > .025 else None)
    engagement = float(np.clip(rng.beta(2.5, 2) + s.CHANNEL_QUALITY[channel], .05, .95))
    skill = float(rng.beta(3, 2))
    payer = rng.random() < .09+.13*engagement
    heavy_payer = payer and rng.random() < .09
    experiment = catalog["experiments"][0]
    variant = None
    if experiment["starts_at"] <= registered < experiment["ends_at"]:
        variant = str(assignment_rng.choice(["control", "treatment"]))
        yield "experiment_assignments", dict(experiment_id=1, player_id=player_id, variant=variant, assigned_at=registered)
    level = 1
    previous_failed = False
    exposed = False
    start = registered + timedelta(seconds=int(rng.integers(15, 600)))
    release_adoption_delay = timedelta(days=int(rng.integers(0, 15)))
    for session_number in range(1, 401):
        if start + timedelta(minutes=12) >= config.end:
            break
        available = [r for r in catalog["game_releases"] if r["platform"] == platform and
                     r["released_at"] + (release_adoption_delay if r["version"] != "1.0.0" else timedelta()) <= start]
        release = available[-1]
        release_id = release["release_id"]
        interrupted = rng.random() < s.RELEASE_INTERRUPTION[release["version"]]
        attempt_count = int(rng.choice([2, 3], p=[.7, .3]))
        duration = 20 + 180*attempt_count + 90
        end = start + timedelta(seconds=duration)
        session_id = player_id*1000 + session_number
        yield "sessions", dict(session_id=session_id, player_id=player_id, session_number=session_number,
                               release_id=release_id, started_at=start, ended_at=end, duration_seconds=duration,
                               status="interrupted" if interrupted else "completed")
        sequence = 0

        def event(kind, at, attempt_id=None, purchase_id=None, **payload):
            nonlocal sequence
            sequence += 1
            # Omission creates sequence gaps, never renumbers retained events.
            if (kind == "session_end" and telemetry.random() < s.END_LOSS_RATE) or (
                kind == "reward_claimed" and telemetry.random() < s.REWARD_LOSS_RATE):
                return []
            delay = int(telemetry.integers(3600, 259201)) if telemetry.random() < s.LATE_RATE else int(telemetry.integers(0, 16))
            props = {"schema_version": 1, **payload}
            return [("events", dict(event_id=session_id*1000+sequence, session_id=session_id,
                     event_sequence=sequence, event_timestamp=at, received_at=at+timedelta(seconds=delay),
                     event_type=kind, attempt_id=attempt_id, purchase_id=purchase_id, properties=props))]

        yield from event("session_start", start, network_type=telemetry.choice(["wifi", "cellular", None], p=[.62,.35,.03]))
        if session_number == 1:
            tutorial_time = start+timedelta(seconds=2)
            if variant and tutorial_time < experiment["ends_at"]:
                exposed = True
                yield "experiment_exposures", dict(experiment_id=1, player_id=player_id, session_id=session_id, exposed_at=tutorial_time)
            yield from event("tutorial_started", tutorial_time, tutorial_id="first_journey")
            yield from event("tutorial_completed", start+timedelta(seconds=10), tutorial_id="first_journey")
        failures = 0
        for attempt_number in range(1, attempt_count+1):
            attempt_id = session_id*10+attempt_number
            attempt_start = start+timedelta(seconds=15+(attempt_number-1)*180)
            attempt_end = attempt_start+timedelta(seconds=int(rng.integers(50, 160)))
            difficulty = float(catalog["difficulty_lookup"][(level, release_id)])
            probability = float(np.clip(.83 + .22*(skill-.5) - .42*difficulty + .05*engagement, .12, .94))
            outcome = "completed" if rng.random() < probability else "failed"
            if interrupted and attempt_number == attempt_count:
                outcome = "abandoned"
                attempt_end = end
            yield "level_attempts", dict(attempt_id=attempt_id, session_id=session_id, release_id=release_id,
                        level_id=level, attempt_number=attempt_number, started_at=attempt_start, ended_at=attempt_end, outcome=outcome)
            if previous_failed:
                yield from event("level_retry", attempt_start, attempt_id=attempt_id, level_id=level)
            yield from event("level_start", attempt_start, attempt_id=attempt_id, level_id=level)
            if outcome == "completed":
                yield from event("level_complete", attempt_end, attempt_id=attempt_id, level_id=level, stars=int(rng.integers(1,4)))
                yield from event("reward_claimed", attempt_end, attempt_id=attempt_id, reward_type="coins", quantity=10+level)
                level = min(level+1, 100)
            elif outcome == "failed":
                yield from event("player_died", attempt_end, attempt_id=attempt_id, cause="enemy")
                yield from event("level_failed", attempt_end, attempt_id=attempt_id, level_id=level, reason="health_depleted")
                failures += 1
            previous_failed = outcome == "failed"
        # Interrupted sessions terminate during the final attempt and never enter the shop.
        if not interrupted and rng.random() < (.28+.18*engagement if payer else .025):
            shop_at = end-timedelta(seconds=50)
            yield from event("shop_opened", shop_at, entry_point="session_summary")
            if payer and rng.random() < (.85 if heavy_payer else .65):
                item = catalog["items"][int(rng.choice(5, p=[.12,.25,.45,.10,.08] if heavy_payer else [.50,.16,.02,.20,.12]))]
                currency = "GBP" if country == "GB" else "EUR" if country in ("DE", "FR") else "USD"
                initiated = end-timedelta(seconds=40)
                rate_date = initiated.date()
                rate = catalog["rate_lookup"][(rate_date, currency)]
                amount = money(item["base_price_usd"] / rate)
                status = str(rng.choice(["completed","failed","pending"], p=[.94,.05,.01]))
                resolved = initiated+timedelta(seconds=5) if status != "pending" else None
                yield "purchases", dict(purchase_id=session_id, session_id=session_id, player_id=player_id,
                            item_id=item["item_id"], initiated_at=initiated, resolved_at=resolved, status=status,
                            currency=currency, rate_date=rate_date, amount=amount,
                            revenue_usd=money(amount*rate) if status == "completed" else Decimal("0.00"))
                yield from event("purchase_started", initiated, purchase_id=session_id, item_id=item["item_id"])
                if status == "completed":
                    yield from event("purchase_completed", resolved, purchase_id=session_id, item_id=item["item_id"])
        if not interrupted:
            yield from event("session_end", end, reason="normal")
        hazard = (s.EARLY_EXIT_BASE+.19*(1-engagement)) if session_number <= 3 else (s.ESTABLISHED_EXIT_BASE+.032*(1-engagement))
        hazard += .009*failures + (.035 if interrupted else 0)
        if exposed and variant == "treatment" and session_number <= 3:
            hazard -= s.TUTORIAL_EFFECT
        if rng.random() < hazard:
            break
        # Time gaps depend on persistent engagement; weekend and evening activity vary.
        if rng.random() < .15*engagement:
            start = end+timedelta(hours=int(rng.integers(2, 7)))
        else:
            gaps = np.arange(1, 15)
            weights = np.exp(-gaps/(1.2+3*(1-engagement)))
            weights *= np.array([1.25 if (end+timedelta(days=int(g))).weekday() >= 5 else 1 for g in gaps])
            gap = int(rng.choice(gaps, p=weights/weights.sum()))
            hours = np.arange(24)
            hour_weights = np.exp(-((hours-19)/4)**2)+.20
            hour = int(rng.choice(hours, p=hour_weights/hour_weights.sum()))
            start = (end+timedelta(days=gap)).replace(hour=hour, minute=int(rng.integers(0,60)), second=int(rng.integers(0,60)))


def prepare_catalog(catalog):
    return {**catalog,
            "rate_lookup": {(r["rate_date"], r["currency"]): r["usd_per_unit"] for r in catalog["exchange_rates"]},
            "difficulty_lookup": {(r["level_id"], r["release_id"]): r["difficulty"] for r in catalog["level_configurations"]},
            "spend_lookup": {(r["campaign_id"], r["spend_date"]): r["spend_usd"] for r in catalog["campaign_daily_spend"]}}


def generate(config):
    from .catalog import catalogs
    catalog = catalogs(config)
    for table, rows in catalog.items():
        for row in rows:
            yield table, row
    prepared = prepare_catalog(catalog)
    for player_id in range(1, config.players+1):
        yield from player_rows(config, prepared, player_id)
