-- Each statement returns a violation count, never a business metric.
-- check: session_chronology
SELECT count(*) FROM sessions s JOIN players p USING (player_id) JOIN game_releases r USING (release_id)
WHERE s.started_at < p.registered_at OR s.ended_at <= s.started_at OR s.duration_seconds <= 0
   OR s.ended_at <> s.started_at + s.duration_seconds * INTERVAL '1 second'
   OR s.started_at < r.released_at OR r.platform <> p.platform;
-- check: session_overlap_and_sequence
SELECT count(*) FROM (
 SELECT *, lag(ended_at) OVER (PARTITION BY player_id ORDER BY session_number) AS previous_end,
 row_number() OVER (PARTITION BY player_id ORDER BY session_number) AS expected_number FROM sessions
) s WHERE started_at < previous_end OR session_number <> expected_number;
-- check: observation_window
SELECT count(*) FROM sessions s CROSS JOIN generation_runs g
WHERE s.started_at < g.observation_start OR s.ended_at >= g.observation_end;
-- check: acquisition_consistency
SELECT count(*) FROM players p LEFT JOIN campaigns c USING (campaign_id) CROSS JOIN generation_runs g
WHERE p.registered_at < g.observation_start OR p.registered_at >= g.observation_end
OR (p.campaign_id IS NOT NULL AND (p.acquisition_channel <> c.channel OR p.registered_at::date NOT BETWEEN c.starts_on AND c.ends_on));
-- check: campaign_spend_dates
SELECT count(*) FROM campaign_daily_spend d JOIN campaigns c USING (campaign_id)
WHERE d.spend_date NOT BETWEEN c.starts_on AND c.ends_on;
-- check: attempt_session_boundaries
SELECT count(*) FROM level_attempts a JOIN sessions s USING (session_id)
WHERE a.started_at < s.started_at OR a.ended_at > s.ended_at OR a.ended_at <= a.started_at
OR a.release_id <> s.release_id
OR (a.outcome = 'abandoned' AND (s.status <> 'interrupted' OR a.ended_at <> s.ended_at));
-- check: attempt_order_and_progression
SELECT count(*) FROM (
 SELECT a.*, s.player_id, lag(a.ended_at) OVER w AS previous_end,
 lag(a.level_id) OVER w AS previous_level, lag(a.outcome) OVER w AS previous_outcome,
 row_number() OVER (PARTITION BY a.session_id ORDER BY a.attempt_number) AS expected_number
 FROM level_attempts a JOIN sessions s USING (session_id)
 WINDOW w AS (PARTITION BY s.player_id ORDER BY s.session_number,a.attempt_number)
) a WHERE a.started_at < previous_end OR attempt_number <> expected_number
OR (previous_level IS NULL AND level_id <> 1)
OR (previous_level IS NOT NULL AND level_id <> least(100, previous_level + CASE WHEN previous_outcome = 'completed' THEN 1 ELSE 0 END));
-- check: interrupted_session_outcomes
SELECT count(*) FROM sessions s WHERE
(s.status = 'interrupted') <> EXISTS (SELECT 1 FROM level_attempts a WHERE a.session_id=s.session_id AND a.outcome='abandoned')
OR NOT EXISTS (SELECT 1 FROM level_attempts a WHERE a.session_id=s.session_id);
-- check: purchase_chronology_and_currency
SELECT count(*) FROM purchases p JOIN sessions s USING (session_id) JOIN exchange_rates x USING (rate_date,currency)
WHERE p.player_id <> s.player_id OR p.initiated_at < s.started_at OR p.initiated_at > s.ended_at
OR p.resolved_at > s.ended_at OR p.resolved_at < p.initiated_at OR p.amount <= 0
OR (p.status = 'pending') <> (p.resolved_at IS NULL)
OR p.rate_date <> p.initiated_at::date
OR p.revenue_usd <> CASE WHEN p.status='completed' THEN round(p.amount*x.usd_per_unit,2) ELSE 0 END;
-- check: event_session_consistency
SELECT count(*) FROM events e JOIN sessions s USING (session_id)
WHERE e.event_timestamp NOT BETWEEN s.started_at AND s.ended_at OR e.received_at < e.event_timestamp
OR e.received_at > e.event_timestamp + INTERVAL '72 hours'
OR (e.event_type='session_start' AND (e.event_timestamp <> s.started_at OR e.event_sequence <> 1))
OR (e.event_type='session_end' AND (e.event_timestamp <> s.ended_at OR s.status <> 'completed'))
OR e.event_id <> e.session_id*1000+e.event_sequence;
-- check: event_source_order
SELECT count(*) FROM (SELECT *, lag(event_timestamp) OVER (PARTITION BY session_id ORDER BY event_sequence) AS prior_time FROM events) e
WHERE event_timestamp < prior_time;
-- check: event_attempt_payload_and_outcome
SELECT count(*) FROM events e JOIN level_attempts a USING (attempt_id)
WHERE e.session_id <> a.session_id
OR (e.properties ? 'level_id' AND (e.properties->>'level_id')::integer <> a.level_id)
OR (e.event_type IN ('level_start','level_retry') AND e.event_timestamp <> a.started_at)
OR (e.event_type IN ('level_complete','reward_claimed') AND (a.outcome <> 'completed' OR e.event_timestamp <> a.ended_at))
OR (e.event_type IN ('level_failed','player_died') AND (a.outcome <> 'failed' OR e.event_timestamp <> a.ended_at));
-- check: required_session_events
SELECT count(*) FROM sessions s LEFT JOIN (
 SELECT session_id, count(*) FILTER (WHERE event_type='session_start') AS starts,
 count(*) FILTER (WHERE event_type='session_end') AS ends FROM events GROUP BY session_id
) e USING (session_id) WHERE coalesce(starts,0) <> 1 OR ends > 1 OR (s.status='interrupted' AND ends <> 0);
-- check: required_attempt_events
SELECT count(*) FROM level_attempts a LEFT JOIN (
 SELECT attempt_id, count(*) FILTER (WHERE event_type='level_start') AS starts,
 count(*) FILTER (WHERE event_type='level_complete') AS completed,
 count(*) FILTER (WHERE event_type='level_failed') AS failed,
 count(*) FILTER (WHERE event_type='player_died') AS deaths,
 count(*) FILTER (WHERE event_type='reward_claimed') AS rewards
 FROM events WHERE attempt_id IS NOT NULL GROUP BY attempt_id
) e USING (attempt_id)
WHERE coalesce(starts,0) <> 1 OR completed <> CASE WHEN outcome='completed' THEN 1 ELSE 0 END
OR failed <> CASE WHEN outcome='failed' THEN 1 ELSE 0 END OR deaths <> failed OR rewards > completed;
-- check: retry_semantics
SELECT count(*) FROM (
 SELECT a.*, lag(a.outcome) OVER (PARTITION BY s.player_id ORDER BY s.session_number, a.attempt_number) AS prior_outcome
 FROM level_attempts a JOIN sessions s USING (session_id)
) a WHERE (SELECT count(*) FROM events e WHERE e.attempt_id=a.attempt_id AND event_type='level_retry')
<> CASE WHEN prior_outcome='failed' THEN 1 ELSE 0 END;
-- check: purchase_event_consistency
SELECT count(*) FROM purchases p LEFT JOIN (
 SELECT purchase_id, count(*) FILTER (WHERE event_type='purchase_started') AS starts,
 count(*) FILTER (WHERE event_type='purchase_completed') AS completed FROM events
 WHERE purchase_id IS NOT NULL GROUP BY purchase_id
) e USING (purchase_id) WHERE coalesce(starts,0) <> 1 OR completed <> CASE WHEN status='completed' THEN 1 ELSE 0 END;
-- check: purchase_event_payload
SELECT count(*) FROM events e JOIN purchases p USING (purchase_id)
WHERE e.session_id <> p.session_id OR (e.properties->>'item_id')::integer <> p.item_id
OR (e.event_type='purchase_started' AND e.event_timestamp <> p.initiated_at)
OR (e.event_type='purchase_completed' AND (p.status <> 'completed' OR e.event_timestamp <> p.resolved_at));
-- check: experiment_eligibility_and_assignment
SELECT count(*) FROM experiment_assignments a JOIN experiments x USING (experiment_id) JOIN players p USING (player_id)
WHERE a.assigned_at <> p.registered_at OR a.assigned_at < x.starts_at OR a.assigned_at >= x.ends_at;
-- check: experiment_eligible_coverage
SELECT count(*) FROM players p CROSS JOIN experiments x
WHERE p.registered_at >= x.starts_at AND p.registered_at < x.ends_at
AND NOT EXISTS (SELECT 1 FROM experiment_assignments a WHERE a.player_id=p.player_id AND a.experiment_id=x.experiment_id);
-- check: experiment_exposure_chronology
SELECT count(*) FROM experiment_exposures e JOIN experiment_assignments a USING (experiment_id,player_id)
JOIN experiments x USING (experiment_id) JOIN sessions s USING (session_id)
WHERE e.exposed_at < a.assigned_at OR e.exposed_at NOT BETWEEN s.started_at AND s.ended_at
OR e.exposed_at >= x.ends_at OR s.player_id <> e.player_id OR s.session_number <> 1
OR NOT EXISTS (SELECT 1 FROM events t WHERE t.session_id=e.session_id AND t.event_type='tutorial_started' AND t.event_timestamp=e.exposed_at);
-- check: experiment_exposure_coverage
SELECT count(*) FROM experiment_assignments a JOIN experiments x USING (experiment_id)
JOIN sessions s ON s.player_id=a.player_id AND s.session_number=1
JOIN events t ON t.session_id=s.session_id AND t.event_type='tutorial_started'
WHERE t.event_timestamp < x.ends_at AND NOT EXISTS (
 SELECT 1 FROM experiment_exposures e WHERE e.player_id=a.player_id AND e.experiment_id=a.experiment_id);
