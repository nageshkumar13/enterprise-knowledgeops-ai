import os
import shutil
import tempfile
from pathlib import Path

from fastapi import UploadFile

from app.api.v1.schemas.document_schema import UploadDocumentData, UploadDocumentResponse
from app.core.errors import BadRequestError, SnowflakeOperationError
from app.core.logging import get_logger
from app.repositories.document_repository import DocumentRepository
from app.utils.file_utils import ensure_pdf, normalize_filename
from app.utils.id_generator import generate_document_id


class DocumentService:
    def __init__(self, document_repository: DocumentRepository) -> None:
        self.document_repository = document_repository
        self.logger = get_logger(self.__class__.__name__)

    def upload_document(self, file: UploadFile) -> UploadDocumentResponse:
        if not file.filename:
            raise BadRequestError("File name is required.")
        ensure_pdf(file.filename, file.content_type)

        doc_id = generate_document_id()
        normalized_name = normalize_filename(file.filename)
        stage_filename = f"{doc_id}_{normalized_name}"
        temp_file_path = ""
        temp_dir_path = ""

        self.logger.info("upload_start doc_id=%s file_name=%s", doc_id, normalized_name)
        try:
            temp_dir_path = tempfile.mkdtemp(prefix="knowledgeops_")
            temp_file_path = str(Path(temp_dir_path) / stage_filename)
            with open(temp_file_path, "wb") as tmp_file:
                file.file.seek(0)
                shutil.copyfileobj(file.file, tmp_file)

            file_size = int(Path(temp_file_path).stat().st_size)
            if file_size <= 0:
                raise BadRequestError("Uploaded file is empty.")

            stage_path = self.document_repository.upload_file_to_stage(temp_file_path, stage_filename)

            self.document_repository.insert_document_metadata(
                doc_id=doc_id,
                file_name=normalized_name,
                stage_path=stage_path,
                file_size=file_size,
                file_type="application/pdf",
                status="UPLOADED",
            )

            chunk_count = self.document_repository.parse_and_store_chunks(
                doc_id=doc_id,
                stage_filename=stage_path,
            )
            self.document_repository.update_document_status(doc_id, "PARSED")

            self.logger.info(
                "upload_success doc_id=%s chunks=%s stage_path=%s",
                doc_id,
                chunk_count,
                stage_path,
            )

            return UploadDocumentResponse(
                success=True,
                message="Document uploaded and parsed successfully.",
                data=UploadDocumentData(
                    doc_id=doc_id,
                    file_name=normalized_name,
                    stage_path=stage_path,
                    status="PARSED",
                    chunk_count=chunk_count,
                ),
            )
        except BadRequestError:
            raise
        except Exception as exc:
            self.logger.exception("upload_failure doc_id=%s error=%s", doc_id, exc)
            try:
                self.document_repository.update_document_status(doc_id, "FAILED")
            except Exception:
                pass
            raise SnowflakeOperationError(f"Document upload failed: {exc}") from exc
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            if temp_dir_path and os.path.isdir(temp_dir_path):
                shutil.rmtree(temp_dir_path, ignore_errors=True)
