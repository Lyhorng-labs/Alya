from app.ai.llm import generate_ai_response
from app.schemas import AssistantReply


async def generate_reply(
    history: list[dict[str, str]],
    preferred_language: str,
) -> AssistantReply:

    return await generate_ai_response(
        history=history,
        preferred_language=preferred_language,
    )