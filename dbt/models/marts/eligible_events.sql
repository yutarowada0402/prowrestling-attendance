select * from {{ ref('fct_events') }} where country_code='JP' and event_status='held'
