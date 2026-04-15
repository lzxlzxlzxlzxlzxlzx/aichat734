from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import (
    cards_router,
    health_router,
    messages_router,
    prompt_traces_router,
    sessions_router,
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


@app.exception_handler(AppError)
async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": exc.message, "detail": None},
    )


app.include_router(health_router, prefix=settings.api_v1_prefix)
app.include_router(cards_router, prefix=settings.api_v1_prefix)
app.include_router(sessions_router, prefix=settings.api_v1_prefix)
app.include_router(messages_router, prefix=settings.api_v1_prefix)
app.include_router(prompt_traces_router, prefix=settings.api_v1_prefix)
