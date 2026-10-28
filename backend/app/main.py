from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    finally:
        db.close()
    yield


app = FastAPI(title="Smart Book API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000","https://frontend-olive-eight-45.vercel.app/"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(books_router.router)
app.include_router(rentals_router.router)
app.include_router(admin_router.router)


@app.get("/health")
def health():
    return {"status": "ok"}