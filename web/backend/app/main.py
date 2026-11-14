from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.constants.http import CORS_ALLOWED_HEADERS, CORS_ALLOWED_METHODS
from app.core.config import get_settings
from app.core.database import Base, engine
from app.users.router import router as users_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Pas d'outil de migration pour l'instant : création des tables manquantes au démarrage.
    # À remplacer par Alembic dès que le schéma évolue.
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="Adopt AI", lifespan=lifespan)

# Le cookie de session circule entre le frontend et l'API : origine explicite, jamais "*".
app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_settings().frontend_url],
    allow_credentials=True,
    allow_methods=list(CORS_ALLOWED_METHODS),
    allow_headers=list(CORS_ALLOWED_HEADERS),
)

app.include_router(auth_router)
app.include_router(users_router)
