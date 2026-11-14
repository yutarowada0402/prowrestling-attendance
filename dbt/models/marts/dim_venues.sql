select * from raw_venues
union all
select venue_id, coalesce(min(venue_raw),'会場未公表'), max(country_code), max(prefecture_raw), null
from {{ ref('int_events') }} where venue_id not in (select venue_id from raw_venues)
group by venue_id
