-- =====================================================
-- 02_stage.sql
-- Creates internal stage for document uploads
-- =====================================================

USE DATABASE KNOWLEDGEOPS_AI;
USE SCHEMA DOCS;


-- Internal stage for PDF storage.
-- SNOWFLAKE_SSE is required for AI_PARSE_DOCUMENT compatibility.
-- NOTE: CREATE OR REPLACE will clear previously staged files.
CREATE OR REPLACE STAGE DOCS_STAGE
ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE')
DIRECTORY = (ENABLE = TRUE);


-- Grant stage access to application role
GRANT READ ON STAGE DOCS_STAGE
TO ROLE KNOWLEDGEOPS_APP_ROLE;

GRANT WRITE ON STAGE DOCS_STAGE
TO ROLE KNOWLEDGEOPS_APP_ROLE;


-- Verify
SHOW STAGES LIKE 'DOCS_STAGE';
