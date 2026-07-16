from dataclasses import dataclass


@dataclass
class DocumentRecord:
    doc_id: str
    file_name: str
    stage_path: str
    file_size: int
    file_type: str
    status: str
