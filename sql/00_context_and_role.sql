-- =====================================================
-- 00_context_and_role.sql
-- Foundation setup for KnowledgeOps AI
-- Run as ACCOUNTADMIN
-- =====================================================

-- Step 1 — Create Application Role

CREATE ROLE IF NOT EXISTS KNOWLEDGEOPS_APP_ROLE;


-- Step 2 — Create Warehouse

CREATE WAREHOUSE IF NOT EXISTS KNOWLEDGEOPS_WH
WAREHOUSE_SIZE = 'SMALL'
AUTO_SUSPEND = 60
AUTO_RESUME = TRUE
INITIALLY_SUSPENDED = TRUE;


-- Step 3 — Grant Warehouse access

GRANT USAGE ON WAREHOUSE KNOWLEDGEOPS_WH
TO ROLE KNOWLEDGEOPS_APP_ROLE;

GRANT OPERATE ON WAREHOUSE KNOWLEDGEOPS_WH
TO ROLE KNOWLEDGEOPS_APP_ROLE;


-- Step 4 — Grant Cortex permissions

GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER
TO ROLE KNOWLEDGEOPS_APP_ROLE;


-- Step 5 — Verify Role

SHOW ROLES LIKE 'KNOWLEDGEOPS_APP_ROLE';


-- Step 6 — Verify Warehouse

SHOW WAREHOUSES LIKE 'KNOWLEDGEOPS_WH';
