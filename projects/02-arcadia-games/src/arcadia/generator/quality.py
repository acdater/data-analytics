"""Streaming generator QA, not learner analytical outputs.

Integer-second histograms keep memory bounded by the timing domain, not row count.
Quantiles use the same linear interpolation convention as NumPy's default.
"""
from collections import Counter
import math
from .timing import behavior_config


def quantile(histogram, probability):
    count = sum(histogram.values())
    position = (count-1)*probability
    lower, upper = math.floor(position), math.ceil(position)
    found = {}
    offset = 0
    for value, frequency in sorted(histogram.items()):
        for index in (lower, upper):
            if offset <= index < offset+frequency:
                found[index] = value
        offset += frequency
    return found[lower]+(position-lower)*(found[upper]-found[lower])


class QualityMonitor:
    def __init__(self, thresholds=None):
        self.thresholds = thresholds or behavior_config()["quality"]
        self.duration = Counter()
        self.first = Counter()
        self.returning = Counter()
        self.attempt_duration = Counter()
        self.attempt_counts = Counter()
        self.purchase_delay = Counter()
        self.attempt_session = None
        self.current_attempts = 0
        self.invalid_duration_count = 0

    def observe(self, table, row):
        if table == "sessions":
            seconds = row["duration_seconds"]
            # Keep corrupted or unbounded input from expanding the histogram domain.
            if not isinstance(seconds, int) or not 0 < seconds <= self.thresholds["maximum_duration_seconds"]:
                self.invalid_duration_count += 1
                return
            self.duration[seconds] += 1
            if row["session_number"] == 1:
                self.first[seconds] += 1
            elif row["session_number"] >= self.thresholds["returning_session_number"]:
                self.returning[seconds] += 1
        elif table == "level_attempts":
            seconds = int((row["ended_at"]-row["started_at"]).total_seconds())
            if 0 < seconds <= self.thresholds["maximum_duration_seconds"]:
                self.attempt_duration[seconds] += 1
            if self.attempt_session is not None and self.attempt_session != row["session_id"]:
                self.attempt_counts[self.current_attempts] += 1
                self.current_attempts = 0
            self.attempt_session = row["session_id"]
            self.current_attempts += 1
        elif table == "purchases" and row["resolved_at"] is not None:
            seconds = int((row["resolved_at"]-row["initiated_at"]).total_seconds())
            if 0 <= seconds <= self.thresholds["maximum_duration_seconds"]:
                self.purchase_delay[seconds] += 1

    def report(self):
        t, hist = self.thresholds, self.duration
        n = sum(hist.values())
        if not n:
            return {"passed": False, "checks": {"duration_population": 1}, "status": "empty"}
        mean = sum(value*count for value, count in hist.items())/n
        variance = sum(count*(value-mean)**2 for value, count in hist.items())/n
        median = quantile(hist, .5)
        stats = {"count": n, "distinct": len(hist), "mean": mean, "median": median,
                 "p25": quantile(hist, .25), "p75": quantile(hist, .75), "p90": quantile(hist, .90),
                 "p99": quantile(hist, .99), "minimum": min(hist), "maximum": max(hist)}
        if n < t["minimum_sessions"]:
            return {"passed": None, "status": "insufficient_sample", "duration_seconds": stats,
                    "required_sessions": t["minimum_sessions"], "checks": {}}
        counts = self.attempt_counts.copy()
        if self.attempt_session is not None:
            counts[self.current_attempts] += 1
        checks = {
            "valid_duration_domain": self.invalid_duration_count == 0,
            "distinct_durations": len(hist) >= t["minimum_distinct_durations"],
            "duration_variation": t["minimum_cv"] <= math.sqrt(variance)/mean <= t["maximum_cv"],
            "right_skew_mean": mean/median >= t["minimum_mean_median_ratio"],
            "right_skew_tail": stats["p90"]/median >= t["minimum_p90_median_ratio"],
            "bounded_tail": stats["p99"] <= t["maximum_p99_seconds"],
            "minimum_duration": min(hist) >= t["minimum_duration_seconds"],
            "no_modal_pileup": max(hist.values())/n <= t["maximum_modal_share"],
            "short_sessions_present": sum(c for v,c in hist.items() if v <= t["maximum_short_seconds"])/n >= t["minimum_short_share"],
            "long_sessions_present": sum(c for v,c in hist.items() if v >= t["minimum_long_seconds"])/n >= t["minimum_long_share"],
            "attempt_count_variation": len(counts) >= t["minimum_attempt_count_values"],
            "attempt_duration_variation": len(self.attempt_duration) >= t["minimum_attempt_duration_values"],
        }
        diagnostics = {"coefficient_of_variation": math.sqrt(variance)/mean, "modal_share": max(hist.values())/n}
        skipped = []
        if min(sum(self.first.values()), sum(self.returning.values())) >= t["minimum_segment_sessions"]:
            ratio = quantile(self.returning, .5)/quantile(self.first, .5)
            diagnostics["returning_first_median_ratio"] = ratio
            checks["lifecycle_segment_tendency"] = t["minimum_returning_first_median_ratio"] <= ratio <= t["maximum_returning_first_median_ratio"]
        else:
            skipped.append("lifecycle_segment_tendency: insufficient segment sample")
        if sum(self.purchase_delay.values()) >= t["minimum_purchases"]:
            checks["checkout_duration_variation"] = len(self.purchase_delay) >= t["minimum_purchase_delay_values"]
        else:
            skipped.append("checkout_duration_variation: insufficient purchase sample")
        return {"passed": all(checks.values()), "status": "checked", "duration_seconds": stats,
                "checks": {key: int(not value) for key,value in checks.items()},
                "diagnostics": diagnostics, "skipped": skipped}


def validate_distributions(connection):
    monitor = QualityMonitor()
    # Read only the required primitive columns; no completed analytical SQL is supplied.
    queries = [
        ("sessions", "SELECT duration_seconds, session_number FROM sessions", ("duration_seconds", "session_number")),
        ("level_attempts", "SELECT session_id, started_at, ended_at FROM level_attempts ORDER BY session_id, attempt_number", ("session_id", "started_at", "ended_at")),
        ("purchases", "SELECT initiated_at, resolved_at FROM purchases", ("initiated_at", "resolved_at")),
    ]
    for table, query, columns in queries:
        with connection.cursor(name=f"quality_{table}") as cursor:
            cursor.execute(query)
            for row in cursor:
                monitor.observe(table, dict(zip(columns, row)))
    return monitor.report()
