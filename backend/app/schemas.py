
from datetime import datetime
from typing import Literal
from uuid import UUID
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConversationOut(BaseModel):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageOut(BaseModel):
    id: UUID
    role: str
    content: str
    language: str
    emotion: str | None
    expression: str | None
    motion: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationDetail(ConversationOut):
    messages: list[MessageOut] = Field(default_factory=list)


class ChatInput(BaseModel):
    type: Literal["user_message"] = "user_message"

    content: str = Field(min_length=1, max_length=4000)

    language: Literal["auto", "en", "zh", "ja"] = "auto"

    @field_validator("content")
    @classmethod
    def clean_content(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Message cannot be empty.")

        return value


class AssistantReply(BaseModel):
    text: str = Field(min_length=1)

    language: Literal["en", "zh", "ja"]

    emotion: Literal[
        "neutral",
        "happy",
        "playful",
        "teasing",
        "affectionate",
        "embarrassed",
        "curious",
        "supportive",
        "surprised",
        "concerned",
        "confused",
    ] = "neutral"

    expression: Literal[
        "neutral",
        "smile",
        "smug",
        "blush",
        "happy",
        "thoughtful",
        "surprised",
        "concerned",
        "gentle",
    ] = "neutral"

    motion: Literal[
        "idle",
        "head_tilt",
        "nod",
        "bounce",
        "look_away",
        "sway",
    ] = "idle"
