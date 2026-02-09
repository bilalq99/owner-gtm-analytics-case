create or replace TABLE DEMO_DB.DE_CASE_BILALQURESHI0309_SCHEMA.STG_EXPENSES_ADVERTISING  as (

      SELECT TO_DATE('01-' || month, 'DD-MON-YY') AS month,
	 TRY_TO_NUMBER(
        REPLACE(
            REPLACE(
                REPLACE(ADVERTISING, 'US$', ''),
                CHAR(160), ''
            ),
            ',', '.'
        ),
        12, 2
    ) AS ADVERTISING
    from demo_db.gtm_case.expenses_advertising
);

