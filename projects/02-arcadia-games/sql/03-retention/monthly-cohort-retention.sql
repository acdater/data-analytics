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