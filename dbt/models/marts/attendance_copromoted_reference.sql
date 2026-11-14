select b.promotion_id, count(distinct e.event_id) as events_held,
 count(e.attendance_reported) as attendance_known, sum(e.attendance_reported) as attendance_total
from {{ ref('eligible_events') }} e join {{ ref('bridge_event_promotions') }} b using(event_id)
group by 1
