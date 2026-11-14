select * from {{ ref('attendance_monthly') }} where attendance_known > events_held
or attendance_known_rate < 0 or attendance_known_rate > 1
or (attendance_known=0 and attendance_total is not null)
