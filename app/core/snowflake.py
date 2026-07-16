import time
from contextlib import contextmanager
from typing import Any, Generator, Tuple

from app.core.config import get_settings
from app.core.logging import get_logger


class SnowflakeConnectionManager:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.settings.validate_snowflake_credentials()
        self._connector = None
        self.logger = get_logger(self.__class__.__name__)

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
        attempts = max(1, self.settings.snowflake_connect_retries)
        backoff_seconds = max(0, self.settings.snowflake_connect_backoff_seconds)
        last_exc: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                return connector.connect(
                    account=self.settings.snowflake_account,
                    user=self.settings.snowflake_user,
                    password=self.settings.snowflake_password,
                    role=self.settings.snowflake_role,
                    warehouse=self.settings.snowflake_warehouse,
                    database=self.settings.snowflake_database,
                    schema=self.settings.snowflake_schema,
                    ocsp_fail_open=self.settings.snowflake_ocsp_fail_open,
                    disable_ocsp_checks=self.settings.snowflake_disable_ocsp_checks,
                    login_timeout=max(1, self.settings.snowflake_login_timeout_seconds),
                    network_timeout=max(1, self.settings.snowflake_network_timeout_seconds),
                    autocommit=False,
                )
            except Exception as exc:
                last_exc = exc
                if attempt >= attempts:
                    break
                self.logger.warning(
                    "snowflake_connect_retry attempt=%s/%s error=%s",
                    attempt,
                    attempts,
                    exc,
                )
                if backoff_seconds > 0:
                    time.sleep(backoff_seconds * attempt)

        if last_exc is not None:
            raise last_exc
        raise RuntimeError("Unable to establish Snowflake connection.")

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
