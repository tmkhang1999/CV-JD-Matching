import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load YAML configuration
CONFIG_PATH = Path(__file__).parent.parent.parent / "config.yaml"


def load_yaml_config() -> Dict[str, Any]:
    """Load and parse YAML configuration file with environment variable substitution."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Configuration file not found: {CONFIG_PATH}")

    with open(CONFIG_PATH, 'r') as f:
        content = f.read()

    # Replace ${VAR_NAME} or ${VAR_NAME:-default} with environment variable values
    import re

    def replace_env_var(match):
        full_match = match.group(1)
        # Check if there's a default value (syntax: VAR_NAME:-default)
        if ':-' in full_match:
            var_name, default_value = full_match.split(':-', 1)
            return os.getenv(var_name, default_value)
        else:
            # No default, return env var or keep original if not found
            return os.getenv(full_match, match.group(0))

    content = re.sub(r'\$\{([^}]+)}', replace_env_var, content)

    return yaml.safe_load(content)


class AppConfig(BaseModel):
    title: str
    version: str
    host: str
    port: int
    debug: bool


class DatabaseConfig(BaseModel):
    host: str
    port: int
    user: str
    password: str
    database: str
    url: str
    pool_size: int
    max_overflow: int


class OpenAIConfig(BaseModel):
    api_key: str
    extraction_model: str
    embedding_model: str
    reranking_model: str
    temperature: float
    max_completion_tokens: int


class ExtractionConfig(BaseModel):
    timeout: int
    max_retries: int


class MatchingWeights(BaseModel):
    global_: float = Field(alias="global")
    skills_tech: float
    skills_language: float


class MatchingConfig(BaseModel):
    weights: MatchingWeights
    default_limit: int
    max_limit: int


class StorageConfig(BaseModel):
    upload_dir: str


class ScoringRubricConfig(BaseModel):
    version: Optional[str] = None
    philosophy: Optional[str] = None
    total_score: int = 100
    stage_0_hard_filters: Optional[Dict[str, Any]] = None
    stage_1_symbolic_scoring: Optional[Dict[str, Any]] = None
    stage_2_semantic_scoring: Optional[Dict[str, Any]] = None
    stage_3_domain_and_context_bonus: Optional[Dict[str, Any]] = None
    stage_4_delta_factors: Optional[Dict[str, Any]] = None
    final_score_calculation: Optional[Dict[str, Any]] = None
    role_weight_overrides: Optional[Dict[str, Any]] = None
    output_metadata: Optional[Dict[str, Any]] = None


class Settings:
    """Application settings loaded from YAML configuration."""

    def __init__(self):
        # Load YAML configuration
        yaml_config = load_yaml_config()

        # Initialize configuration sections
        self.app = AppConfig(**yaml_config["app"])
        self.database = DatabaseConfig(**yaml_config["database"])
        self.openai = OpenAIConfig(**yaml_config["openai"])
        self.extraction = ExtractionConfig(**yaml_config["extraction"])
        self.matching = MatchingConfig(**yaml_config["matching"])
        self.storage = StorageConfig(**yaml_config["storage"])
        self.scoring_rubric = ScoringRubricConfig(**yaml_config.get("scoring_rubric", {}))

    # Convenience properties for backward compatibility
    @property
    def OPENAI_API_KEY(self) -> str:
        return self.openai.api_key

    @property
    def OPENAI_EXTRACTION_MODEL(self) -> str:
        return self.openai.extraction_model

    @property
    def OPENAI_EMBEDDING_MODEL(self) -> str:
        return self.openai.embedding_model

    @property
    def OPENAI_RERANKING_MODEL(self) -> str:
        return self.openai.reranking_model

    @property
    def OPENAI_TEMPERATURE(self) -> float:
        return self.openai.temperature

    @property
    def OPENAI_MAX_COMPLETION_TOKENS(self) -> int:
        return self.openai.max_completion_tokens

    @property
    def DATABASE_URL(self) -> str:
        return self.database.url


# Global settings instance
settings = Settings()