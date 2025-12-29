from pydantic_settings import BaseSettings
from pydantic import EmailStr


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./sql_app.db"
    API_PREFIX: str = "/api/v1"
    TESTING: bool = True
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    USER_REGISTER_EXPIRE_SECONDS: int = 300
    USER_LOGIN_EXPIRE_SECONDS: int = 86400
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: EmailStr = "test@gmail.com"
    MAIL_PORT: int = 456
    MAIL_SERVER: str = ""
    MAIL_FROM_NAME: str = ""
    MAIL_SSL_TLS: bool = True
    MAIL_STARTTLS: bool = False
    USE_CREDENTIALS: bool = True
    VALIDATE_CERTS: bool = True
    MAIL_DEBUG: bool = False
    REDIRECT_URI_BASE: str = "http://localhost:8000"
    FRONTEND_URI: str = "http://localhost:3000"
    GROQ_API_KEY: str
    TAVILY_API_KEY: str
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_CALENDAR_CREDENTIALS_PATH: str = "credentials.json"
    GOOGLE_CALENDAR_TOKEN_PATH: str = "token.json"
    SECRET_KEY: str = ""
    TEAM_SUPPORT_EMAIL: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
