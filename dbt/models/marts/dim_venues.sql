select * from raw_venues
union all
select distinct venue_id, venue_raw, country_code, null, null
from {{ ref('int_events') }} where venue_id not in (select venue_id from raw_venues)
