create or replace transient table DEMO_DB.DE_CASE_BILALQURESHI0309_SCHEMA.MART_GTM_FUNNEL_DAILY as
with f as (
  select
    fo.OPPORTUNITY_ID,
    fo.OPP_START_DATE::date as dt,   -- business-valid opp start (demo booked)
    fo.DEMO_SET_DATE,
    fo.DEMO_HELD_DATE,
    fo.STAGE_NAME,
    fo.LOSS_REASON_GROUP,
    dc.CHANNEL_GROUP
  from DEMO_DB.DE_CASE_BILALQURESHI0309_SCHEMA.FACT_OPPORTUNITY fo
  left join DEMO_DB.DE_CASE_BILALQURESHI0309_SCHEMA.DIM_CHANNEL dc
    on fo.SOURCE_CHANNEL = dc.CHANNEL_KEY
),
flags as (
  select
    dt,
    CHANNEL_GROUP,
    1 as opp_created_flag,
    /* Set: explicit set date OR a demo time exists */
    case when DEMO_SET_DATE is not null or DEMO_HELD_DATE is not null then 1 else 0 end as demos_set_flag,
    /* Held: has time AND not a 'No Show' */
    case when DEMO_HELD_DATE is not null and coalesce(LOSS_REASON_GROUP,'OTHER') <> 'NO_SHOW' then 1 else 0 end as demos_held_flag,
    case when STAGE_NAME = 'CLOSED WON'      then 1 else 0 end as closed_won_flag,
    case when STAGE_NAME like 'CLOSED LOST%' then 1 else 0 end as closed_lost_flag
  from f
)
select
  dt,
  CHANNEL_GROUP,
  sum(opp_created_flag) as OPP_CREATED,
  sum(demos_set_flag)   as DEMOS_SET,
  sum(demos_held_flag)  as DEMOS_HELD,
  sum(closed_won_flag)  as CLOSED_WON,
  sum(closed_lost_flag) as CLOSED_LOST
from flags
group by 1,2
order by 1,2;
