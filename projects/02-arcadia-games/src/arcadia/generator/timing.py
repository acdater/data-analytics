"""Bounded continuous timing draws, quantized only to the schema's seconds."""
from functools import lru_cache
import math
import tomllib
from arcadia.common.config import ROOT


@lru_cache(maxsize=1)
def behavior_config():
    return tomllib.loads((ROOT / "config/behavior.toml").read_text())


def log_seconds(rng, median, sigma, low, high):
    """Rejection sampling avoids a probability spike at either bound."""
    if not 0 < low < high or median <= 0 or sigma <= 0:
        raise ValueError("Invalid timing distribution")
    for _ in range(10000):
        value = float(rng.lognormal(math.log(median), sigma))
        if low <= value < high:
            return max(low, int(round(value)))
    raise ValueError("Timing bounds have negligible probability mass")


def play_budget(rng, engagement, level, session_number, previous_failure_fraction):
    t = behavior_config()["timing"]
    median = t["play_median_seconds"] * math.exp(
        t["engagement_log_effect"] * (engagement - .5)
        + t["progression_log_effect"] * math.log1p(level - 1) / math.log(100)
        - t["previous_failure_log_effect"] * previous_failure_fraction
    )
    if session_number == 1:
        median *= t["new_player_multiplier"]
    low = t["first_play_minimum_seconds"] if session_number == 1 else t["minimum_play_seconds"]
    # Reserve room for optional browse/checkout and exit; no end-of-session clipping.
    high = t["maximum_session_seconds"] - sum(t[k] for k in (
        "exit_maximum_seconds", "browse_maximum_seconds", "checkout_maximum_seconds"))
    return log_seconds(rng, median, t["play_log_sigma"], low, high)
