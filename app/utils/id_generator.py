from uuid import uuid4


def generate_document_id() -> str:
    return str(uuid4())
