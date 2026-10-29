import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", str(_BACKEND_DIR / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    secret_key: str = "dev-secret-key-change-in-production"
    access_token_expire_minutes: int = 480
    database_url: str = ""
    default_rental_days: int = 14
    max_active_rentals: int = 2

    # Vector DB / Qdrant settings
    qdrant_url: str | None = None
    qdrant_api_key: str | None = None
    qdrant_path: str = "./qdrant_data"
    qdrant_collection: str = "books"
    gemini_api_key: str | None = None
    # Free local FastEmbed model; its 384-dimensional vectors match the Qdrant index.
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    # Loading FastEmbed + full-catalog indexing on boot needs >512Mi (typical Render free tier).
    startup_qdrant_index: bool = False
    enable_vector_search: bool = True

    def model_post_init(self, __context: object) -> None:
        on_render = bool(os.getenv("RENDER"))
        if on_render and os.getenv("ENABLE_VECTOR_SEARCH") is None:
            self.enable_vector_search = False
        if on_render and os.getenv("STARTUP_QDRANT_INDEX") is None:
            self.startup_qdrant_index = False


settings = Settings()
