from typing import Iterable, Mapping


def build_answer_prompt(question: str, chunks: Iterable[Mapping[str, object]]) -> str:
    context_lines: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        doc_id = chunk.get("DOC_ID", "unknown")
        page = chunk.get("PAGE_NUMBER", "unknown")
        text = chunk.get("CHUNK_TEXT", "")
        context_lines.append(f"[{index}] doc={doc_id} page={page}\n{text}")

    context_block = "\n\n".join(context_lines) if context_lines else "No supporting context found."
    return (
        "You are a KnowledgeOps assistant.\n"
        "Answer using only the provided context.\n"
        "If context is insufficient, explicitly say so.\n\n"
        f"Question:\n{question}\n\n"
        f"Context:\n{context_block}\n\n"
        "Provide a concise answer and cite context item numbers used."
    )
