import logging
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    PROJECT_NAME: str = "Dynamic Research Agent"
    API_V1_STR: str = "/api/v1"
    SERVER_HOST: str = Field("0.0.0.0", env="SERVER_HOST")
    SERVER_PORT: int = Field(8765, env="SERVER_PORT")

    GEMINI_API_KEY: str = Field(..., env="GEMINI_API_KEY")
    SCHEMA_GENERATION_MODEL: str = "gemini-2.5-flash"
    SCRAPEGRAPH_EXTRACTION_MODEL: str = "gemini-2.5-flash"

    SCRAPER_MAX_RESULTS: int = 5
    SCRAPER_HEADLESS: bool = True
    SCRAPEGRAPH_MAX_TOKENS: int = 8192
    SCRAPEGRAPH_BATCHSIZE: int = 16

    model_config = SettingsConfigDict(env_file=".env", extra='ignore')

settings = Settings()
