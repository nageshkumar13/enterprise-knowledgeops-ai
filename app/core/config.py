import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Enterprise KnowledgeOps AI")
    app_version: str = os.getenv("APP_VERSION", "1.0.0")
    api_prefix: str = os.getenv("API_PREFIX", "/api/v1")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    snowflake_account: str = os.getenv("SNOWFLAKE_ACCOUNT", "")
    snowflake_user: str = os.getenv("SNOWFLAKE_USER", "")
    snowflake_password: str = os.getenv("SNOWFLAKE_PASSWORD", "")
    snowflake_role: str = os.getenv("SNOWFLAKE_ROLE", "KNOWLEDGEOPS_APP_ROLE")
    snowflake_warehouse: str = os.getenv("SNOWFLAKE_WAREHOUSE", "KNOWLEDGEOPS_WH")
    snowflake_database: str = os.getenv("SNOWFLAKE_DATABASE", "KNOWLEDGEOPS_AI")
    snowflake_schema: str = os.getenv("SNOWFLAKE_SCHEMA", "DOCS")
    snowflake_stage: str = os.getenv("SNOWFLAKE_STAGE", "DOCS_STAGE")
    snowflake_search_service: str = os.getenv("SNOWFLAKE_SEARCH_SERVICE", "DOCS_SEARCH_SERVICE")

    cortex_model: str = os.getenv("CORTEX_MODEL", "claude-3-5-sonnet")
    query_result_limit: int = int(os.getenv("QUERY_RESULT_LIMIT", "5"))

    @property
    def stage_reference(self) -> str:
        if "." in self.snowflake_stage:
            return f"@{self.snowflake_stage}"
        return f"@{self.snowflake_database}.{self.snowflake_schema}.{self.snowflake_stage}"

    @property
    def search_service_fqn(self) -> str:
        if "." in self.snowflake_search_service:
            return self.snowflake_search_service
        return f"{self.snowflake_database}.{self.snowflake_schema}.{self.snowflake_search_service}"

    def validate_snowflake_credentials(self) -> None:
        required = {
            "SNOWFLAKE_ACCOUNT": self.snowflake_account,
            "SNOWFLAKE_USER": self.snowflake_user,
            "SNOWFLAKE_PASSWORD": self.snowflake_password,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            missing_joined = ", ".join(missing)
            raise ValueError(f"Missing required environment variables: {missing_joined}")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
