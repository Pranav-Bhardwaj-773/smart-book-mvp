from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    secret_key: str
    access_token_expire_minutes: int = 480
    database_url: str = "sqlite:///./smartbook.db"
    default_rental_days: int = 14
    max_active_rentals: int = 2


settings = Settings()