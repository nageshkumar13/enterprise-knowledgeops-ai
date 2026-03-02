from app.repositories.cortex_complete_repository import CortexCompleteRepository


class CortexCompleteService:
    def __init__(self, repository: CortexCompleteRepository) -> None:
        self.repository = repository

    def generate(self, prompt: str) -> str:
        return self.repository.generate_answer(prompt=prompt)
