from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@db:5432/appdb"
    MODEL_URL: str = "http://model:8001"
    CORS_ALLOW_ORIGINS: str = "*"  # MVP: 일단 전체 허용, 나중에 앱 도메인으로 제한

settings = Settings()
