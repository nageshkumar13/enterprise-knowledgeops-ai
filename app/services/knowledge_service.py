from app.api.v1.schemas.query_schema import QueryContextChunk, QueryResponse, QueryResponseData
from app.core.config import get_settings
from app.core.errors import BadRequestError, SnowflakeOperationError
from app.core.logging import get_logger
from app.repositories.query_log_repository import QueryLogRepository
from app.services.cortex_complete_service import CortexCompleteService
from app.services.cortex_search_service import CortexSearchService
from app.utils.prompt_builder import build_answer_prompt


class KnowledgeService:
    def __init__(
        self,
        search_service: CortexSearchService,
        complete_service: CortexCompleteService,
        query_log_repository: QueryLogRepository,
    ) -> None:
        self.search_service = search_service
        self.complete_service = complete_service
        self.query_log_repository = query_log_repository
        self.settings = get_settings()
        self.logger = get_logger(self.__class__.__name__)

    def answer_query(self, question: str, limit: int) -> QueryResponse:
        question = question.strip()
        if not question:
            raise BadRequestError("Question cannot be empty.")

        self.logger.info("query_start question=%s", question)
        try:
            chunks = self.search_service.search(question=question, limit=limit)
            self.logger.info("query_search_success question=%s hits=%s", question, len(chunks))

            prompt = build_answer_prompt(question=question, chunks=chunks)
            answer = self.complete_service.generate(prompt=prompt).strip()
            if not answer:
                answer = "No answer was generated from the available context."

            self.logger.info("query_generation_success question=%s", question)
            self.query_log_repository.try_log(question=question, answer=answer)

            return QueryResponse(
                success=True,
                message="Answer generated successfully.",
                data=QueryResponseData(
                    question=question,
                    answer=answer,
                    model=self.settings.cortex_model,
                    chunks=[
                        QueryContextChunk(
                            doc_id=str(item.get("DOC_ID") or ""),
                            page_number=(
                                int(item["PAGE_NUMBER"]) if item.get("PAGE_NUMBER") is not None else None
                            ),
                            chunk_text=str(item.get("CHUNK_TEXT") or ""),
                        )
                        for item in chunks
                    ],
                ),
            )
        except BadRequestError:
            raise
        except Exception as exc:
            raise SnowflakeOperationError(f"Query processing failed: {exc}") from exc
