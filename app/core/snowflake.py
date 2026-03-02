from contextlib import contextmanager
from typing import Any, Generator, Tuple

from app.core.config import get_settings


class SnowflakeConnectionManager:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.settings.validate_snowflake_credentials()
        self._connector = None

    def _get_connector(self) -> Any:
        if self._connector is None:
            try:
                import snowflake.connector as connector
            except ModuleNotFoundError as exc:
                raise RuntimeError(
                    "snowflake-connector-python is required for Snowflake operations."
                ) from exc
            self._connector = connector
        return self._connector

    def get_connection(self) -> Any:
        connector = self._get_connector()
        return connector.connect(
            account=self.settings.snowflake_account,
            user=self.settings.snowflake_user,
            password=self.settings.snowflake_password,
            role=self.settings.snowflake_role,
            warehouse=self.settings.snowflake_warehouse,
            database=self.settings.snowflake_database,
            schema=self.settings.snowflake_schema,
            autocommit=False,
        )

    @contextmanager
    def cursor(self) -> Generator[Tuple[Any, Any], None, None]:
        connection = self.get_connection()
        connector = self._get_connector()
        cursor = connection.cursor(connector.DictCursor)
        try:
            yield connection, cursor
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()
