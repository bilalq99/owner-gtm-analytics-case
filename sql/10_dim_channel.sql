create or replace transient table DEMO_DB.DE_CASE_BILALQURESHI0309_SCHEMA.DIM_CHANNEL as
select distinct
  SOURCE_CHANNEL                                         as CHANNEL_KEY,
  case
    when SOURCE_CHANNEL like '%FACEBOOK%' or SOURCE_CHANNEL like '%IG%' then 'PAID_SOCIAL'
    when SOURCE_CHANNEL like '%COLD CALL%'      then 'OUTBOUND'
    when SOURCE_CHANNEL like '%MEDIA%'          then 'MEDIA'
    when SOURCE_CHANNEL like '%YOUTUBE%'        then 'VIDEO'
    when SOURCE_CHANNEL like '%GOOGLE%'         then 'SEARCH'
    when SOURCE_CHANNEL like '%REFERRAL%'       then 'REFERRAL'
    when SOURCE_CHANNEL like '%WORD OF MOUTH%'  then 'WOM'
    else 'OTHER'
  end                                                    as CHANNEL_GROUP
from DEMO_DB.DE_CASE_BILALQURESHI0309_SCHEMA.STG2_OPPORTUNITIES
where SOURCE_CHANNEL is not null;
