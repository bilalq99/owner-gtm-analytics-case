***
# Owner.com — GTM Analytics Case (Snowflake-first)

Snowflake‑first data modeling for the Owner.com GTM case: **raw data** → **initial staging (STG)** → **typed staging (STG2)** → **conformed DIM/FACT** → **business marts** → **H1’24 CAC/LTV & funnel views** → **executive readout PDF**.

This repo shows how to turn raw case extracts into **trustworthy, self‑serve GTM metrics** (funnel, wins/losses, CAC/LTV) with a few clear business rules and data‑quality guard rails.

***

## Table of Contents

*   \#whats-in-this-repo
*   \#prerequisites
*   \#quick-start-run-in-order
*   \#data-model-overview
*   \#lifecycle--definitions-important
*   \#metrics-glossary
*   \#qa-checks
*   \#file-index
*   \#dashboards


***

## What’s in this repo

*   **`/sql`** – runnable Snowflake SQL, organized by dependency:
    *  STG1, (initial staging) STG2 (typed staging), DIM/FACT (conformed), MART (business‑ready), Views (H1, CAC/LTV), QA checks
*   **`/assets`** – *Executive Readout PDF*


***

## Prerequisites

*   A Snowflake account and a role with permission to `CREATE TABLE/VIEW` in your target **database/schema**
*   The case uses tables already loaded into Snowflake 

**Target namespace used in scripts**  
`DEMO_DB.DE_CASE_BILALQURESHI0309_SCHEMA`  

***

## Quick start (run in order)

In Snowflake **Worksheets**, run the files in this order:

```sql
-- 0) Session
sql/000_prereqs.sql
-- (Sets USE DATABASE/SCHEMA and H1’24 window variables)

-- 1) Initial staging to clean arrays, date formatting, and number formatting (STG1)
sql/001_stg_leads.sql
sql/002_stg_opportunities.sql
sql/003_stg_expenses_advertising.sql
sql/004_stg_expenses_salary_and_commissions.sql

-- 2) Typed staging (STG2)
sql/01_stg2_leads.sql
sql/02_stg2_opportunities.sql
sql/03_stg2_spend.sql

-- 3) Conformed dimensions
sql/10_dim_channel.sql
sql/11_dim_reason.sql

-- 4) Conformed facts
sql/20_fact_lead.sql
sql/21_fact_opportunity.sql
sql/22_fact_gtm_spend.sql

-- 45 Business marts
sql/30_mart_gtm_funnel_daily.sql
sql/31_mart_gtm_funnel_monthly.sql
sql/36_mart_cac_ltv.sql

-- 6) H1’24 convenience views
sql/32_mart_h1_funnel.sql
sql/33_mart_h1_wins_by_source.sql
sql/34_mart_h1_loss_reasons.sql
sql/35_mart_h1_spend_cac.sql

-- 7) QA checks (sanity)
sql/99_qa_checks.sql
```


***

## Data model overview

    Raw tables (already in Snowflake)
       ├── LEADS
       ├── OPPORTUNITIES
       ├── EXPENSES_ADVERTISING
       └── EXPENSES_SALARY_AND_COMMISSIONS
    STG_* (cleaned)
       ├── STG_LEADS
       ├── STG_OPPORTUNITIES
       ├── STG_EXPENSES_ADVERTISING
       └── STG_EXPENSES_SALARY_AND_COMMISSIONS

    STG2_* (typed, cleaned)
       ├── STG2_LEADS
       ├── STG2_OPPORTUNITIES
       └── STG2_SPEND

    Conformed layer
       ├── DIM_CHANNEL       (maps SOURCE_CHANNEL → CHANNEL_GROUP)
       ├── DIM_REASON        (loss reason grouping)
       ├── FACT_LEAD         (lead-level attributes, predicted sales)
       ├── FACT_OPPORTUNITY  (opportunity lifecycle dates, reason group)
       └── FACT_GTM_SPEND    (monthly ad + people spend)

    Business marts
       ├── MART_GTM_FUNNEL_DAILY
       ├── MART_GTM_FUNNEL_MONTHLY (view)
       └── MART_CAC_LTV            (monthly CAC/LTV aggregate)

    H1 views (for the case window, first half 2024)
       ├── MART_H1_FUNNEL
       ├── MART_H1_WINS_BY_SOURCE
       ├── MART_H1_LOSS_REASONS
       └── MART_H1_SPEND_CAC

***

## Lifecycle & definitions (important)

**Assignment rule**

> An **opportunity** is considered to start when a **demo is booked**.

