create or replace view DEMO_DB.DE_CASE_BILALQURESHI0309_SCHEMA.MART_H1_SPEND_CAC as
with spend_h1 as (
  select sum(TOTAL_SPEND) as TOTAL_SPEND
  from DEMO_DB.DE_CASE_BILALQURESHI0309_SCHEMA.FACT_GTM_SPEND
  where MONTH_DATE between $h1_start and $h1_end
),
wins_h1 as (
  select count(*) as WINS
  from DEMO_DB.DE_CASE_BILALQURESHI0309_SCHEMA.FACT_OPPORTUNITY
  where STAGE_NAME = 'CLOSED WON'
    and CLOSE_DATE between $h1_start and $h1_end
)
select
  s.TOTAL_SPEND,
  w.WINS,
  case when w.WINS=0 then null else s.TOTAL_SPEND / w.WINS end as NAIVE_CAC
from spend_h1 s cross join wins_h1 w;
