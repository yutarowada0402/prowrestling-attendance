select coalesce(v.event_id, m.event_id) as event_id,
       o.* exclude(event_date,event_status,attendance_reported),
       coalesce(cast(v.event_date as date), o.event_date) as event_date,
       coalesce(v.event_status, o.event_status) as event_status,
       coalesce(v.venue_id, a.venue_id, 'unclassified_' || md5(coalesce(o.venue_raw,'unknown'))) as venue_id,
       coalesce(v.primary_promotion_id, pa.promotion_id, 'unclassified') as primary_promotion_id,
       coalesce(v.promotion_ids, v.primary_promotion_id, pa.promotion_id, 'unclassified') as promotion_ids,
       coalesce(cast(v.attendance_reported as bigint), o.attendance_reported, o.retained_attendance) as attendance_reported,
       v.reason as override_reason,
       v.attendance_reported is not null as manual_attendance,
       case when o.attendance_disappeared then o.retained_observation_id else o.observation_id end as attendance_observation_id
from {{ ref('stg_latest') }} o
join raw_event_ids m using(source,source_event_id)
left join raw_overrides v using(source,source_event_id)
left join raw_venue_aliases a on trim(o.venue_raw) = trim(a.alias)
left join raw_promotion_aliases pa on trim(o.promotion_raw) = trim(pa.alias)
