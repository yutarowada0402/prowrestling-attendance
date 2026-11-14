with agg as (
 select primary_promotion_id, strftime(event_date,'%Y-%m') as month,
 count(*) as events_held, count(attendance_reported) as attendance_known,
 sum(attendance_reported) as attendance_total, avg(attendance_reported) as attendance_mean,
 median(attendance_reported) as attendance_median,
 count(attendance_reported)::double/count(*) as attendance_known_rate
 from {{ ref('eligible_events') }} group by 1,2
), compared as (
 select a.*, p.events_held as previous_events_held, p.attendance_total as previous_attendance_total,
 p.attendance_mean as previous_attendance_mean,
 a.attendance_total/nullif(p.attendance_total,0)-1 as attendance_yoy,
 a.events_held::double/nullif(p.events_held,0)-1 as events_yoy,
 a.attendance_mean/nullif(p.attendance_mean,0)-1 as mean_yoy,
 (a.attendance_known-p.attendance_known)*p.attendance_mean as known_event_count_effect,
 a.attendance_known*(a.attendance_mean-p.attendance_mean) as known_event_mean_effect
 from agg a left join agg p on a.primary_promotion_id=p.primary_promotion_id
 and cast(a.month||'-01' as date) = cast(p.month||'-01' as date)+interval 1 year
)
select * from compared
