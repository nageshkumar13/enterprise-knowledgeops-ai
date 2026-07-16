import re
import time
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

    @staticmethod
    def _validate_stage_file_path(stage_file_path: str) -> None:
        if not re.fullmatch(r"[A-Za-z0-9._/-]+", stage_file_path):
            raise ValueError("Invalid stage file path.")

    @staticmethod
    def _is_missing_updated_at_error(exc: Exception) -> bool:
        message = str(exc).upper()
        return "INVALID IDENTIFIER" in message and "UPDATED_AT" in message

    @staticmethod
    def _is_unknown_split_function_error(exc: Exception) -> bool:
        message = str(exc).upper()
        return (
            "UNKNOWN FUNCTION SPLIT_TEXT_RECURSIVE_CHARACTER" in message
            or "UNKNOWN FUNCTION SNOWFLAKE.CORTEX.SPLIT_TEXT_RECURSIVE_CHARACTER" in message
        )

    @staticmethod
    def _is_missing_chunk_id_error(exc: Exception) -> bool:
        message = str(exc).upper()
        return "INVALID IDENTIFIER" in message and "CHUNK_ID" in message

    @staticmethod
    def _is_remote_file_not_found_error(exc: Exception) -> bool:
        message = str(exc).upper()
        return "REMOTE FILE" in message and "WAS NOT FOUND" in message

    @staticmethod
    def _is_client_side_encryption_error(exc: Exception) -> bool:
        message = str(exc).upper()
        return "CLIENT SIDE ENCRYPTION" in message and "NOT SUPPORTED" in message

    def _stage_file_candidates(self, stage_filename: str) -> list[str]:
        normalized = stage_filename.strip()
        if normalized.startswith(self.settings.stage_reference):
            prefix = f"{self.settings.stage_reference}/"
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix) :]
            else:
                normalized = normalized[len(self.settings.stage_reference) :].lstrip("/")
        normalized = normalized.lstrip("/")
        self._validate_stage_file_path(normalized)

        stage_name = self.settings.snowflake_stage.split(".")[-1].strip('"').strip().lower()
        prefixed = f"{stage_name}/{normalized}" if stage_name else normalized
        if normalized.startswith(f"{stage_name}/"):
            candidates = [normalized]
        else:
            candidates = [normalized, prefixed]
        # Preserve order and remove duplicates.
        return list(dict.fromkeys(candidates))

    @staticmethod
    def _extract_stage_list_name(row: dict[str, object]) -> str | None:
        value = row.get("NAME") if isinstance(row, dict) else None
        if value is None and isinstance(row, dict):
            value = row.get("name")
        return str(value) if value else None

    def _list_stage_file_candidates(self, cursor: object, stage_filename: str) -> list[str]:
        leaf_name = stage_filename.split("/")[-1]
        escaped_name = re.escape(leaf_name)
        list_sql = f"LIST {self.settings.stage_reference} PATTERN='.*{escaped_name}$'"
        cursor.execute(list_sql)
        rows = cursor.fetchall() or []
        discovered: list[str] = []
        for row in rows:
            if isinstance(row, dict):
                name = self._extract_stage_list_name(row)
                if name:
                    discovered.append(name.lstrip("/"))
        return list(dict.fromkeys(discovered))

    @staticmethod
    def _extract_put_target(row: dict[str, object]) -> str | None:
        if not isinstance(row, dict):
            return None
        target = row.get("TARGET")
        if target is None:
            target = row.get("target")
        if target is None:
            return None
        return str(target).strip()

    @staticmethod
    def _get_chunk_count_with_cursor(cursor: object, doc_id: str) -> int:
        sql = "SELECT COUNT(*) AS TOTAL FROM DOCUMENT_CHUNKS WHERE DOC_ID = %s"
        cursor.execute(sql, (doc_id,))
        row = cursor.fetchone()
        if not row:
            return 0
        if isinstance(row, dict):
            return int(row.get("TOTAL") or 0)
        return int(row[0] if row else 0)

    def upload_file_to_stage(self, file_path: str, stage_filename: str) -> str:
        self._validate_stage_filename(stage_filename)
        normalized_path = Path(file_path).resolve().as_posix()
        stage_path = f"{self.settings.stage_reference}/{stage_filename}"
        put_sql = (
            f"PUT 'file://{normalized_path}' "
            f"{self.settings.stage_reference}/ "
            "AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
        )
        with self.connection_manager.cursor() as (_, cursor):
            cursor.execute(put_sql)
            put_rows = cursor.fetchall() or []
            for row in put_rows:
                put_target = self._extract_put_target(row)
                if not put_target:
                    continue
                normalized_target = put_target.lstrip("/")
                if put_target.startswith("@"):
                    if put_target.split("/")[-1] == stage_filename:
                        return put_target
                elif normalized_target.split("/")[-1] == stage_filename:
                    return f"{self.settings.stage_reference}/{normalized_target}"
            discovered = self._list_stage_file_candidates(cursor, stage_filename)
            if discovered:
                return f"{self.settings.stage_reference}/{discovered[0]}"
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
        sql_with_updated_at = """
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
        sql_without_updated_at = """
            INSERT INTO DOCUMENTS
            (
                DOC_ID,
                FILE_NAME,
                STAGE_PATH,
                FILE_SIZE,
                FILE_TYPE,
                STATUS,
                CREATED_AT
            )
            VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP())
        """
        with self.connection_manager.cursor() as (_, cursor):
            params = (doc_id, file_name, stage_path, file_size, file_type, status)
            try:
                cursor.execute(sql_with_updated_at, params)
            except Exception as exc:
                if not self._is_missing_updated_at_error(exc):
                    raise
                cursor.execute(sql_without_updated_at, params)

    def update_document_status(self, doc_id: str, status: str) -> None:
        sql_with_updated_at = """
            UPDATE DOCUMENTS
            SET STATUS = %s, UPDATED_AT = CURRENT_TIMESTAMP()
            WHERE DOC_ID = %s
        """
        sql_without_updated_at = """
            UPDATE DOCUMENTS
            SET STATUS = %s
            WHERE DOC_ID = %s
        """
        with self.connection_manager.cursor() as (_, cursor):
            try:
                cursor.execute(sql_with_updated_at, (status, doc_id))
            except Exception as exc:
                if not self._is_missing_updated_at_error(exc):
                    raise
                cursor.execute(sql_without_updated_at, (status, doc_id))

    def parse_and_store_chunks(self, doc_id: str, stage_filename: str) -> int:
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
                        OBJECT_CONSTRUCT('mode', 'LAYOUT', 'page_split', TRUE)
                    ) AS PARSED
            ),
            pages AS
            (
                SELECT
                    VALUE:index::NUMBER AS PAGE_NUMBER,
                    COALESCE(VALUE:content::STRING, VALUE:text::STRING) AS PAGE_TEXT
                FROM parsed_doc,
                LATERAL FLATTEN(INPUT => PARSED:pages)
            ),
            chunks AS
            (
                SELECT
                    PAGE_NUMBER,
                    SNOWFLAKE.CORTEX.SPLIT_TEXT_RECURSIVE_CHARACTER(
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
                CHUNK_ID,
                PAGE_NUMBER,
                CHUNK_TEXT
            )
            WITH parsed_doc AS
            (
                SELECT
                    AI_PARSE_DOCUMENT(
                        TO_FILE('{self.settings.stage_reference}', %s),
                        OBJECT_CONSTRUCT('mode', 'LAYOUT', 'page_split', TRUE)
                    ) AS PARSED
            ),
            final_chunks AS
            (
                SELECT
                    ROW_NUMBER() OVER (ORDER BY VALUE:index::NUMBER) AS CHUNK_ID,
                    VALUE:index::NUMBER AS PAGE_NUMBER,
                    COALESCE(VALUE:content::STRING, VALUE:text::STRING) AS CHUNK_TEXT
                FROM parsed_doc,
                LATERAL FLATTEN(INPUT => PARSED:pages)
            )
            SELECT
                %s AS DOC_ID,
                CHUNK_ID,
                PAGE_NUMBER,
                CHUNK_TEXT
            FROM final_chunks
            WHERE CHUNK_TEXT IS NOT NULL
              AND TRIM(CHUNK_TEXT) <> ''
        """
        parse_sql_without_chunk_id_legacy_table = f"""
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
                        OBJECT_CONSTRUCT('mode', 'LAYOUT', 'page_split', TRUE)
                    ) AS PARSED
            ),
            final_chunks AS
            (
                SELECT
                    VALUE:index::NUMBER AS PAGE_NUMBER,
                    COALESCE(VALUE:content::STRING, VALUE:text::STRING) AS CHUNK_TEXT
                FROM parsed_doc,
                LATERAL FLATTEN(INPUT => PARSED:pages)
            )
            SELECT
                %s AS DOC_ID,
                PAGE_NUMBER,
                CHUNK_TEXT
            FROM final_chunks
            WHERE CHUNK_TEXT IS NOT NULL
              AND TRIM(CHUNK_TEXT) <> ''
        """
        parse_sql_ocr_with_chunk_id = f"""
            INSERT INTO DOCUMENT_CHUNKS
            (
                DOC_ID,
                CHUNK_ID,
                PAGE_NUMBER,
                CHUNK_TEXT
            )
            WITH parsed_doc AS
            (
                SELECT
                    AI_PARSE_DOCUMENT(
                        TO_FILE('{self.settings.stage_reference}', %s),
                        OBJECT_CONSTRUCT('mode', 'OCR', 'page_split', TRUE)
                    ) AS PARSED
            ),
            final_chunks AS
            (
                SELECT
                    ROW_NUMBER() OVER (ORDER BY VALUE:index::NUMBER) AS CHUNK_ID,
                    VALUE:index::NUMBER AS PAGE_NUMBER,
                    COALESCE(VALUE:content::STRING, VALUE:text::STRING) AS CHUNK_TEXT
                FROM parsed_doc,
                LATERAL FLATTEN(INPUT => PARSED:pages)
            )
            SELECT
                %s AS DOC_ID,
                CHUNK_ID,
                PAGE_NUMBER,
                CHUNK_TEXT
            FROM final_chunks
            WHERE CHUNK_TEXT IS NOT NULL
              AND TRIM(CHUNK_TEXT) <> ''
        """
        parse_sql_ocr_legacy_table = f"""
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
                        OBJECT_CONSTRUCT('mode', 'OCR', 'page_split', TRUE)
                    ) AS PARSED
            ),
            final_chunks AS
            (
                SELECT
                    VALUE:index::NUMBER AS PAGE_NUMBER,
                    COALESCE(VALUE:content::STRING, VALUE:text::STRING) AS CHUNK_TEXT
                FROM parsed_doc,
                LATERAL FLATTEN(INPUT => PARSED:pages)
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
            last_remote_not_found_error: Exception | None = None

            for attempt in range(3):
                candidates = self._stage_file_candidates(stage_filename)
                try:
                    discovered = self._list_stage_file_candidates(cursor, stage_filename)
                    for candidate in discovered:
                        if candidate not in candidates:
                            candidates.insert(0, candidate)
                except Exception:
                    pass

                for candidate in candidates:
                    try:
                        cursor.execute(parse_sql_with_chunk_id, (candidate, doc_id))
                        count = self._get_chunk_count_with_cursor(cursor, doc_id)
                        if count > 0:
                            return count
                        try:
                            cursor.execute(parse_sql_ocr_with_chunk_id, (candidate, doc_id))
                        except Exception as ocr_exc:
                            if self._is_missing_chunk_id_error(ocr_exc):
                                cursor.execute(parse_sql_ocr_legacy_table, (candidate, doc_id))
                            else:
                                raise
                        count = self._get_chunk_count_with_cursor(cursor, doc_id)
                        if count > 0:
                            return count
                        return count
                    except Exception as exc:
                        if self._is_client_side_encryption_error(exc):
                            raise ValueError(
                                "Stage uses client-side encrypted files. "
                                "Set stage encryption to SNOWFLAKE_SSE, remove old stage files, and re-upload."
                            ) from exc
                        if self._is_unknown_split_function_error(exc):
                            try:
                                cursor.execute(parse_sql_without_chunk_id, (candidate, doc_id))
                                count = self._get_chunk_count_with_cursor(cursor, doc_id)
                                if count > 0:
                                    return count
                                try:
                                    cursor.execute(parse_sql_ocr_with_chunk_id, (candidate, doc_id))
                                except Exception as ocr_exc:
                                    if self._is_missing_chunk_id_error(ocr_exc):
                                        cursor.execute(parse_sql_ocr_legacy_table, (candidate, doc_id))
                                    else:
                                        raise
                                count = self._get_chunk_count_with_cursor(cursor, doc_id)
                                if count > 0:
                                    return count
                                return count
                            except Exception as fallback_exc:
                                if self._is_client_side_encryption_error(fallback_exc):
                                    raise ValueError(
                                        "Stage uses client-side encrypted files. "
                                        "Set stage encryption to SNOWFLAKE_SSE, remove old stage files, and re-upload."
                                    ) from fallback_exc
                                if self._is_remote_file_not_found_error(fallback_exc):
                                    last_remote_not_found_error = fallback_exc
                                    continue
                                if not self._is_missing_chunk_id_error(fallback_exc):
                                    raise
                                try:
                                    cursor.execute(
                                        parse_sql_without_chunk_id_legacy_table,
                                        (candidate, doc_id),
                                    )
                                    count = self._get_chunk_count_with_cursor(cursor, doc_id)
                                    if count > 0:
                                        return count
                                    cursor.execute(parse_sql_ocr_legacy_table, (candidate, doc_id))
                                    count = self._get_chunk_count_with_cursor(cursor, doc_id)
                                    if count > 0:
                                        return count
                                    return count
                                except Exception as legacy_exc:
                                    if self._is_client_side_encryption_error(legacy_exc):
                                        raise ValueError(
                                            "Stage uses client-side encrypted files. "
                                            "Set stage encryption to SNOWFLAKE_SSE, remove old stage files, and re-upload."
                                        ) from legacy_exc
                                    if self._is_remote_file_not_found_error(legacy_exc):
                                        last_remote_not_found_error = legacy_exc
                                        continue
                                    raise

                        if self._is_missing_chunk_id_error(exc):
                            try:
                                cursor.execute(parse_sql_without_chunk_id_legacy_table, (candidate, doc_id))
                                count = self._get_chunk_count_with_cursor(cursor, doc_id)
                                if count > 0:
                                    return count
                                cursor.execute(parse_sql_ocr_legacy_table, (candidate, doc_id))
                                count = self._get_chunk_count_with_cursor(cursor, doc_id)
                                if count > 0:
                                    return count
                                return count
                            except Exception as legacy_exc:
                                if self._is_client_side_encryption_error(legacy_exc):
                                    raise ValueError(
                                        "Stage uses client-side encrypted files. "
                                        "Set stage encryption to SNOWFLAKE_SSE, remove old stage files, and re-upload."
                                    ) from legacy_exc
                                if self._is_remote_file_not_found_error(legacy_exc):
                                    last_remote_not_found_error = legacy_exc
                                    continue
                                raise

                        if self._is_remote_file_not_found_error(exc):
                            last_remote_not_found_error = exc
                            continue

                        raise

                if attempt < 2 and last_remote_not_found_error is not None:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                break

            if last_remote_not_found_error is not None:
                raise last_remote_not_found_error
            raise ValueError(f"Remote stage file not found for '{stage_filename}'.")
        return self.get_chunk_count(doc_id)

    def get_chunk_count(self, doc_id: str) -> int:
        sql = "SELECT COUNT(*) AS TOTAL FROM DOCUMENT_CHUNKS WHERE DOC_ID = %s"
        with self.connection_manager.cursor() as (_, cursor):
            cursor.execute(sql, (doc_id,))
            row = cursor.fetchone()
        return int(row["TOTAL"] if row else 0)
