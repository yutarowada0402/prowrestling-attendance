select * from raw_overrides where reason is null or source is null or source_event_id is null
or (attendance_reported is not null and
    (try_cast(attendance_reported as bigint) is null or try_cast(attendance_reported as bigint)<0))
