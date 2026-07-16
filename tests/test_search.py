from app.utils.prompt_builder import build_answer_prompt


def test_build_answer_prompt_contains_question_and_context() -> None:
    prompt = build_answer_prompt(
        question="What is the SLA?",
        chunks=[{"DOC_ID": "doc-1", "PAGE_NUMBER": 2, "CHUNK_TEXT": "SLA is 99.9% uptime."}],
    )
    assert "What is the SLA?" in prompt
    assert "SLA is 99.9% uptime." in prompt
    assert "[1] doc=doc-1 page=2" in prompt
