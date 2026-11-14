select a.event_id as event_id_a, b.event_id as event_id_b, a.event_date, a.venue_id,
       a.start_time as start_time_a, b.start_time as start_time_b,
       'same_date_venue_review_only' as reason
from {{ ref('fct_events') }} a join {{ ref('fct_events') }} b
 on a.event_date=b.event_date and a.venue_id=b.venue_id and a.event_id<b.event_id
