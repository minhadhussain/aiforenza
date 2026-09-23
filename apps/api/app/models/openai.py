from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="allow")
    role: str
    content: Any = None


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    # Public model IDs are identifiers, not query expressions. SQL text in message
    # content is still ordinary prompt data and must remain supported.
    model: str = Field(min_length=1, max_length=160, pattern=r"^[A-Za-z0-9._/-]+$")
    messages: list[ChatMessage] = Field(min_length=1)
    temperature: float | None = None
    max_tokens: int | None = Field(default=None, gt=0, strict=True)
    max_completion_tokens: int | None = Field(default=None, gt=0, strict=True)
    stream: bool = False
