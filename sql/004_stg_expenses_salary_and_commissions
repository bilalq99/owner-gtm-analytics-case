CREATE OR REPLACE TABLE DEMO_DB.DE_CASE_BILALQURESHI0309_SCHEMA.STG_EXPENSES_SALARY_AND_COMMISSIONS AS

   SELECT TO_DATE('01-' || month, 'DD-MON-YY') AS month,


    TRY_TO_NUMBER(
        REPLACE(
            REPLACE(
                REPLACE(OUTBOUND_SALES_TEAM, 'US$', ''),
                CHAR(160), ''
            ),
            ',', '.'
        ),
        12, 2
    ) AS OUTBOUND_SALES_TEAM,
      TRY_TO_NUMBER(
        REPLACE(
            REPLACE(
                REPLACE(INBOUND_SALES_TEAM, 'US$', ''),
                CHAR(160), ''
            ),
            ',', '.'
        ),
        12, 2
    ) AS INBOUND_SALES_TEAM,
FROM DEMO_DB.GTM_CASE.EXPENSES_SALARY_AND_COMMISSIONS

