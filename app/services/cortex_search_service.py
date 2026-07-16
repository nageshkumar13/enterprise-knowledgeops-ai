from typing import Any

from app.repositories.cortex_search_repository import CortexSearchRepository


class CortexSearchService:
    def __init__(self, repository: CortexSearchRepository) -> None:
        self.repository = repository

    def search(self, question: str, limit: int) -> list[dict[str, Any]]:
        raw_results = self.repository.search(query=question, limit=limit)
        normalized: list[dict[str, Any]] = []
        for item in raw_results:
            normalized.append(
                {
                    "DOC_ID": item.get("DOC_ID") or item.get("doc_id"),
                    "PAGE_NUMBER": item.get("PAGE_NUMBER") or item.get("page_number"),
                    "CHUNK_TEXT": item.get("CHUNK_TEXT")
                    or item.get("chunk_text")
                    or item.get("text")
                    or "",
                }
            )
        return normalized
