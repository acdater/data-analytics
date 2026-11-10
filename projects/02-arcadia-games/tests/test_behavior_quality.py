"""Generator acceptance/regression tests; these do not solve learner analyses."""
from collections import Counter
from dataclasses import replace
import numpy as np
import pytest
from arcadia.common.config import load_config
from arcadia.generator.quality import QualityMonitor, quantile
from arcadia.generator.simulate import generate
from arcadia.generator.timing import behavior_config, play_budget


@pytest.fixture(scope="module")
def development_quality():
    monitor = QualityMonitor()
    for table, row in generate(load_config("development")):
        monitor.observe(table, row)
    return monitor.report()


def test_development_distribution_quality(development_quality):
    assert development_quality["status"] == "checked"
    assert development_quality["passed"], development_quality
    assert not development_quality["skipped"]


@pytest.mark.parametrize("durations", [
    [470, 650]*1000,                  # Original fixed-attempt template.
    [470]*2000,                      # Collapsed distribution.
    list(range(50, 2050)),           # Variable but symmetric, not right-skewed.
])
def test_quality_rejects_degenerate_or_uniform_durations(durations):
    monitor = QualityMonitor()
    for i, seconds in enumerate(durations):
        monitor.observe("sessions", {"duration_seconds": seconds, "session_number": 1 if i % 2 else 5})
    report = monitor.report()
    assert not report["passed"]
    duration_checks = {key: value for key, value in report["checks"].items()
                       if key in {"distinct_durations", "duration_variation", "right_skew_mean", "right_skew_tail", "no_modal_pileup"}}
    assert any(duration_checks.values()), report


def test_small_samples_explicitly_skip_population_claims():
    monitor = QualityMonitor()
    for table, row in generate(replace(load_config(), players=2)):
        monitor.observe(table, row)
    assert monitor.report()["status"] == "insufficient_sample"
    assert monitor.report()["passed"] is None


def test_histogram_quantiles_match_numpy():
    values = [4, 4, 12, 80, 120, 120, 900]
    hist = Counter(values)
    for p in (0, .25, .5, .75, .9, .99, 1):
        assert quantile(hist, p) == pytest.approx(np.quantile(values, p))


def test_engagement_tendency_with_session_variation():
    # Controlled same-state draws avoid interpreting observational survival as causation.
    t = behavior_config()["quality"]
    sample_size = t["minimum_sessions"]
    low_rng, high_rng = np.random.default_rng(110), np.random.default_rng(110)
    casual = [play_budget(low_rng, .2, 15, 8, 0) for _ in range(sample_size)]
    engaged = [play_budget(high_rng, .8, 15, 8, 0) for _ in range(sample_size)]
    expected_ratio = np.exp(behavior_config()["timing"]["engagement_log_effect"]*(.8-.2))
    # Broad tolerance allows truncation and random variation, not a significance test.
    tolerance = t["controlled_engagement_ratio_tolerance"]
    assert expected_ratio*(1-tolerance) < np.median(engaged)/np.median(casual) < expected_ratio*(1+tolerance)
    assert len(set(casual)) >= t["minimum_distinct_durations"]
    assert len(set(engaged)) >= t["minimum_distinct_durations"]
    assert np.quantile(casual, .9) > np.quantile(engaged, .25)
