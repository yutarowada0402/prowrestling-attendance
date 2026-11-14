select * from {{ ref('fct_events') }} where attendance_reported < 0
