create or replace transient table DEMO_DB.DE_CASE_BILALQURESHI0309_SCHEMA.STG2_LEADS as
select
  cast(LEAD_ID as string) as LEAD_ID,

  /* robust timestamp coercion (string-first try, else cast) */
  coalesce(try_to_timestamp_ntz(FORM_SUBMISSION_DATE::string),  cast(FORM_SUBMISSION_DATE  as timestamp_ntz)) as FORM_SUBMISSION_TS,
  coalesce(try_to_timestamp_ntz(FIRST_MEETING_BOOKED_DATE::string), cast(FIRST_MEETING_BOOKED_DATE as timestamp_ntz)) as FIRST_MEETING_BOOKED_TS,
  coalesce(try_to_timestamp_ntz(LAST_SALES_ACTIVITY_DATE::string),  cast(LAST_SALES_ACTIVITY_DATE  as timestamp_ntz)) as LAST_SALES_ACTIVITY_TS,

  coalesce(PREDICTED_SALES_WITH_OWNER, 0)         as PREDICTED_SALES_WITH_OWNER,
  upper(trim(STATUS))                              as STATUS,
  upper(trim(CONNECTED_WITH_DECISION_MAKER))       as CONNECTED_WITH_DM,
  upper(trim(MARKETPLACES_USED))                   as MARKETPLACES_USED_RAW,
  upper(trim(ONLINE_ORDERING_USED))                as ONLINE_ORDERING_RAW,
  upper(trim(CUISINE_TYPES))                       as CUISINE_RAW,
  coalesce(LOCATION_COUNT, 1)                      as LOCATION_COUNT,
  cast(CONVERTED_OPPORTUNITY_ID as string)         as CONVERTED_OPPORTUNITY_ID
from DEMO_DB.DE_CASE_BILALQURESHI0309_SCHEMA.STG_LEADS;
