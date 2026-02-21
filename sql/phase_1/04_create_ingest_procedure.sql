-- =====================================================
-- 04_create_ingest_procedure.sql
-- Parses documents from stage and creates chunks
-- =====================================================

USE DATABASE KNOWLEDGEOPS_AI;
USE SCHEMA DOCS;


CREATE OR REPLACE PROCEDURE SP_INGEST_DOCS_FROM_STAGE()
RETURNS STRING
LANGUAGE SQL
EXECUTE AS OWNER
AS
$$

BEGIN

    -- Clear existing chunks

    DELETE FROM DOCUMENT_CHUNKS;


    -- Insert chunks from stage

    INSERT INTO DOCUMENT_CHUNKS
    (
        DOC_ID,
        CHUNK_ID,
        CHUNK_TEXT,
        PAGE_NUMBER
    )

    WITH parsed_docs AS (

        SELECT

            METADATA$FILENAME AS DOC_ID,

            AI_PARSE_DOCUMENT(
                TO_FILE('@DOCS_STAGE', METADATA$FILENAME),
                OBJECT_CONSTRUCT('mode', 'LAYOUT')
            ) AS parsed

        FROM DIRECTORY(@DOCS_STAGE)

    ),

    pages AS (

        SELECT

            DOC_ID,

            VALUE:index AS PAGE_NUMBER,

            VALUE:text::STRING AS PAGE_TEXT

        FROM parsed_docs,
        LATERAL FLATTEN(parsed:pages)

    ),

    chunks AS (

        SELECT

            DOC_ID,

            PAGE_NUMBER,

            SPLIT_TEXT_RECURSIVE_CHARACTER(
                PAGE_TEXT,
                'plain_text',
                1500,
                200
            ) AS chunk_array

        FROM pages

    ),

    final_chunks AS (

        SELECT

            DOC_ID,

            PAGE_NUMBER,

            VALUE::STRING AS CHUNK_TEXT,

            ROW_NUMBER() OVER
            (
                PARTITION BY DOC_ID
                ORDER BY PAGE_NUMBER
            ) AS CHUNK_ID

        FROM chunks,
        LATERAL FLATTEN(chunk_array)

    )

    SELECT
        DOC_ID,
        CHUNK_ID,
        CHUNK_TEXT,
        PAGE_NUMBER
    FROM final_chunks;


    RETURN 'INGEST SUCCESS';

END;

$$;


-- Verify

SHOW PROCEDURES LIKE 'SP_INGEST_DOCS_FROM_STAGE';