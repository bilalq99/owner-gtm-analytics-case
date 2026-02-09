CREATE OR REPLACE FUNCTION DEMO_DB.DE_CASE_BILALQURESHI0309_SCHEMA.CLEAN_STR_ARRAY("S" VARCHAR)
RETURNS ARRAY
LANGUAGE SQL
AS '
    CASE
      WHEN s IS NULL THEN ARRAY_CONSTRUCT()
      WHEN LOWER(TRIM(s)) IN (''nan'',''null'') THEN ARRAY_CONSTRUCT()
      WHEN REGEXP_REPLACE(s, ''\\\\s'', '''') IN (''[]'', ''[\\''\\'']'') THEN ARRAY_CONSTRUCT()
      ELSE COALESCE(
             TRY_PARSE_JSON(
               -- convert single quotes to double quotes to make it valid JSON
               REGEXP_REPLACE(TRIM(s), '''''''', ''"'')
             )::ARRAY,
             ARRAY_CONSTRUCT()
           )
    END
';
