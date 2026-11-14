select primary_promotion_id, weekday, count(*) as events_held,
 count(attendance_reported) as attendance_known, sum(attendance_reported) as attendance_total,
 avg(attendance_reported) as attendance_mean, median(attendance_reported) as attendance_median,
 count(attendance_reported)::double/count(*) as attendance_known_rate
from {{ ref('eligible_events') }} group by 1,2
