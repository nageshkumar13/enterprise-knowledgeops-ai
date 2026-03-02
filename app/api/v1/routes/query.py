from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.schemas.query_schema import QueryRequest, QueryResponse
from app.core.errors import ApplicationError
from app.dependencies import get_knowledge_service
from app.services.knowledge_service import KnowledgeService

router = APIRouter(prefix="/query", tags=["query"])


@router.post("", response_model=QueryResponse)
def query_documents(
    request: QueryRequest,
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
) -> QueryResponse:
    try:
        return knowledge_service.answer_query(question=request.question, limit=request.limit)
    except ApplicationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
