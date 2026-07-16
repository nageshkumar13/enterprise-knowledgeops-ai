from pydantic import BaseModel, Field


class UploadDocumentData(BaseModel):
    doc_id: str = Field(..., description="Generated document identifier")
    file_name: str
    stage_path: str
    status: str
    chunk_count: int


class UploadDocumentResponse(BaseModel):
    success: bool
    message: str
    data: UploadDocumentData
