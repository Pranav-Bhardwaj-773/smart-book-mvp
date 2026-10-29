import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.database import Base, SessionLocal, engine
from app.models import AppSettings, Book, Notification, Rental, User  
from app.seed import seed_if_empty
from app.routers import auth as auth_router
from app.routers import books as books_router
from app.routers import rentals as rentals_router
from app.routers import admin as admin_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
        from app.config import settings

        if not settings.startup_qdrant_index:
            logging.getLogger(__name__).info(
                "Skipping Qdrant startup indexing (STARTUP_QDRANT_INDEX=false). "
                "Keyword search is still available; run index_books.py locally to refresh vectors."
            )
        else:
            try:
                from app.services.vector_store import (
                    get_qdrant_client,
                    index_books_from_db,
                    qdrant_index_in_sync,
                )

                if not qdrant_index_in_sync(db):
                    logging.getLogger(__name__).info(
                        "Qdrant index out of sync with database; re-indexing catalog…"
                    )
                    index_books_from_db(db, recreate=True)
                else:
                    with get_qdrant_client() as client:
                        coll_exists = client.collection_exists(settings.qdrant_collection)
                        count = (
                            client.count(settings.qdrant_collection).count
                            if coll_exists
                            else 0
                        )
                    if not coll_exists or count == 0:
                        index_books_from_db(db)
            except Exception as e:
                logging.getLogger(__name__).warning(
                    "Could not auto-index into Qdrant: %s", e
                )
    finally:
        db.close()
    yield


app = FastAPI(title="Smart Book API", lifespan=lifespan)

_logger = logging.getLogger(__name__)


def _cors_allow_origins() -> list[str]:
    origins = [
        "http://localhost:3000",
        "https://frontend-olive-eight-45.vercel.app",
    ]
    extra = os.getenv("CORS_ORIGINS", "")
    if extra:
        origins.extend(part.strip() for part in extra.split(",") if part.strip())
    return list(dict.fromkeys(origins))


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins(),
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception):
    _logger.exception("Unhandled server error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

app.include_router(auth_router.router)
app.include_router(books_router.router)
app.include_router(rentals_router.router)
app.include_router(admin_router.router)


@app.get("/health")
def health():
    return {"status": "ok"}