We implement a business‑valid start date in `FACT_OPPORTUNITY`:

```sql
OPP_START_DATE := COALESCE(DEMO_SET_DATE, CREATED_DATE)
```

**Demo guard‑rails** (to match how the source fields are populated and prevent “Held > Set”):

*   **Demos Set**  = `DEMO_SET_DATE IS NOT NULL` **OR** `DEMO_HELD_DATE IS NOT NULL`  
    (Exports often include a timestamp for a scheduled demo even when the formal set date wasn’t filled.)
*   **Demos Held** = `DEMO_HELD_DATE IS NOT NULL` **AND** `LOSS_REASON_GROUP <> 'NO_SHOW'`  
    (Avoids counting scheduled no‑shows as held.)

These rules are embedded in **`MART_GTM_FUNNEL_*`** and any view that reports set/held counts.

***

## Metrics glossary

*   **Leads**: Count of `STG2_LEADS` by submission date in window.
*   **Opportunities (Opps)**: Count of `FACT_OPPORTUNITY` anchored by `OPP_START_DATE`.
*   **Demos Set**: Booked demo per guard‑rail definition.
*   **Demos Held**: Completed demo per guard‑rail definition.
*   **Closed Won / Lost**: Terminal stages in `FACT_OPPORTUNITY.STAGE_NAME`.
*   **Win rate (from demo held)**: `Closed Won / Demos Held` (same grain).
*   **Spend (H1)**: From `FACT_GTM_SPEND` → `TOTAL_SPEND` = Advertising + Inbound + Outbound comp.
*   **CAC (Naïve)**: Month (or H1) **company‑level spend** ÷ **wins** (no channel allocation yet).
*   **LTV (12‑month)**: `12 × ( 500 + 0.05 × predicted_monthly_sales )` from `FACT_LEAD.PREDICTED_SALES_WITH_OWNER`.
*   **LTV:CAC**: `Average LTV / CAC`.

> When channel-level spend tagging is added, swap **naïve CAC** for **true CAC by channel**.

***

## QA checks

Run `sql/99_qa_checks.sql` to verify:

1.  **Held ≤ Set** at all grains (e.g., monthly):

```sql
select * from MART_GTM_FUNNEL_MONTHLY where DEMOS_HELD > DEMOS_SET;
```

2.  **Why the guard exists** (scheduled time but labeled “No Demo Held”):

```sql
select count(*) as rows_time_but_no_demo
from STG2_OPPORTUNITIES
where DEMO_HELD_TS is not null
  and upper(coalesce(LOST_REASON,'')) like '%NO DEMO HELD%';
```

3.  **Lifecycle sanity** (opp start after created):

```sql
select count(*) as opp_start_lt_created
from FACT_OPPORTUNITY
where OPP_START_DATE < CREATED_DATE;
```

***

## File index

    sql/
      000_prereqs.sql
      001_stg_leads.sql
      002_stg_opportunities.sql
      003_stg_expenses_advertising.sql
      004_stg_expenses_salary_and_commissions.sql
      01_stg2_leads.sql
      02_stg2_opportunities.sql
      03_stg2_spend.sql
      10_dim_channel.sql
      11_dim_reason.sql
      20_fact_lead.sql
      21_fact_opportunity.sql
      22_fact_gtm_spend.sql
      30_mart_gtm_funnel_daily.sql
      31_mart_gtm_funnel_monthly.sql
      32_mart_h1_funnel.sql
      33_mart_h1_wins_by_source.sql
      34_mart_h1_loss_reasons.sql
      35_mart_h1_spend_cac.sql
      36_mart_cac_ltv.sql
      99_qa_checks.sql
      clean_str_array.sql

    assets/
      Owner_GTM_H1_2024_Executive_Readout_v2.pdf
      dashboard_screenshot.png

***

## Dashboards (Snowflake)

*   **Snowflake**: Create tiles that read from:
    *   `MART_GTM_FUNNEL_MONTHLY` (bar/line for Set/Held/Won),
    *   `MART_H1_WINS_BY_SOURCE` (bar by `SOURCE_CHANNEL` / `CHANNEL_GROUP`),
    *   `MART_H1_LOSS_REASONS` (bar by reason group),
    *   `MART_H1_SPEND_CAC` and `MART_CAC_LTV` (single value tiles for spend, CAC, LTV).

***

## Security & privacy

*   **No raw data** is stored in this repo.
*   No credentials, secrets, or private account details are included.
*   Object names can be parameterized if needed; adjust in `000_prereqs.sql`.
