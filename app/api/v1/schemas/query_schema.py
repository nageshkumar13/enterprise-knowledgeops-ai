from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    limit: int = Field(default=5, ge=1, le=20)


class QueryContextChunk(BaseModel):
    doc_id: str
    page_number: int | None = None
    chunk_text: str


class QueryResponseData(BaseModel):
    question: str
    answer: str
    model: str
    chunks: list[QueryContextChunk]


class QueryResponse(BaseModel):
    success: bool
    message: str
    data: QueryResponseData
