from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Scalable Booking System"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str
    TEST_DATABASE_URL: str = ""
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    RABBITMQ_URL: str
    REDIS_URL: str
    ENVIRONMENT: str = "development"

    # Email (SendGrid in production, unused in development)
    SENDGRID_API_KEY: str = ""
    EMAIL_FROM: str = "booking-system@example.com"

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()
