-- SELECT *
-- FROM information_schema.tables
-- WHERE table_schema NOT IN ('pg_catalog', 'information_schema')

-- select chapter, count(level_id) as "levels per chapter"
-- from levels
-- group by chapter
-- order by chapter

-- select status, count(purchase_id), sum(amount) as "sum amount", sum(revenue_usd) "sum revenue"
-- from purchases
-- group by status

-- select round(avg(duration_seconds) / 60, 2) as "minutes" from sessions

-- select count(session_id) from sessions
-- select distinct status from sessions

-- select session_id, status, (ended_at - started_at) as "calc_duration", duration_seconds * interval '1 seconds'
-- from sessions

-- select status, count(session_id)
-- from sessions
-- group by status

-- select round(avg(duration_seconds)/60.0, 2), round(min(duration_seconds)/60.0, 2), round(max(duration_seconds)/60.0, 2)
-- from sessions

-- select 
-- count (session_id),
-- count(duration_seconds = round(extract(epoch from ended_at - started_at)))
-- from sessions

-- select *
-- from sessions
-- where duration_seconds <=0 or ended_at < started_at

-- with registrations_by_session as (
-- 	select s.session_id, p.player_id, s.started_at, p.registered_at, p.registered_at > s.started_at as "registered_after_session"
-- 	from sessions as s
-- 	left join players as p on s.player_id = p.player_id
-- )
-- select registered_after_session, count(registered_after_session)
-- from registrations_by_session
-- group by registered_after_session

-- SELECT
--     COUNT(*) AS total_sessions,
--     COUNT(*) FILTER (
--         WHERE duration_seconds =
--             ROUND(EXTRACT(EPOCH FROM (ended_at - started_at)))
--     ) AS matching_sessions,
--     COUNT(*) FILTER (
--         WHERE duration_seconds IS DISTINCT FROM
--             ROUND(EXTRACT(EPOCH FROM (ended_at - started_at)))
--     ) AS mismatching_sessions
-- FROM sessions;

-- SELECT 
-- 	status, 
-- 	COUNT(*) as session_count,
-- 	round(avg(duration_seconds)/60.0, 2) as avg_duration_minutes,
-- 	ROUND(
-- 		COUNT(*) * 100.0 / sum(count(*)) over (), 
-- 		2) as sessions_by_status_pct,
-- 	round((percentile_cont(0.5) within group (order by duration_seconds))::numeric, 2) as median
-- FROM sessions
-- GROUP BY status
-- ORDER BY session_count DESC

-- SELECT
--     status,
--     MIN(duration_seconds) AS min_seconds,
--     PERCENTILE_CONT(0.25)
--         WITHIN GROUP (ORDER BY duration_seconds) AS p25,
--     PERCENTILE_CONT(0.50)
--         WITHIN GROUP (ORDER BY duration_seconds) AS p50,
--     PERCENTILE_CONT(0.75)
--         WITHIN GROUP (ORDER BY duration_seconds) AS p75,
--     PERCENTILE_CONT(0.90)
--         WITHIN GROUP (ORDER BY duration_seconds) AS p90,
--     PERCENTILE_CONT(0.99)
--         WITHIN GROUP (ORDER BY duration_seconds) AS p99,
--     MAX(duration_seconds) AS max_seconds
-- FROM sessions
-- GROUP BY status;

-- SELECT
--     duration_seconds,
--     status,
--     COUNT(*) AS session_count
-- FROM sessions
-- GROUP BY duration_seconds, status
-- ORDER BY duration_seconds, status;

-- with per_day as (
-- 	select 
-- 		started_at::date as session_date,
-- 		player_id,
-- 		session_id
-- 	from sessions
-- ),
-- grouped_sessions as (
-- 	select 
-- 		session_date,
-- 		count (distinct player_id) as dau,
-- 		count (session_id) as count_sessions
-- 	from per_day
-- 	group by session_date)
-- select 
-- 	session_date,
-- 	dau,
-- 	count_sessions,
-- 	round(count_sessions / dau::numeric, 2) as sessions_per_dau
-- from grouped_sessions

-- same as above but corrected and easier
-- SELECT
--     started_at::date AS session_date,
--     COUNT(DISTINCT player_id) AS dau,
--     COUNT(*) AS session_count,
--     ROUND(
--         COUNT(*)::numeric
--         / NULLIF(COUNT(DISTINCT player_id), 0),
--         2
--     ) AS sessions_per_dau
-- FROM sessions
-- GROUP BY started_at::date
-- ORDER BY session_date;

-- with first_sessions as (
-- 	select
-- 		player_id,
-- 		min((started_at at time zone 'UTC')::date) as first_session_date
-- 	from sessions
-- 	group by player_id
-- ),
-- active_days as (
-- 	select distinct
-- 		player_id,
-- 		(started_at at time zone 'UTC')::date as session_date
-- 	from sessions
-- )
-- select 
-- 	f.player_id,
-- 	f.first_session_date,
-- 	a.player_id is not null as returned_d1
-- from first_sessions as f
-- left join active_days as a 
-- 	on f.player_id = a.player_id and
-- 		f.first_session_date + 1 = a.session_date
-- order by f.player_id

