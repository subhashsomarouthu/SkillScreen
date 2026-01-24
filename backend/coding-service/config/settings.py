from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database Configuration
    database_url: str = Field(..., alias="DATABASE_URL")

    # Service Configuration
    service_name: str = Field(default="coding-service", alias="SERVICE_NAME")
    service_port: int = Field(default=8080, alias="PORT")
    environment: str = Field(default="development", alias="ENVIRONMENT")

    # Judge0 Configuration
    judge0_base_url: str = Field(
        default="https://judge0-ce.p.rapidapi.com",
        alias="JUDGE0_BASE_URL"
    )
    judge0_rapidapi_key: str = Field(..., alias="JUDGE0_RAPIDAPI_KEY")
    judge0_rapidapi_host: str = Field(
        default="judge0-ce.p.rapidapi.com",
        alias="JUDGE0_RAPIDAPI_HOST"
    )

    # Execution Configuration
    max_poll_attempts: int = Field(default=10, alias="MAX_POLL_ATTEMPTS")
    poll_interval_seconds: float = Field(default=0.5, alias="POLL_INTERVAL_SECONDS")
    execution_timeout_seconds: int = Field(default=20, alias="EXECUTION_TIMEOUT_SECONDS")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # JWT Configuration (must match SSO service)
    jwt_secret_key: str = Field(default="supersecret", alias="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="ALGORITHM")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


# Create global settings instance
settings = Settings()