-- check: experiment_allocations
SELECT count(*) FROM (SELECT experiment_id FROM experiment_variants GROUP BY experiment_id HAVING sum(allocation) <> 1) x;
-- check: tutorial_sequence
SELECT count(*) FROM sessions s LEFT JOIN (
 SELECT session_id, count(*) FILTER (WHERE event_type='tutorial_started') AS starts,
 count(*) FILTER (WHERE event_type='tutorial_completed') AS ends,
 min(event_timestamp) FILTER (WHERE event_type='tutorial_started') AS first_time,
 min(event_timestamp) FILTER (WHERE event_type='tutorial_completed') AS last_time
 FROM events GROUP BY session_id
) e USING (session_id) WHERE starts <> CASE WHEN session_number=1 THEN 1 ELSE 0 END
OR ends <> starts OR last_time <= first_time;
-- check: shop_before_purchase
SELECT count(*) FROM purchases p WHERE NOT EXISTS (
 SELECT 1 FROM events e WHERE e.session_id=p.session_id AND e.event_type='shop_opened' AND e.event_timestamp < p.initiated_at);
-- check: retry_before_start
SELECT count(*) FROM events r JOIN events s ON s.attempt_id=r.attempt_id AND s.event_type='level_start'
WHERE r.event_type='level_retry' AND r.event_sequence >= s.event_sequence;
-- check: outcome_event_order
SELECT count(*) FROM events e JOIN events s ON s.attempt_id=e.attempt_id AND s.event_type='level_start'
WHERE e.event_type IN ('level_complete','level_failed','player_died','reward_claimed') AND e.event_sequence <= s.event_sequence;
-- check: attempt_time_limit
SELECT count(*) FROM level_attempts a JOIN level_configurations c USING (level_id,release_id)
WHERE a.ended_at-a.started_at > c.time_limit_seconds * INTERVAL '1 second';
-- check: shop_after_gameplay
SELECT count(*) FROM events e WHERE e.event_type='shop_opened' AND EXISTS (
 SELECT 1 FROM level_attempts a WHERE a.session_id=e.session_id AND a.ended_at > e.event_timestamp);
-- check: tutorial_before_gameplay
SELECT count(*) FROM events e WHERE e.event_type='tutorial_completed' AND EXISTS (
 SELECT 1 FROM level_attempts a WHERE a.session_id=e.session_id AND a.started_at < e.event_timestamp);
