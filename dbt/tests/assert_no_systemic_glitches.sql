-- BUG-009: single transponder glitches are filtered in staging and counted.
-- But if a large share of ONE snapshot is implausible, it is a systemic bug
-- (OpenSky changed the field order, lat/lon swapped, wrong units).
-- That must still stop the publish.
select snapshot_ts, count(*) as rows_in_snapshot,
       sum(case when not is_plausible then 1 else 0 end) as implausible_rows
from {{ ref('stg_state_vectors') }}
group by snapshot_ts
having sum(case when not is_plausible then 1 else 0 end) > {{ var('max_glitch_share') }} * count(*)
