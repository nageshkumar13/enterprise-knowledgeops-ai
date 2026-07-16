from app.api.v1.schemas.query_schema import QueryRequest


def test_query_request_defaults_limit() -> None:
    payload = QueryRequest(question="Summarize policy")
    assert payload.limit == 5
