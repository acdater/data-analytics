from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
import math


def money(value):
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def catalogs(config):
    from .scenarios import SPIKE_LEVEL, SPIKE_DIFFICULTY
    campaigns = []
    spend = []
    for i, channel in enumerate(("paid_social", "paid_search", "creator"), 1):
        campaigns.append(dict(campaign_id=i, name=f"Dungeon Rush {channel} 2025", channel=channel,
                              starts_on=config.start.date(), ends_on=(config.end-timedelta(days=1)).date()))
    day = config.start.date()
    rates = []
    while day < config.end.date():
        n = (day-config.start.date()).days
        for i in range(1, 4):
            amount = money((160 + i*45)*(1 + .25*math.sin(n/23+i)) * (1.15 if day.weekday() >= 5 else 1))
            spend.append(dict(campaign_id=i, spend_date=day, spend_usd=amount,
                              impressions=int(amount*180), clicks=int(amount*3)))
        for currency, base in (("USD", 1), ("EUR", 1.09), ("GBP", 1.28)):
            rate = Decimal(str(base if currency == "USD" else base*(1+.025*math.sin(n/37)))).quantize(Decimal("0.000001"))
            rates.append(dict(rate_date=day, currency=currency, usd_per_unit=rate))
        day += timedelta(days=1)
    releases = [dict(release_id=2*j+i, version=version, platform=platform,
                     released_at=config.start+timedelta(days=offset))
                for j, (version, offset) in enumerate((("1.0.0", 0), ("1.1.0", 90), ("1.2.0", 181), ("1.3.0", 273)))
                for i, platform in enumerate(("ios", "android"), 1)]
    levels = [dict(level_id=i, name=f"Dungeon {i}", chapter=(i-1)//10+1) for i in range(1, 101)]
    configurations = []
    for release in releases:
        for level in levels:
            i = level["level_id"]
            difficulty = .24 + .006*i + (SPIKE_DIFFICULTY if i == SPIKE_LEVEL else 0)
            if release["version"] == "1.3.0" and i == SPIKE_LEVEL:
                difficulty -= .15
            configurations.append(dict(level_id=i, release_id=release["release_id"],
                                       difficulty=Decimal(str(round(difficulty, 3))), time_limit_seconds=180))
    items = [dict(item_id=i, sku=f"DR-{i:03}", name=name, category=category, base_price_usd=money(price))
             for i, (name, category, price) in enumerate((("Small gem pack", "currency", 1.99),
               ("Gem chest", "currency", 9.99), ("Royal gem vault", "currency", 49.99),
               ("Revive bundle", "booster", 4.99), ("Ember cloak", "cosmetic", 7.99)), 1)]
    experiments = [dict(experiment_id=1, name="First journey", starts_at=config.start+timedelta(days=90),
                        ends_at=config.start+timedelta(days=273),
                        eligibility_rule="New registrations during enrollment; assigned at registration, before first session",
                        exposure_trigger="First tutorial_started in the first session, within enrollment window")]
    variants = [dict(experiment_id=1, variant=v, allocation=Decimal("0.5000")) for v in ("control", "treatment")]
    return dict(campaigns=campaigns, campaign_daily_spend=spend, game_releases=releases, levels=levels,
                level_configurations=configurations, items=items, exchange_rates=rates,
                experiments=experiments, experiment_variants=variants)
