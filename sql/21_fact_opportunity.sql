create or replace transient table DEMO_DB.DE_CASE_BILALQURESHI0309_SCHEMA.FACT_OPPORTUNITY as
select
  o.OPPORTUNITY_ID,
  o.ACCOUNT_ID,
  o.STAGE_NAME,
  o.SOURCE_CHANNEL,
  o.CREATED_TS::date   as CREATED_DATE,
  o.DEMO_SET_TS::date  as DEMO_SET_DATE,     -- demo booked
  o.DEMO_HELD_TS::date as DEMO_HELD_DATE,    -- scheduled/held timestamp (guarded in marts)
  o.CLOSE_TS::date     as CLOSE_DATE,

  /* assignment rule anchor */
  coalesce(o.DEMO_SET_TS::date, o.CREATED_TS::date) as OPP_START_DATE,

  coalesce(r.REASON_GROUP, 'OTHER') as LOSS_REASON_GROUP
from DEMO_DB.DE_CASE_BILALQURESHI0309_SCHEMA.STG2_OPPORTUNITIES o
left join DEMO_DB.DE_CASE_BILALQURESHI0309_SCHEMA.DIM_REASON r
  on o.LOST_REASON = r.REASON_KEY;
