create or replace view DEMO_DB.DE_CASE_BILALQURESHI0309_SCHEMA.MART_H1_FUNNEL as
with f as (
  select
    fo.OPP_START_DATE::date as dt,
    fo.DEMO_SET_DATE,
    fo.DEMO_HELD_DATE,
    fo.STAGE_NAME,
    fo.LOSS_REASON_GROUP
  from DEMO_DB.DE_CASE_BILALQURESHI0309_SCHEMA.FACT_OPPORTUNITY fo
  where fo.OPP_START_DATE between $h1_start and $h1_end
),
flags as (
  select
    case when DEMO_SET_DATE is not null or DEMO_HELD_DATE is not null then 1 else 0 end as demo_set,
    case when DEMO_HELD_DATE is not null and coalesce(LOSS_REASON_GROUP,'OTHER') <> 'NO_SHOW' then 1 else 0 end as demo_held,
    case when STAGE_NAME = 'CLOSED WON' then 1 else 0 end as cw,
    case when STAGE_NAME like 'CLOSED LOST%' then 1 else 0 end as cl
  from f
)
select
  (select count(*) from DEMO_DB.DE_CASE_BILALQURESHI0309_SCHEMA.STG2_LEADS
    where FORM_SUBMISSION_TS::date between $h1_start and $h1_end) as LEADS,
  (select count(*) from f)                                        as OPPS,
  sum(demo_set)                                                   as DEMOS_SET,
  sum(demo_held)                                                  as DEMOS_HELD,
  sum(cw)                                                         as CLOSED_WON,
  sum(cl)                                                         as CLOSED_LOST,
  case when nullif(sum(demo_held),0) is null then null
       else sum(cw) / nullif(sum(demo_held),0)::float
  end as WIN_RATE_FROM_DEMO
from flags;
