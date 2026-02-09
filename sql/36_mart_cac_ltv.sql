create or replace transient table DEMO_DB.DE_CASE_BILALQURESHI0309_SCHEMA.MART_CAC_LTV as
with won as (
  select
    f.CLOSE_DATE                                        as MONTH_DATE,
    d.CHANNEL_GROUP,
    f.OPPORTUNITY_ID
  from DEMO_DB.DE_CASE_BILALQURESHI0309_SCHEMA.FACT_OPPORTUNITY f
  left join DEMO_DB.DE_CASE_BILALQURESHI0309_SCHEMA.DIM_CHANNEL d
         on f.SOURCE_CHANNEL = d.CHANNEL_KEY
  where f.STAGE_NAME = 'CLOSED WON'
),
rev as (
  select
    date_trunc('month', w.MONTH_DATE)                   as MONTH,
    w.CHANNEL_GROUP,
    l.LEAD_ID,
    500 + 0.05 * coalesce(l.PREDICTED_SALES_WITH_OWNER,0)      as EST_MONTHLY_REV,
    (500 + 0.05 * coalesce(l.PREDICTED_SALES_WITH_OWNER,0))*12 as EST_LTV_12M
  from won w
  left join DEMO_DB.DE_CASE_BILALQURESHI0309_SCHEMA.FACT_LEAD l
         on w.OPPORTUNITY_ID = l.CONVERTED_OPPORTUNITY_ID
),
spend as (
  select
    MONTH_DATE                                         as MONTH,
    ADVERTISING, INBOUND_COMP, OUTBOUND_COMP, TOTAL_SPEND
  from DEMO_DB.DE_CASE_BILALQURESHI0309_SCHEMA.FACT_GTM_SPEND
)
select
  r.MONTH,
  r.CHANNEL_GROUP,
  count(*)                                             as WINS,
  avg(r.EST_LTV_12M)                                   as AVG_LTV_12M,
  s.TOTAL_SPEND                                        as TOTAL_SPEND_MONTH,
  case when count(*)=0 then null else s.TOTAL_SPEND / count(*) end as NAIVE_CAC
from rev r
left join spend s on r.MONTH = s.MONTH
group by 1,2,5
;
