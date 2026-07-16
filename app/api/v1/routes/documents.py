from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.v1.schemas.document_schema import UploadDocumentResponse
from app.core.errors import ApplicationError
from app.dependencies import get_document_service
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=UploadDocumentResponse)
def upload_document(
    file: UploadFile = File(...),
    document_service: DocumentService = Depends(get_document_service),
) -> UploadDocumentResponse:
    try:
        return document_service.upload_document(file=file)
    except ApplicationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
