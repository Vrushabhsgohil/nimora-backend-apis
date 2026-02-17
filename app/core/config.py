from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "Niroma Backend APIs"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "changethis"
    
    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4.1-nano"
    
    # WaveSpeed Vidu
    VIDU_API_KEY: str
    VIDU_API_BASE_URL: str = "https://api.wavespeed.ai/api/v3"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
