create or replace transient table DEMO_DB.DE_CASE_BILALQURESHI0309_SCHEMA.STG2_OPPORTUNITIES as
select
  cast(OPPORTUNITY_ID as string) as OPPORTUNITY_ID,
  upper(trim(STAGE_NAME))        as STAGE_NAME,
  upper(trim(LOST_REASON_C))     as LOST_REASON,
  upper(trim(HOW_DID_YOU_HEAR_ABOUT_US_C)) as SOURCE_CHANNEL,

  /* robust timestamp coercion */
  coalesce(try_to_timestamp_ntz(CREATED_DATE::string),  cast(CREATED_DATE  as timestamp_ntz)) as CREATED_TS,
  coalesce(try_to_timestamp_ntz(DEMO_SET_DATE::string), cast(DEMO_SET_DATE as timestamp_ntz)) as DEMO_SET_TS,
  coalesce(try_to_timestamp_ntz(DEMO_TIME::string),     cast(DEMO_TIME     as timestamp_ntz)) as DEMO_HELD_TS,
  coalesce(try_to_timestamp_ntz(CLOSE_DATE::string),    cast(CLOSE_DATE    as timestamp_ntz)) as CLOSE_TS,

  cast(ACCOUNT_ID as string)     as ACCOUNT_ID
from DEMO_DB.DE_CASE_BILALQURESHI0309_SCHEMA.STG_OPPORTUNITIES;
