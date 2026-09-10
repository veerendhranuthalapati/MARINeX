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

    # CORS - explicit dev origins only; wildcard + credentials is disallowed by
    # the fetch spec and would be a security hole. Extend via .env for prod.
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    # File paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR.parent / "data"
    SAMPLES_DIR: Path = BASE_DIR.parent / "data" / "samples"
    UPLOADS_DIR: Path = BASE_DIR / "uploads"
    REPORTS_DIR: Path = BASE_DIR.parent / "reports"
    DEMO_SAMPLE_PATH: Path = SAMPLES_DIR / "imagery" / "sentinel1_20260301_sar_sample.png"

    # Default Attribution Weights
    WEIGHT_PROXIMITY: float = 0.35
    WEIGHT_TEMPORAL: float = 0.25
    WEIGHT_TRAJECTORY: float = 0.25
    WEIGHT_BEHAVIOR: float = 0.15

    # Drift Simulation defaults
    DEFAULT_WIND_DRIFT_FACTOR: float = 0.032  # 3.2% of 10m wind vector
    DEFAULT_DIFFUSION_COEFF: float = 10.0      # m2/s turbulent eddy diffusivity
    DEFAULT_DRIFT_UNCERTAINTY_KM: float = 5.0  # initial origin uncertainty band

    # Environmental real-data adapter (ERA5 / CMEMS). Leave unset for DEMO provider.
    ERA5_CACHE_DIR: str = ""
    CDS_API_KEY: str = ""
    CDS_API_URL: str = ""

    # Production detection defaults. Points at the frozen campaign artifact
    # (marinex_unet_v1.pt, see scripts/freeze_final_model.py). The 0.70
    # threshold is the frozen operating point from reports/calibration.json
    # (best_iou_threshold); temperature 0.226 for calibrated probabilities.
    PROD_MODEL_PATH: str = "models/best_model/marinex_unet_v1.pt"
    PROD_MODEL_NAME: str = "unet"
    PROD_MODEL_CHANNELS: int = 3
    PROD_PREPROC_VARIANT: str = "percentile"
    PROD_DEFAULT_THRESHOLD: float = 0.70
    PROD_CONFIDENCE_MIN: float = 0.60

    @property
    def prod_model_abs_path(self) -> Path:
        p = Path(self.PROD_MODEL_PATH)
        return p if p.is_absolute() else self.BASE_DIR.parent / p

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
