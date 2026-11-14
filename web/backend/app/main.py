from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth.exceptions import InvalidCredentialsError
from app.auth.router import router as auth_router
from app.constants.auth import INVALID_CREDENTIALS_CODE
from app.constants.http import API_V1_PREFIX, CORS_ALLOWED_HEADERS, CORS_ALLOWED_METHODS
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


# Conversion des erreurs métier en réponses HTTP : un seul endroit.
@app.exception_handler(InvalidCredentialsError)
async def handle_invalid_credentials(_: Request, __: InvalidCredentialsError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST, content={"detail": INVALID_CREDENTIALS_CODE}
    )


# Le cookie de session circule entre le frontend et l'API : origine explicite, jamais "*".
app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_settings().frontend_url],
    allow_credentials=True,
    allow_methods=list(CORS_ALLOWED_METHODS),
    allow_headers=list(CORS_ALLOWED_HEADERS),
)

# Les routers de contexte n'ont pas de préfixe de version : c'est ici qu'on les rattache à une version.
api_v1_router = APIRouter(prefix=API_V1_PREFIX)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(users_router)

app.include_router(api_v1_router)
