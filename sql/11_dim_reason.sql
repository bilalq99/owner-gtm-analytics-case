create or replace transient table DEMO_DB.DE_CASE_BILALQURESHI0309_SCHEMA.DIM_REASON as
select distinct
  LOST_REASON                                            as REASON_KEY,
  case
    when LOST_REASON like '%NO DEMO HELD%'                                    then 'NO_SHOW'
    when LOST_REASON like '%NO DECISION%' or LOST_REASON like '%NON-RESPONSIVE%' then 'NO_DECISION'
    when LOST_REASON like '%PRICE%'                                           then 'PRICE'
    when LOST_REASON like '%POS%'                                             then 'POS_INTEGRATION'
    when LOST_REASON like '%MISSING FEATURES%'                                 then 'FEATURE_GAP'
    when LOST_REASON like '%NOT A DECISION MAKER%'                             then 'NON_DM'
    when LOST_REASON like '%BAD FIT%'                                          then 'BAD_FIT'
    when LOST_REASON like '%LOST TO COMPETITOR%'                               then 'COMPETITOR'
    else 'OTHER'
  end                                                    as REASON_GROUP
from DEMO_DB.DE_CASE_BILALQURESHI0309_SCHEMA.STG2_OPPORTUNITIES
where LOST_REASON is not null;
