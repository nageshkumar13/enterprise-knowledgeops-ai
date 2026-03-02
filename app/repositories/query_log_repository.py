from app.core.logging import get_logger
from app.core.snowflake import SnowflakeConnectionManager


class QueryLogRepository:
    def __init__(self, connection_manager: SnowflakeConnectionManager) -> None:
        self.connection_manager = connection_manager
        self.logger = get_logger(self.__class__.__name__)

    def try_log(self, question: str, answer: str) -> None:
        sql = """
            INSERT INTO QUERY_LOG
            (
                QUESTION,
                ANSWER,
                CREATED_AT
            )
            VALUES (%s, %s, CURRENT_TIMESTAMP())
        """
        try:
            with self.connection_manager.cursor() as (_, cursor):
                cursor.execute(sql, (question, answer))
        except Exception as exc:
            self.logger.warning("Query log write skipped: %s", exc)
