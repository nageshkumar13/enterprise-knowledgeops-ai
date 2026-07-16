from app.core.config import get_settings
from app.repositories.cortex_complete_repository import CortexCompleteRepository
from app.repositories.cortex_search_repository import CortexSearchRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.query_log_repository import QueryLogRepository


def _reset_settings(monkeypatch) -> object:
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.delenv("SNOWFLAKE_ACCOUNT", raising=False)
    monkeypatch.delenv("SNOWFLAKE_USER", raising=False)
    monkeypatch.delenv("SNOWFLAKE_PASSWORD", raising=False)
    get_settings.cache_clear()
    return get_settings()


def test_demo_mode_repositories_use_local_fallback(monkeypatch) -> None:
    settings = _reset_settings(monkeypatch)

    assert settings.demo_mode is True

    document_repository = DocumentRepository(connection_manager=object())
    stage_path = document_repository.upload_file_to_stage("/tmp/policy.pdf", "policy.pdf")
    assert "demo" in stage_path.lower()

    document_repository.insert_document_metadata("doc-1", "policy.pdf", stage_path, 100, "application/pdf", "UPLOADED")
    assert document_repository.parse_and_store_chunks("doc-1", "policy.pdf") == 1
    document_repository.update_document_status("doc-1", "PARSED")

    search_repository = CortexSearchRepository(connection_manager=object())
    search_results = search_repository.search("What is the policy?", 3)
    assert search_results[0]["DOC_ID"] == "demo-doc-1"

    complete_repository = CortexCompleteRepository(connection_manager=object())
    answer = complete_repository.generate_answer("Summarize the policy")
    assert "demo" in answer.lower()

    query_log_repository = QueryLogRepository(connection_manager=object())
    query_log_repository.try_log("What is the policy?", 3, 25, 1, "demo-model", True)
