-- =====================================================
-- 05_cortex_search_service.sql
-- Creates semantic search index
-- =====================================================

USE DATABASE KNOWLEDGEOPS_AI;
USE SCHEMA DOCS;


CREATE OR REPLACE CORTEX SEARCH SERVICE DOCS_SEARCH_SERVICE

ON CHUNK_TEXT

ATTRIBUTES DOC_ID, PAGE_NUMBER

WAREHOUSE = KNOWLEDGEOPS_WH

TARGET_LAG = '1 minute'

AS

SELECT

    CHUNK_TEXT,

    DOC_ID,

    PAGE_NUMBER

FROM DOCUMENT_CHUNKS;


-- Grant access

GRANT USAGE ON CORTEX SEARCH SERVICE DOCS_SEARCH_SERVICE
TO ROLE KNOWLEDGEOPS_APP_ROLE;


-- Verify

SHOW CORTEX SEARCH SERVICES;