-- with first_sessions as (
-- 	select
-- 		player_id,
-- 		min((started_at at time zone 'UTC')::date) as first_session_date
-- 	from sessions
-- 	group by player_id
-- ),
-- active_days as (
-- 	select distinct
-- 		player_id,
-- 		(started_at at time zone 'UTC')::date as session_date
-- 	from sessions
-- ),
-- joined_d1 as (
-- 	select 
-- 		f.player_id,
-- 		f.first_session_date,
-- 		a.player_id is not null as returned_d1
-- 	from first_sessions as f
-- 	left join active_days as a 
-- 		on f.player_id = a.player_id and
-- 			f.first_session_date + 1 = a.session_date
-- ),
-- joined_d7 as (
-- 	select 
-- 		jd1.player_id,
-- 		jd1.first_session_date,
-- 		a.session_date as d7_session_date,
-- 		jd1.returned_d1,
-- 		a.player_id is not null as returned_d7
-- 	from joined_d1 as jd1
-- 	left join active_days as a 
-- 		on jd1.player_id = a.player_id and
-- 			jd1.first_session_date + 7 = a.session_date
-- ),
-- joined_d30 as (
-- 	select 
-- 		jd7.player_id,
-- 		jd7.first_session_date,
-- 		jd7.d7_session_date,
-- 		a.session_date as d30_session_date,
-- 		jd7.returned_d1,
-- 		jd7.returned_d7,
-- 		a.player_id is not null as returned_d30
-- 	from joined_d7 as jd7
-- 	left join active_days as a 
-- 		on jd7.player_id = a.player_id and
-- 			jd7.first_session_date + 30 = a.session_date
-- ),
-- observation_window AS (
--     SELECT
--         MAX((started_at AT TIME ZONE 'UTC')::date)
--             AS last_observation_date
--     FROM sessions
-- )
-- select 
-- 	count(*) filter (where first_session_date <= last_observation_date - 1) as eligible_d1,
-- 	count(*) filter (where first_session_date <= last_observation_date - 7) as eligible_d7,
-- 	count(*) filter (where first_session_date <= last_observation_date - 30) as eligible_d30,
-- 	count(*) filter (where returned_d1 and first_session_date <= last_observation_date - 1) as returned_d1,
-- 	count(*) filter (where returned_d7 and first_session_date <= last_observation_date - 7) as returned_d7,
-- 	count(*) filter (where returned_d30 and first_session_date <= last_observation_date - 30) as returned_d30,
-- 	round(count(*) filter (where returned_d1 and first_session_date <= last_observation_date - 1) * 100.0
-- 		/ nullif(count(*) filter(where first_session_date <= last_observation_date - 1), 0), 2) as d1_retention_pct,
-- 	round(count(*) filter (where returned_d7 and first_session_date <= last_observation_date - 7) * 100.0
-- 		/ nullif(count(*) filter(where first_session_date <= last_observation_date - 7), 0), 2) as d7_retention_pct,
-- 	round(count(*) filter (where returned_d30 and first_session_date <= last_observation_date - 30) * 100.0
-- 	/ nullif(count(*) filter(where first_session_date <= last_observation_date - 30), 0), 2) as d30_retention_pct
-- from joined_d30
-- cross join observation_window

with first_sessions as (
	select
		player_id,
		min((started_at at time zone 'UTC')::date) as first_session_date
	from sessions
	group by player_id
),
active_days as (
	select distinct
		player_id,
		(started_at at time zone 'UTC')::date as session_date
	from sessions
),
joined_d1 as (
	select 
		f.player_id,
		f.first_session_date,
		a.player_id is not null as returned_d1
	from first_sessions as f
	left join active_days as a 
		on f.player_id = a.player_id and
			f.first_session_date + 1 = a.session_date
),
joined_d7 as (
	select 
		jd1.player_id,
		jd1.first_session_date,
		a.session_date as d7_session_date,
		jd1.returned_d1,
		a.player_id is not null as returned_d7
	from joined_d1 as jd1
	left join active_days as a 
		on jd1.player_id = a.player_id and
			jd1.first_session_date + 7 = a.session_date
),
joined_d30 as (
	select 
		jd7.player_id,
		jd7.first_session_date,
		jd7.d7_session_date,
		a.session_date as d30_session_date,
		jd7.returned_d1,
		jd7.returned_d7,
		a.player_id is not null as returned_d30
	from joined_d7 as jd7
	left join active_days as a 
		on jd7.player_id = a.player_id and
			jd7.first_session_date + 30 = a.session_date
),
observation_window AS (
    SELECT
        MAX((started_at AT TIME ZONE 'UTC')::date)
            AS last_observation_date
    FROM sessions
)
select 
	date_trunc('month', first_session_date)::date as cohort_month,
	count(*) filter (where first_session_date <= last_observation_date - 1) as eligible_d1,
	count(*) filter (where first_session_date <= last_observation_date - 7) as eligible_d7,
	count(*) filter (where first_session_date <= last_observation_date - 30) as eligible_d30,
	count(*) filter (where returned_d1 and first_session_date <= last_observation_date - 1) as returned_d1,
	count(*) filter (where returned_d7 and first_session_date <= last_observation_date - 7) as returned_d7,
	count(*) filter (where returned_d30 and first_session_date <= last_observation_date - 30) as returned_d30,
	round(count(*) filter (where returned_d1 and first_session_date <= last_observation_date - 1) * 100.0
		/ nullif(count(*) filter(where first_session_date <= last_observation_date - 1), 0), 2) as d1_retention_pct,
	round(count(*) filter (where returned_d7 and first_session_date <= last_observation_date - 7) * 100.0
		/ nullif(count(*) filter(where first_session_date <= last_observation_date - 7), 0), 2) as d7_retention_pct,
	round(count(*) filter (where returned_d30 and first_session_date <= last_observation_date - 30) * 100.0
	/ nullif(count(*) filter(where first_session_date <= last_observation_date - 30), 0), 2) as d30_retention_pct
from joined_d30
cross join observation_window
group by cohort_month
order by cohort_month