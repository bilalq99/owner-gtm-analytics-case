-- Held should never exceed Set (after guard-rails)
select * from DEMO_DB.DE_CASE_BILALQURESHI0309_SCHEMA.MART_GTM_FUNNEL_MONTHLY
where DEMOS_HELD > DEMOS_SET;

-- Why the guard exists: demo time present but explicitly "No Demo Held"
select count(*) as rows_time_but_no_demo
from DEMO_DB.DE_CASE_BILALQURESHI0309_SCHEMA.STG2_OPPORTUNITIES
where DEMO_HELD_TS is not null
  and upper(coalesce(LOST_REASON,'')) like '%NO DEMO HELD%';

-- Lifecycle sanity: opp start should be on/after created date
select count(*) as opp_start_lt_created
from DEMO_DB.DE_CASE_BILALQURESHI0309_SCHEMA.FACT_OPPORTUNITY
where OPP_START_DATE < CREATED_DATE;
