"""Application configuration using Pydantic Settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # P21 API Configuration
    p21_base_url: str = "https://p21.ifp.local"
    p21_username: str = ""
    p21_password: str = ""

    # Application Settings
    app_env: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000

    @property
    def odata_url(self) -> str:
        """Get the OData API base URL."""
        return f"{self.p21_base_url}/odataservice/odata"

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.app_env.lower() == "development"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
