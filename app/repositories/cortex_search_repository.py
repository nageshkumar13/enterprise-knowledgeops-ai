import json
from typing import Any

from app.core.config import get_settings
from app.core.snowflake import SnowflakeConnectionManager


class CortexSearchRepository:
    def __init__(self, connection_manager: SnowflakeConnectionManager) -> None:
        self.connection_manager = connection_manager
        self.settings = get_settings()

    def search(self, query: str, limit: int) -> list[dict[str, Any]]:
        sql_json_string_payload = """
            SELECT
                SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
                    %s,
                    %s
                ) AS SEARCH_RESULT
        """
        payload_json = json.dumps(
            {
                "query": query,
                "columns": ["DOC_ID", "PAGE_NUMBER", "CHUNK_TEXT"],
                "limit": limit,
            }
        )
        with self.connection_manager.cursor() as (_, cursor):
            try:
                cursor.execute(sql_json_string_payload, (self.settings.search_service_fqn, payload_json))
            except Exception as exc:
                message = str(exc)
                normalized = message.upper()
                if "390404" in normalized or "DOES NOT EXIST OR ACCESS IS NOT AUTHORIZED" in normalized:
                    raise RuntimeError(
                        "Cortex Search Service is missing or not authorized for the configured role. "
                        f"service={self.settings.search_service_fqn}. "
                        "Create/verify the service and grant USAGE to the app role."
                    ) from exc
                raise
            row = cursor.fetchone()

        if not row or not row.get("SEARCH_RESULT"):
            return []

        payload = row["SEARCH_RESULT"]
        if isinstance(payload, str):
            parsed = json.loads(payload)
        else:
            parsed = payload
        return parsed.get("results", [])
