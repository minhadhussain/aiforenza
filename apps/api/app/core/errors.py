from fastapi import status


class OpenAIAPIError(Exception):
    def __init__(
        self,
        message: str,
        *,
        error_type: str,
        code: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.code = code
        self.status_code = status_code


def openai_error_payload(message: str, error_type: str, code: str) -> dict:
    return {
        "error": {
            "message": message,
            "type": error_type,
            "code": code,
        }
    }
