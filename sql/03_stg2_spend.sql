create or replace transient table DEMO_DB.DE_CASE_BILALQURESHI0309_SCHEMA.STG2_SPEND as
with adv as (
  select date_trunc('month', cast(MONTH as date)) as MONTH_DATE,
         coalesce(ADVERTISING,0)                  as ADVERTISING
  from DEMO_DB.DE_CASE_BILALQURESHI0309_SCHEMA.STG_EXPENSES_ADVERTISING
),
comp as (
  select date_trunc('month', cast(MONTH as date)) as MONTH_DATE,
         coalesce(OUTBOUND_SALES_TEAM,0)          as OUTBOUND_COMP,
         coalesce(INBOUND_SALES_TEAM,0)           as INBOUND_COMP
  from DEMO_DB.DE_CASE_BILALQURESHI0309_SCHEMA.STG_EXPENSES_SALARY_AND_COMMISSIONS
)
select
  coalesce(a.MONTH_DATE, c.MONTH_DATE) as MONTH_DATE,
  coalesce(ADVERTISING,0)              as ADVERTISING,
  coalesce(OUTBOUND_COMP,0)            as OUTBOUND_COMP,
  coalesce(INBOUND_COMP,0)             as INBOUND_COMP,
  (coalesce(ADVERTISING,0) + coalesce(OUTBOUND_COMP,0) + coalesce(INBOUND_COMP,0)) as TOTAL_SPEND
from adv a
full outer join comp c using (MONTH_DATE);
