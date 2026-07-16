class ApplicationError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class BadRequestError(ApplicationError):
    def __init__(self, message: str) -> None:
        super().__init__(message=message, status_code=400)


class SnowflakeOperationError(ApplicationError):
    def __init__(self, message: str) -> None:
        super().__init__(message=message, status_code=500)
