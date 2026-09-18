"""
Application Settings and Configuration Module.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Optional, List, Union


class Settings(BaseSettings):
    # Application Info
    PROJECT_NAME: str = "Zaslon-QDS"
    VERSION: str = "1.0.0"
    APP_ENV: str = Field(default="development", description="development, staging, or production")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    SECRET_KEY: str = Field(
        default="zaslon_qds_dev_secret_key_change_in_production_123456789",
        description="Application secret key for cryptographic commitments"
    )

    # Database Configuration
    DATABASE_HOST: str = Field(default="localhost")
    DATABASE_PORT: int = Field(default=3306)
    DATABASE_NAME: str = Field(default="zaslon_qds")
    DATABASE_USER: str = Field(default="zaslon_user")
    DATABASE_PASSWORD: str = Field(default="zaslon_secure_password")
    DATABASE_URL_OVERRIDE: Optional[str] = None

    # Quantum Engine Microservice
    QUANTUM_SERVICE_URL: str = Field(
        default="http://quantum-service:8001",
        description="URL to the dedicated CUDA-Q microservice"
    )
    CUDA_TARGET: str = Field(default="default")

    # QDS Workload Parameters
    TELEPORTATION_COUNT: int = Field(default=4096, ge=1, description="Total 3-qubit teleportation operations")
    QUANTUM_BATCH_SIZE: int = Field(default=512, ge=1, le=4096, description="Quantum batch execution size")
    VERIFICATION_SAMPLE_RATIO: float = Field(default=0.05, gt=0.0, le=1.0, description="Verification sample ratio (5%)")

    # Statistical and Cybersecurity Thresholds
    BASELINE_ERROR_RATE: float = Field(default=0.01, ge=0.0, le=0.5, description="Theoretical quantum channel baseline error rate")
    FISHER_SIGNIFICANCE_ALPHA: float = Field(default=0.01, gt=0.0, lt=1.0, description="Fisher exact test significance threshold")
    MISMATCH_THRESHOLD_RATIO: float = Field(default=0.03, ge=0.0, le=1.0, description="Maximum tolerable mismatch ratio (3%)")
    REPLAY_WINDOW_SECONDS: int = Field(default=300, gt=0, description="Max tolerable drift for signature timestamp")

    # Network Bindings
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=8000)

    # CORS Configuration
    CORS_ORIGINS: Union[List[str], str] = Field(
        default=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
            "http://localhost:5175",
            "http://127.0.0.1:5175",
        ],
        description="Allowed CORS origins"
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("DATABASE_HOST")
    @classmethod
    def validate_db_host(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("DATABASE_HOST cannot be empty")
        return v.strip()

    @field_validator("CUDA_TARGET")
    @classmethod
    def validate_cuda_target(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("CUDA_TARGET cannot be empty")
        return v.strip()

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL_OVERRIDE:
            return self.DATABASE_URL_OVERRIDE
        # Standard MySQL PyMySQL connection string
        return (
            f"mysql+pymysql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@"
            f"{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
