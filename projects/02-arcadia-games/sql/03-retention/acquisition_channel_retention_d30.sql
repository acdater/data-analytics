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
dau_30 as (
	select 
		f.player_id,
		f.first_session_date,
		a.session_date,
		a.player_id is not null as returned_d30
	from first_sessions as f
	left join active_days as a on f.player_id = a.player_id and
		f.first_session_date + 30 = a.session_date
	
),
observation_window AS (
    SELECT
        MAX((started_at AT TIME ZONE 'UTC')::date)
            AS last_observation_date
    FROM sessions
),
joined_monthly AS (
    SELECT
        f.player_id,
        f.first_session_date,
        DATE_TRUNC('month', f.first_session_date)::date
            AS first_session_month,
        p.platform,
        p.acquisition_channel,
        f.returned_d30
    FROM players p
    JOIN dau_30 f
        ON p.player_id = f.player_id
)
SELECT
    acquisition_channel,

    COUNT(*) FILTER (
        WHERE first_session_date <= last_observation_date - 30
    ) AS eligible_d30,

    COUNT(*) FILTER (
        WHERE returned_d30
          AND first_session_date <= last_observation_date - 30
    ) AS returned_d30,

    ROUND(
        COUNT(*) FILTER (
            WHERE returned_d30
              AND first_session_date <= last_observation_date - 30
        ) * 100.0
        /
        NULLIF(
            COUNT(*) FILTER (
                WHERE first_session_date <= last_observation_date - 30
            ),
            0
        ),
        2
    ) AS d30_retention_pct

FROM joined_monthly
CROSS JOIN observation_window
GROUP BY
    acquisition_channel
ORDER BY
    acquisition_channel;