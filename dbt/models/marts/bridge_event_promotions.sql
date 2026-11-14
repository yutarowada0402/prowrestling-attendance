select distinct event_id, unnest(string_split(promotion_ids,'|')) as promotion_id,
       primary_promotion_id, 'organizer_unspecified' as role
from {{ ref('int_events') }}
