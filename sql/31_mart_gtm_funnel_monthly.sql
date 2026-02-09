create or replace view DEMO_DB.DE_CASE_BILALQURESHI0309_SCHEMA.MART_GTM_FUNNEL_MONTHLY as
with f as (
  select
    fo.OPP_START_DATE::date as dt,
    fo.DEMO_SET_DATE,
    fo.DEMO_HELD_DATE,
    fo.STAGE_NAME,
    fo.LOSS_REASON_GROUP,
    dc.CHANNEL_GROUP
  from DEMO_DB.DE_CASE_BILALQURESHI0309_SCHEMA.FACT_OPPORTUNITY fo
  left join DEMO_DB.DE_CASE_BILALQURESHI0309_SCHEMA.DIM_CHANNEL dc
    on fo.SOURCE_CHANNEL = dc.CHANNEL_KEY
)
select
  date_trunc('month', dt) as MONTH,
  CHANNEL_GROUP,
  count(*) as OPP_CREATED,
  sum(case when DEMO_SET_DATE is not null or DEMO_HELD_DATE is not null then 1 else 0 end) as DEMOS_SET,
  sum(case when DEMO_HELD_DATE is not null and coalesce(LOSS_REASON_GROUP,'OTHER') <> 'NO_SHOW' then 1 else 0 end) as DEMOS_HELD,
  sum(case when STAGE_NAME = 'CLOSED WON' then 1 else 0 end) as CLOSED_WON,
  sum(case when STAGE_NAME like 'CLOSED LOST%' then 1 else 0 end) as CLOSED_LOST
from f
group by 1,2
order by 1,2;
