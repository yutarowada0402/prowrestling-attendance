with cutoffs as (
 select primary_promotion_id, extract(year from event_date)::integer as year, max(event_date) as cutoff
 from {{ ref('eligible_events') }} group by 1,2
)
select c.*, e.events_held, e.attendance_known, e.attendance_total,
 p.events_held as previous_events_held, p.attendance_known as previous_attendance_known,
 p.attendance_total as previous_attendance_total,
 e.attendance_total/nullif(p.attendance_total,0)-1 as attendance_yoy
from cutoffs c
left join lateral (select count(*) as events_held, count(attendance_reported) as attendance_known,
 sum(attendance_reported) as attendance_total from {{ ref('eligible_events') }} e
 where e.primary_promotion_id=c.primary_promotion_id
 and e.event_date between make_date(c.year,1,1) and c.cutoff) e on true
left join lateral (select count(*) as events_held, count(attendance_reported) as attendance_known,
 sum(attendance_reported) as attendance_total from {{ ref('eligible_events') }} p
 where p.primary_promotion_id=c.primary_promotion_id
 and p.event_date between make_date(c.year-1,1,1) and cast(c.cutoff-interval 1 year as date)) p on true
