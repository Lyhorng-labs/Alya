
import logging
import re

import httpx
from pydantic import ValidationError
from app.ai.language import resolve_turn_language
from app.ai.personality import ALYA_SYSTEM_PROMPT
from app.config import settings
from app.schemas import AssistantReply


logger = logging.getLogger(__name__)


def detect_fallback_language(
    history: list[dict[str, str]],
    preferred_language: str,
) -> str:
    if preferred_language != "auto":
        return preferred_language

    latest_message = ""

    for message in reversed(history):
        if message["role"] == "user":
            latest_message = message["content"]
            break

    # Japanese Hiragana and Katakana
    if re.search(r"[\u3040-\u30ff]", latest_message):
        return "ja"

    # Chinese characters
    if re.search(r"[\u4e00-\u9fff]", latest_message):
        return "zh"

    return "en"


def parse_assistant_response(
    raw_response: str,
    preferred_language: str,
    history: list[dict[str, str]],
) -> AssistantReply:

    fallback_language = detect_fallback_language(
        history,
        preferred_language,
    )

    cleaned_response = re.sub(
        r"<think>.*?</think>",
        "",
        raw_response,
        flags=re.DOTALL,
    ).strip()

    start = cleaned_response.find("{")
    end = cleaned_response.rfind("}")

    if start != -1 and end > start:
        try:
            parsed = AssistantReply.model_validate_json(
                cleaned_response[start:end + 1]
            )

            if preferred_language != "auto":
                parsed = parsed.model_copy(
                    update={"language": preferred_language}
                )

            return parsed

        except ValidationError as exc:
            logger.warning(
                "Alya returned invalid structured JSON: %s",
                exc,
    )

    # Graceful fallback if the model doesn't follow
    # the requested JSON format.
    return AssistantReply(
        text=cleaned_response or (
            "I'm having a little trouble right now. "
            "Could you say that again?"
        ),
        language=fallback_language,
        emotion="neutral",
        expression="neutral",
        motion="idle",
    )


async def generate_ai_response(
    history: list[dict[str, str]],
    preferred_language: str = "auto",
) -> AssistantReply:
    resolved_language= resolve_turn_language(
        history=history,
        requested_language=preferred_language,
    )
    language_instructions = {
        "en": (
            "Respond entirely in English. "
            "Do not include Japanese or Chinese sentences."
        ),
        "zh": (
            "Respond entirely in Mandarin Chinese "
            "using Simplified Chinese characters."
        ),
        "ja": (
            "Respond entirely in natural Japanese."
        ),
    }

    messages = [
        {
             "role": "system",
            "content": (
                ALYA_SYSTEM_PROMPT
                + "\n\nSTRICT CURRENT RESPONSE LANGUAGE:\n"
                + language_instructions[resolved_language]
                + "\nThe language field must be: "
                + resolved_language
                + "\nFollow this instruction regardless of "
                  "the language used in earlier assistant messages."
            ),
        }
    ]

    for message in history[-20:]:
        if message["role"] not in ("user", "assistant"):
            continue

        messages.append({
            "role": message["role"],
            "content": message["content"],
        })

    payload = {
        "model": settings.llm_model,
        "messages": messages,
        "stream": False,
        "think": False,
        "format": AssistantReply.model_json_schema(),
        "options": {
            "temperature": 0.8,
            "num_predict": 450,
        },
    }

    url = (
        settings.llm_base_url.rstrip("/")
        + "/api/chat"
    )

    try:
        async with httpx.AsyncClient(
            timeout=settings.llm_timeout_seconds
        ) as http_client:

            response = await http_client.post(
                url,
                json=payload,
            )

            response.raise_for_status()

            result = response.json()

        assistant_message = result.get("message") or {}

        raw_response = (
            assistant_message.get("content") or ""
        ).strip()

        if not raw_response:
            logger.error(
                "Ollama returned empty content. "
                "Thinking field present: %s. "
                "Done reason: %s",
                bool(assistant_message.get("thinking")),
                result.get("done_reason"),
            )

            raise RuntimeError(
                "Ollama returned an empty assistant message. "
                "Check the model response and Ollama logs."
            )

        return parse_assistant_response(
            raw_response=raw_response,
            preferred_language=preferred_language,
            history=history,
        )

    except httpx.HTTPStatusError:
        logger.exception(
            "Ollama returned an HTTP error."
        )
        raise

    except httpx.RequestError:
        logger.exception(
            "Could not connect to Ollama."
        )
        raise
