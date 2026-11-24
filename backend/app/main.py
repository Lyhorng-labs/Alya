
from contextlib import asynccontextmanager
from uuid import UUID
from fastapi import (
    Depends,
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import (
    SessionFactory,
    close_database,
    engine,
    get_session,
)
from app.models import Base, Conversation, Message
from app.schemas import (
    ChatInput,
    ConversationDetail,
    ConversationOut,
    MessageOut,
)
from app.services.conversation import generate_reply
import logging
logger= logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Automatically create tables during local development.
    # Production will use Alembic migrations instead.
    if settings.app_env == "development":
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    yield

    await close_database()


app = FastAPI(
    title="Alya API",
    description="Backend for Alya AI Companion",
    version="0.1.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------
# Health checks
# ---------------------------

@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "healthy",
        "application": "Alya",
    }


@app.get("/api/v1/health/database")
async def database_health(
    session: AsyncSession = Depends(get_session),
):
    await session.execute(text("SELECT 1"))

    return {
        "status": "healthy",
        "database": "connected",
    }


# ---------------------------
# Conversations
# ---------------------------

@app.post(
    "/api/v1/conversations",
    response_model=ConversationOut,
)
async def create_conversation(
    session: AsyncSession = Depends(get_session),
):
    conversation = Conversation()

    session.add(conversation)

    await session.commit()
    await session.refresh(conversation)

    return conversation


@app.get(
    "/api/v1/conversations/{conversation_id}",
    response_model=ConversationDetail,
)
async def get_conversation(
    conversation_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id)
    )

    conversation = result.scalar_one_or_none()

    if conversation is None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    return conversation


# ---------------------------
# Real-time chat
# ---------------------------

@app.websocket(
    "/api/v1/ws/conversations/{conversation_id}"
)
@app.websocket(
    "/api/v1/ws/conversations/{conversation_id}"
)
async def conversation_websocket(
    websocket: WebSocket,
    conversation_id: UUID,
):
    origin = websocket.headers.get("origin")

    if origin and origin not in settings.allowed_origins:
        await websocket.close(code=1008)
        return

    await websocket.accept()

    try:
        async with SessionFactory() as session:

            conversation = await session.get(
                Conversation,
                conversation_id,
            )

            if conversation is None:
                await websocket.send_json({
                    "type": "error",
                    "message": "Conversation not found",
                })

                await websocket.close(code=1008)
                return

            while True:

                payload = await websocket.receive_json()

                try:
                    chat_input = ChatInput.model_validate(
                        payload
                    )

                except ValidationError:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Invalid message format",
                    })
                    continue

                # 1. Save the user's message.

                user_message = Message(
                    conversation_id=conversation_id,
                    role="user",
                    content=chat_input.content,
                    language=chat_input.language,
                )

                session.add(user_message)

                await session.commit()
                await session.refresh(user_message)

                await websocket.send_json({
                    "type": "user_message_saved",
                    "message": MessageOut.model_validate(
                        user_message
                    ).model_dump(mode="json"),
                })

                # 2. Retrieve recent conversation history.

                history_result = await session.execute(
                    select(Message)
                    .where(
                        Message.conversation_id == conversation_id
                    )
                    .order_by(Message.created_at.desc())
                    .limit(20)
                )

                history_messages = list(
                    reversed(history_result.scalars().all())
                )

                history = [
                    {
                        "role": message.role,
                        "content": message.content,
                    }
                    for message in history_messages
                ]

                # 3. Generate Alya's actual AI response.

                try:
                    reply = await generate_reply(
                        history=history,
                        preferred_language=chat_input.language,
                    )

                except Exception:
                    logger.exception(
                        "Failed to generate Alya's response."
                    )

                    await websocket.send_json({
                        "type": "error",
                        "message": (
                            "I couldn't reach my AI brain. "
                            "Please check whether Ollama is running "
                            "and the model is available."
                        ),
                    })

                    continue

                # 4. Save Alya's response.

                assistant_message = Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=reply.text,
                    language=reply.language,
                    emotion=reply.emotion,
                    expression=reply.expression,
                    motion=reply.motion,
                )

                session.add(assistant_message)

                await session.commit()
                await session.refresh(assistant_message)

                # 5. Send structured response to frontend.

                await websocket.send_json({
                    "type": "assistant_message",
                    "message": MessageOut.model_validate(
                        assistant_message
                    ).model_dump(mode="json"),
                })

    except WebSocketDisconnect:
        logger.info(
            "Conversation disconnected: %s",
            conversation_id,
        )