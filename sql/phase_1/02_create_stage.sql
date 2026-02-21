-- =====================================================
-- 03_create_document_tables.sql
-- Document metadata and chunk storage
-- =====================================================

USE DATABASE KNOWLEDGEOPS_AI;
USE SCHEMA DOCS;


-- =====================================================
-- DOCUMENTS TABLE
-- Stores uploaded document metadata
-- =====================================================

CREATE OR REPLACE TABLE DOCUMENTS (

    DOC_ID STRING PRIMARY KEY,

    FILE_NAME STRING,

    STAGE_PATH STRING,

    FILE_SIZE NUMBER,

    FILE_TYPE STRING,

    UPLOADED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),

    STATUS STRING,

    CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),

    UPDATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()

);


-- =====================================================
-- DOCUMENT_CHUNKS TABLE
-- Stores chunks used for Cortex Search indexing
-- =====================================================

CREATE OR REPLACE TABLE DOCUMENT_CHUNKS (

    DOC_ID STRING,

    CHUNK_ID NUMBER,

    CHUNK_TEXT STRING,

    PAGE_NUMBER NUMBER,

    CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),

    PRIMARY KEY (DOC_ID, CHUNK_ID)

);


-- Enable change tracking (required for Cortex Search)

ALTER TABLE DOCUMENT_CHUNKS
SET CHANGE_TRACKING = TRUE;


-- =====================================================
-- Verify
-- =====================================================

SHOW TABLES IN SCHEMA KNOWLEDGEOPS_AI.DOCS;