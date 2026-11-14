select count(*) as collected_events, count(*) filter(where event_status='held') as held_events,
 count(*) filter(where country_code='JP' and event_status='held') as domestic_held_events,
 count(attendance_reported) filter(where country_code='JP' and event_status='held') as domestic_attendance_known,
 count(attendance_reported) filter(where country_code='JP' and event_status='held')::double /
 nullif(count(*) filter(where country_code='JP' and event_status='held'),0) as domestic_attendance_known_rate,
 count(*) filter(where conflict_flag) as conflicts,
 count(*) filter(where attendance_disappeared) as attendance_disappeared,
 count(*) filter(where country_code is null) as country_unknown,
 min(event_date) as date_from, max(event_date) as date_to
from {{ ref('fct_events') }}
