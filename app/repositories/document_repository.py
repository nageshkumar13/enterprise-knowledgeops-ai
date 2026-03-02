import re
from pathlib import Path

from app.core.config import get_settings
from app.core.snowflake import SnowflakeConnectionManager


class DocumentRepository:
    def __init__(self, connection_manager: SnowflakeConnectionManager) -> None:
        self.connection_manager = connection_manager
        self.settings = get_settings()

    @staticmethod
    def _validate_stage_filename(stage_filename: str) -> None:
        if not re.fullmatch(r"[A-Za-z0-9._-]+", stage_filename):
            raise ValueError("Invalid stage filename.")

    def upload_file_to_stage(self, file_path: str, stage_filename: str) -> str:
        self._validate_stage_filename(stage_filename)
        normalized_path = Path(file_path).resolve().as_posix()
        stage_path = f"{self.settings.stage_reference}/{stage_filename}"
        put_sql = (
            f"PUT 'file://{normalized_path}' "
            f"{stage_path} "
            "AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
        )
        with self.connection_manager.cursor() as (_, cursor):
            cursor.execute(put_sql)
        return stage_path

    def insert_document_metadata(
        self,
        doc_id: str,
        file_name: str,
        stage_path: str,
        file_size: int,
        file_type: str,
        status: str,
    ) -> None:
        sql = """
            INSERT INTO DOCUMENTS
            (
                DOC_ID,
                FILE_NAME,
                STAGE_PATH,
                FILE_SIZE,
                FILE_TYPE,
                STATUS,
                CREATED_AT,
                UPDATED_AT
            )
            VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP())
        """
        with self.connection_manager.cursor() as (_, cursor):
            cursor.execute(sql, (doc_id, file_name, stage_path, file_size, file_type, status))

    def update_document_status(self, doc_id: str, status: str) -> None:
        sql = """
            UPDATE DOCUMENTS
            SET STATUS = %s, UPDATED_AT = CURRENT_TIMESTAMP()
            WHERE DOC_ID = %s
        """
        with self.connection_manager.cursor() as (_, cursor):
            cursor.execute(sql, (status, doc_id))

    def parse_and_store_chunks(self, doc_id: str, stage_filename: str) -> int:
        self._validate_stage_filename(stage_filename)
        parse_sql_with_chunk_id = f"""
            INSERT INTO DOCUMENT_CHUNKS
            (
                DOC_ID,
                CHUNK_ID,
                CHUNK_TEXT,
                PAGE_NUMBER
            )
            WITH parsed_doc AS
            (
                SELECT
                    AI_PARSE_DOCUMENT(
                        TO_FILE('{self.settings.stage_reference}', %s),
                        OBJECT_CONSTRUCT('mode', 'LAYOUT')
                    ) AS PARSED
            ),
            pages AS
            (
                SELECT
                    VALUE:index::NUMBER AS PAGE_NUMBER,
                    VALUE:text::STRING AS PAGE_TEXT
                FROM parsed_doc,
                LATERAL FLATTEN(INPUT => PARSED:pages)
            ),
            chunks AS
            (
                SELECT
                    PAGE_NUMBER,
                    SPLIT_TEXT_RECURSIVE_CHARACTER(
                        PAGE_TEXT,
                        'plain_text',
                        1500,
                        200
                    ) AS CHUNK_ARRAY
                FROM pages
            ),
            final_chunks AS
            (
                SELECT
                    ROW_NUMBER() OVER (ORDER BY PAGE_NUMBER, INDEX) AS CHUNK_ID,
                    PAGE_NUMBER,
                    VALUE::STRING AS CHUNK_TEXT
                FROM chunks,
                LATERAL FLATTEN(INPUT => CHUNK_ARRAY)
            )
            SELECT
                %s AS DOC_ID,
                CHUNK_ID,
                CHUNK_TEXT,
                PAGE_NUMBER
            FROM final_chunks
            WHERE CHUNK_TEXT IS NOT NULL
              AND TRIM(CHUNK_TEXT) <> ''
        """
        parse_sql_without_chunk_id = f"""
            INSERT INTO DOCUMENT_CHUNKS
            (
                DOC_ID,
                PAGE_NUMBER,
                CHUNK_TEXT
            )
            WITH parsed_doc AS
            (
                SELECT
                    AI_PARSE_DOCUMENT(
                        TO_FILE('{self.settings.stage_reference}', %s),
                        OBJECT_CONSTRUCT('mode', 'LAYOUT')
                    ) AS PARSED
            ),
            pages AS
            (
                SELECT
                    VALUE:index::NUMBER AS PAGE_NUMBER,
                    VALUE:text::STRING AS PAGE_TEXT
                FROM parsed_doc,
                LATERAL FLATTEN(INPUT => PARSED:pages)
            ),
            chunks AS
            (
                SELECT
                    PAGE_NUMBER,
                    SPLIT_TEXT_RECURSIVE_CHARACTER(
                        PAGE_TEXT,
                        'plain_text',
                        1500,
                        200
                    ) AS CHUNK_ARRAY
                FROM pages
            ),
            final_chunks AS
            (
                SELECT
                    PAGE_NUMBER,
                    VALUE::STRING AS CHUNK_TEXT
                FROM chunks,
                LATERAL FLATTEN(INPUT => CHUNK_ARRAY)
            )
            SELECT
                %s AS DOC_ID,
                PAGE_NUMBER,
                CHUNK_TEXT
            FROM final_chunks
            WHERE CHUNK_TEXT IS NOT NULL
              AND TRIM(CHUNK_TEXT) <> ''
        """
        with self.connection_manager.cursor() as (_, cursor):
            try:
                cursor.execute(parse_sql_with_chunk_id, (stage_filename, doc_id))
            except Exception:
                cursor.execute(parse_sql_without_chunk_id, (stage_filename, doc_id))
        return self.get_chunk_count(doc_id)

    def get_chunk_count(self, doc_id: str) -> int:
        sql = "SELECT COUNT(*) AS TOTAL FROM DOCUMENT_CHUNKS WHERE DOC_ID = %s"
        with self.connection_manager.cursor() as (_, cursor):
            cursor.execute(sql, (doc_id,))
            row = cursor.fetchone()
        return int(row["TOTAL"] if row else 0)
