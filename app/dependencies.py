from functools import lru_cache

from app.core.snowflake import SnowflakeConnectionManager
from app.repositories.cortex_complete_repository import CortexCompleteRepository
from app.repositories.cortex_search_repository import CortexSearchRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.query_log_repository import QueryLogRepository
from app.services.cortex_complete_service import CortexCompleteService
from app.services.cortex_search_service import CortexSearchService
from app.services.document_service import DocumentService
from app.services.knowledge_service import KnowledgeService


@lru_cache(maxsize=1)
def get_snowflake_connection_manager() -> SnowflakeConnectionManager:
    return SnowflakeConnectionManager()


@lru_cache(maxsize=1)
def get_document_repository() -> DocumentRepository:
    return DocumentRepository(get_snowflake_connection_manager())


@lru_cache(maxsize=1)
def get_cortex_search_repository() -> CortexSearchRepository:
    return CortexSearchRepository(get_snowflake_connection_manager())


@lru_cache(maxsize=1)
def get_cortex_complete_repository() -> CortexCompleteRepository:
    return CortexCompleteRepository(get_snowflake_connection_manager())


@lru_cache(maxsize=1)
def get_query_log_repository() -> QueryLogRepository:
    return QueryLogRepository(get_snowflake_connection_manager())


def get_document_service() -> DocumentService:
    return DocumentService(get_document_repository())


def get_knowledge_service() -> KnowledgeService:
    search_service = CortexSearchService(get_cortex_search_repository())
    complete_service = CortexCompleteService(get_cortex_complete_repository())
    query_log_repository = get_query_log_repository()
    return KnowledgeService(search_service, complete_service, query_log_repository)
