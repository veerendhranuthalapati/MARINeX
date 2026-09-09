from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    PROJECT_NAME: str = "MARINeX"
    PROJECT_DESCRIPTION: str = (
        "SIH26143: Satellite-Derived Oil Spill Detection & AIS Vessel Correlation Monorepo MVP"
    )
    API_V1_STR: str = "/api/v1"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    # Default to local SQLite for zero-setup local dev/testing; switch to PostgreSQL via env in Docker
    DATABASE_URL: str = "sqlite:///./marinex.db"
    USE_POSTGIS: bool = False

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "*",
    ]

    # File paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR.parent / "data"
    SAMPLES_DIR: Path = BASE_DIR.parent / "data" / "samples"
    UPLOADS_DIR: Path = BASE_DIR / "uploads"

    # Default Attribution Weights
    WEIGHT_PROXIMITY: float = 0.35
    WEIGHT_TEMPORAL: float = 0.25
    WEIGHT_TRAJECTORY: float = 0.25
    WEIGHT_BEHAVIOR: float = 0.15

    # Drift Simulation defaults
    DEFAULT_WIND_DRIFT_FACTOR: float = 0.032  # 3.2% of 10m wind vector
    DEFAULT_DIFFUSION_COEFF: float = 10.0      # m2/s turbulent eddy diffusivity

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
