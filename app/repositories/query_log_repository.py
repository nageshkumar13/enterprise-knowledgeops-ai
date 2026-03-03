from app.core.logging import get_logger
from app.core.snowflake import SnowflakeConnectionManager


class QueryLogRepository:
    def __init__(self, connection_manager: SnowflakeConnectionManager) -> None:
        self.connection_manager = connection_manager
        self.logger = get_logger(self.__class__.__name__)

    def try_log(
        self,
        query_text: str,
        top_k: int,
        response_time_ms: int,
        search_results_count: int,
        model_used: str,
        success: bool,
        error_message: str | None = None,
        user_id: str | None = None,
    ) -> None:
        sql = """
            INSERT INTO QUERY_LOG
            (
                USER_ID,
                QUERY_TEXT,
                TOP_K,
                RESPONSE_TIME_MS,
                SEARCH_RESULTS_COUNT,
                MODEL_USED,
                SUCCESS,
                ERROR_MESSAGE
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        try:
            with self.connection_manager.cursor() as (_, cursor):
                cursor.execute(
                    sql,
                    (
                        user_id,
                        query_text,
                        top_k,
                        response_time_ms,
                        search_results_count,
                        model_used,
                        success,
                        error_message,
                    ),
                )
        except Exception as exc:
            self.logger.warning("Query log write skipped: %s", exc)
