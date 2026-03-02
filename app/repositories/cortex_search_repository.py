import json
from typing import Any

from app.core.config import get_settings
from app.core.snowflake import SnowflakeConnectionManager


class CortexSearchRepository:
    def __init__(self, connection_manager: SnowflakeConnectionManager) -> None:
        self.connection_manager = connection_manager
        self.settings = get_settings()

    def search(self, query: str, limit: int) -> list[dict[str, Any]]:
        sql = """
            SELECT
                SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
                    %s,
                    TO_JSON(
                        OBJECT_CONSTRUCT(
                            'query', %s,
                            'columns', ARRAY_CONSTRUCT('DOC_ID', 'PAGE_NUMBER', 'CHUNK_TEXT'),
                            'limit', %s
                        )
                    )
                ) AS SEARCH_RESULT
        """
        with self.connection_manager.cursor() as (_, cursor):
            cursor.execute(sql, (self.settings.search_service_fqn, query, limit))
            row = cursor.fetchone()

        if not row or not row.get("SEARCH_RESULT"):
            return []

        payload = row["SEARCH_RESULT"]
        if isinstance(payload, str):
            parsed = json.loads(payload)
        else:
            parsed = payload
        return parsed.get("results", [])
