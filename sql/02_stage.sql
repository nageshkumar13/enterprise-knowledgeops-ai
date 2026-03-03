-- =====================================================
-- 02_stage.sql
-- Creates internal stage for document uploads
-- =====================================================

USE DATABASE KNOWLEDGEOPS_AI;
USE SCHEMA DOCS;


-- Internal stage for PDF storage.
-- SNOWFLAKE_SSE is required for AI_PARSE_DOCUMENT compatibility.
CREATE STAGE IF NOT EXISTS DOCS_STAGE
ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE')
DIRECTORY = (ENABLE = TRUE);


-- Grant stage access to application role
GRANT READ ON STAGE DOCS_STAGE
TO ROLE KNOWLEDGEOPS_APP_ROLE;

GRANT WRITE ON STAGE DOCS_STAGE
TO ROLE KNOWLEDGEOPS_APP_ROLE;


-- Verify
SHOW STAGES LIKE 'DOCS_STAGE';
