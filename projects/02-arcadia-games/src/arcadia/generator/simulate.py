"""Streaming stateful simulation. No analytical metrics are persisted."""
from datetime import timedelta
from decimal import Decimal
import math
import numpy as np
from faker import Faker
from .catalog import money
from . import scenarios as s
from .timing import behavior_config, log_seconds, play_budget


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
    timing = behavior_config()["timing"]
    previous_failure_fraction = 0.0
    for session_number in range(1, 401):
        # Do not force a short session against the administrative observation cutoff.
        if start + timedelta(seconds=timing["maximum_session_seconds"]) >= config.end:
            break
        available = [r for r in catalog["game_releases"] if r["platform"] == platform and
                     r["released_at"] + (release_adoption_delay if r["version"] != "1.0.0" else timedelta()) <= start]
        release = available[-1]
        release_id = release["release_id"]
        session_id = player_id*1000 + session_number
        budget = play_budget(rng, engagement, level, session_number, previous_failure_fraction)
        # Build only this session before emitting its authoritative end. This bounds
        # memory independently of the number of players and preserves parent-first COPY.
        actions, attempts = [], []
        purchase = None
        exposure = None

        def action(kind, offset, attempt_id=None, purchase_id=None, **payload):
            actions.append((kind, start+timedelta(seconds=offset), attempt_id, purchase_id, payload))

        action("session_start", 0)
        cursor = log_seconds(rng, timing["login_median_seconds"], .55, 2, 15)
        if session_number == 1:
            tutorial_time = start+timedelta(seconds=cursor)
            if variant and tutorial_time < experiment["ends_at"]:
                exposed = True
                exposure = dict(experiment_id=1, player_id=player_id, session_id=session_id, exposed_at=tutorial_time)
            action("tutorial_started", cursor, tutorial_id="first_journey")
            cursor += log_seconds(rng, timing["tutorial_median_seconds"], .4, 12, 45)
            action("tutorial_completed", cursor, tutorial_id="first_journey")
        failures = 0
        interrupted = False
        interruption_rate = -math.log1p(-s.RELEASE_INTERRUPTION[release["version"]]) / timing["interruption_reference_seconds"]
        # The interruption clock runs during active combat (renderer/app exit).
        combat_until_interruption = float(rng.exponential(1 / interruption_rate))
        while cursor + timing["attempt_minimum_seconds"] < budget:
            attempt_number = len(attempts)+1
            # Reserve enough ID space for variable-length sessions; no schema change.
            attempt_id = session_id*1000+attempt_number
            difficulty = float(catalog["difficulty_lookup"][(level, release_id)])
            probability = float(np.clip(.83 + .22*(skill-.5) - .42*difficulty + .05*engagement, .12, .94))
            outcome = "completed" if rng.random() < probability else "failed"
            median = timing["attempt_median_seconds"] * (1+.3*difficulty) * (1-.18*skill)
            if outcome == "failed":
                median *= .85
            upper = catalog["time_limit_lookup"][(level, release_id)]
            attempt_seconds = log_seconds(rng, median, timing["attempt_log_sigma"], timing["attempt_minimum_seconds"], upper)
            # Do not squeeze a whole level into the last few seconds of a budget.
            # A first attempt can overrun a short intention; later attempts must fit.
            if attempts and cursor + attempt_seconds > budget:
                break
            if combat_until_interruption < attempt_seconds:
                attempt_seconds = max(1, int(math.ceil(combat_until_interruption)))
                outcome = "abandoned"
                interrupted = True
            combat_until_interruption -= attempt_seconds
            attempts.append(dict(attempt_id=attempt_id, session_id=session_id, release_id=release_id,
                        level_id=level, attempt_number=attempt_number, started_at=start+timedelta(seconds=cursor),
                        ended_at=start+timedelta(seconds=cursor+attempt_seconds), outcome=outcome))
            if previous_failed:
                action("level_retry", cursor, attempt_id=attempt_id, level_id=level)
            action("level_start", cursor, attempt_id=attempt_id, level_id=level)
            cursor += attempt_seconds
            if outcome == "completed":
                star_quality = float(np.clip(.25+.5*skill-.12*difficulty, .1, .8))
                stars = 1 + int(rng.binomial(2, star_quality))
                action("level_complete", cursor, attempt_id=attempt_id, level_id=level, stars=stars)
                action("reward_claimed", cursor, attempt_id=attempt_id, reward_type="coins", quantity=10+level)
                level = min(level+1, 100)
            elif outcome == "failed":
                action("player_died", cursor, attempt_id=attempt_id, cause="enemy")
                action("level_failed", cursor, attempt_id=attempt_id, level_id=level, reason="health_depleted")
                failures += 1
            previous_failed = outcome == "failed"
            if interrupted:
                break
            # Repeated failure can end play early; it does not deterministically force exit.
            if failures > 1 and rng.random() < .10*(1-engagement):
                break
            menu_seconds = log_seconds(rng, timing["menu_median_seconds"]*(1+.15*failures), .6, 3, 90)
            if cursor + menu_seconds + timing["attempt_minimum_seconds"] >= budget:
                break
            cursor += menu_seconds
        if not attempts:
            raise ValueError("Timing configuration leaves no room for gameplay")
        # Shop visits remain after gameplay, but dwell/checkout/exit are separate
        # variable actions rather than fixed offsets from an invented session end.
        shop_probability = (.28+.18*engagement if payer else .025) * min(1.25, .65+cursor/600)
        if not interrupted and rng.random() < shop_probability:
            action("shop_opened", cursor, entry_point="session_summary")
            cursor += log_seconds(rng, 35, .65, 8, timing["browse_maximum_seconds"])
            if payer and rng.random() < (.85 if heavy_payer else .65):
                item = catalog["items"][int(rng.choice(5, p=[.12,.25,.45,.10,.08] if heavy_payer else [.50,.16,.02,.20,.12]))]
                currency = "GBP" if country == "GB" else "EUR" if country in ("DE", "FR") else "USD"
                initiated = start+timedelta(seconds=cursor)
                rate_date = initiated.date()
                rate = catalog["rate_lookup"][(rate_date, currency)]
                amount = money(item["base_price_usd"] / rate)
                status = str(rng.choice(["completed","failed","pending"], p=[.94,.05,.01]))
                action("purchase_started", cursor, purchase_id=session_id, item_id=item["item_id"])
                cursor += log_seconds(rng, 10, .65, 3, timing["checkout_maximum_seconds"])
                resolved = start+timedelta(seconds=cursor) if status != "pending" else None
                purchase = dict(purchase_id=session_id, session_id=session_id, player_id=player_id,
                            item_id=item["item_id"], initiated_at=initiated, resolved_at=resolved, status=status,
                            currency=currency, rate_date=rate_date, amount=amount,
                            revenue_usd=money(amount*rate) if status == "completed" else Decimal("0.00"))
                if status == "completed":
                    action("purchase_completed", cursor, purchase_id=session_id, item_id=item["item_id"])
        if not interrupted:
            cursor += log_seconds(rng, 12, .6, 3, timing["exit_maximum_seconds"])
            action("session_end", cursor, reason="normal")
        duration = cursor
        end = start+timedelta(seconds=duration)
        yield "sessions", dict(session_id=session_id, player_id=player_id, session_number=session_number,
                               release_id=release_id, started_at=start, ended_at=end, duration_seconds=duration,
                               status="interrupted" if interrupted else "completed")
        if exposure:
            yield "experiment_exposures", exposure
        for attempt in attempts:
            yield "level_attempts", attempt
        if purchase:
            yield "purchases", purchase
        if len(actions) >= 1000:
            raise ValueError("Session exceeds stable event ID capacity")
        for sequence, (kind, at, attempt_id, purchase_id, payload) in enumerate(actions, 1):
            if kind == "session_start":
                payload = {"network_type": telemetry.choice(["wifi", "cellular", None], p=[.62,.35,.03])}
            if (kind == "session_end" and telemetry.random() < s.END_LOSS_RATE) or (
                kind == "reward_claimed" and telemetry.random() < s.REWARD_LOSS_RATE):
                continue
            delay = int(telemetry.integers(3600, 259201)) if telemetry.random() < s.LATE_RATE else int(telemetry.integers(0, 16))
            yield "events", dict(event_id=session_id*1000+sequence, session_id=session_id,
                     event_sequence=sequence, event_timestamp=at, received_at=at+timedelta(seconds=delay),
                     event_type=kind, attempt_id=attempt_id, purchase_id=purchase_id,
                     properties={"schema_version": 1, **payload})
        previous_failure_fraction = failures/len(attempts)
        hazard = (s.EARLY_EXIT_BASE+.19*(1-engagement)) if session_number <= 3 else (s.ESTABLISHED_EXIT_BASE+.032*(1-engagement))
        hazard += .018*previous_failure_fraction + (.035 if interrupted else 0)
        if exposed and variant == "treatment" and session_number <= 3:
            hazard -= s.TUTORIAL_EFFECT
        if rng.random() < hazard:
            break
        # Time gaps depend on persistent engagement; weekend and evening activity vary.
        if rng.random() < .15*engagement:
            start = end+timedelta(seconds=log_seconds(rng, 10800, .6, 1800, 43200))
        else:
            gaps = np.arange(1, 46)
            weights = np.exp(-gaps/(1.2+3*(1-engagement)+.5*previous_failure_fraction))
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
            "time_limit_lookup": {(r["level_id"], r["release_id"]): r["time_limit_seconds"] for r in catalog["level_configurations"]},
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
