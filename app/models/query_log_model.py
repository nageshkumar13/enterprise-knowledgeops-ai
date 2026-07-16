from dataclasses import dataclass


@dataclass
class QueryResult:
    question: str
    answer: str
