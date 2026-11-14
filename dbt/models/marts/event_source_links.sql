select distinct event_id, source, source_event_id, source_url from {{ ref('int_events') }}
