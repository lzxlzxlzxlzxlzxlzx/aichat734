from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import (
    cards_router,
    chat_router,
    conversation_snapshots_router,
    creation_router,
    health_router,
    long_term_memories_router,
    memory_summaries_router,
    media_router,
    messages_router,
    play_router,
    prompt_traces_router,
    sessions_router,
    states_router,
)
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.services.database_init_service import initialize_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": exc.message, "detail": None},
    )


app.include_router(health_router, prefix=settings.api_v1_prefix)
app.include_router(cards_router, prefix=settings.api_v1_prefix)
app.include_router(chat_router, prefix=settings.api_v1_prefix)
app.include_router(conversation_snapshots_router, prefix=settings.api_v1_prefix)
app.include_router(creation_router, prefix=settings.api_v1_prefix)
app.include_router(long_term_memories_router, prefix=settings.api_v1_prefix)
app.include_router(memory_summaries_router, prefix=settings.api_v1_prefix)
app.include_router(media_router, prefix=settings.api_v1_prefix)
app.include_router(sessions_router, prefix=settings.api_v1_prefix)
app.include_router(messages_router, prefix=settings.api_v1_prefix)
app.include_router(play_router, prefix=settings.api_v1_prefix)
app.include_router(prompt_traces_router, prefix=settings.api_v1_prefix)
app.include_router(states_router, prefix=settings.api_v1_prefix)
