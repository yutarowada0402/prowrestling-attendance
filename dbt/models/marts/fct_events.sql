with ranked as (
 select *, count(distinct attendance_reported) over(partition by event_id) > 1 as source_conflict,
 row_number() over(partition by event_id order by manual_attendance desc,
   (attendance_reported is not null) desc, coalesce(checked_at,fetched_at) desc, source, source_event_id) as rn
 from {{ ref('int_events') }}
)
select event_id, event_date, start_time,
       coalesce(timezone, case when v.country_code='JP' then 'Asia/Tokyo' end) as timezone,
       coalesce(v.country_code,r.country_code) as country_code,
       event_name_raw as event_name, r.venue_id, coalesce(v.display_name,venue_raw) as venue,
       coalesce(v.prefecture,'未分類') as prefecture, coalesce(v.city,'未分類') as city,
       primary_promotion_id, event_status, attendance_reported,
       case when manual_attendance then 'manual' else source end as attendance_source,
       source_url, attendance_raw, attendance_note, attendance_observation_id,
       source_conflict or attendance_disappeared as conflict_flag,
       attendance_disappeared, override_reason, extraction_warnings,
       extract(isodow from event_date)::integer as weekday
from ranked r left join raw_venues v using(venue_id) where rn = 1
