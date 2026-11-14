select * exclude(event_date, attendance_reported),
       cast(event_date as date) as event_date,
       cast(attendance_reported as bigint) as attendance_reported
from raw_observations
