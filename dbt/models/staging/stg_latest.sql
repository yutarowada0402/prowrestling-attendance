with ranked as (
  select o.*, c.checked_at,
    row_number() over (partition by source, source_event_id
      order by (o.observation_id = c.observation_id) desc nulls last, fetched_at desc, o.observation_id) as rn
  from {{ ref('stg_observations') }} o left join raw_checks c using(source_url)
), prior_value as (
  select source, source_event_id, attendance_reported as retained_attendance,
         observation_id as retained_observation_id
  from {{ ref('stg_observations') }} where attendance_reported is not null
  qualify row_number() over (partition by source, source_event_id order by fetched_at desc, observation_id) = 1
)
select r.* exclude(rn), p.retained_attendance, p.retained_observation_id,
       r.attendance_reported is null and p.retained_attendance is not null as attendance_disappeared
from ranked r left join prior_value p using(source, source_event_id) where rn = 1
