from app.core.config import get_settings
from app.core.snowflake import SnowflakeConnectionManager


class CortexCompleteRepository:
    def __init__(self, connection_manager: SnowflakeConnectionManager) -> None:
        self.connection_manager = connection_manager
        self.settings = get_settings()

    def generate_answer(self, prompt: str) -> str:
        primary_sql = "SELECT AI_COMPLETE(%s, %s) AS ANSWER"
        fallback_sql = "SELECT SNOWFLAKE.CORTEX.COMPLETE(%s, %s) AS ANSWER"

        try:
            with self.connection_manager.cursor() as (_, cursor):
                cursor.execute(primary_sql, (self.settings.cortex_model, prompt))
                row = cursor.fetchone()
                return str(row["ANSWER"]) if row and row.get("ANSWER") else ""
        except Exception:
            with self.connection_manager.cursor() as (_, cursor):
                cursor.execute(fallback_sql, (self.settings.cortex_model, prompt))
                row = cursor.fetchone()
                return str(row["ANSWER"]) if row and row.get("ANSWER") else ""
