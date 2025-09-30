import os

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_env_file_path():
    """
    Get the path to the .env file, handling both local and CI environments
    """
    # Try different possible locations for .env file
    possible_paths = [
        os.path.join(os.path.dirname(__file__), ".env"),  # Same directory as config.py
        ".env",  # Current working directory
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return path

    # Return None if no .env file found (GitHub Actions will use environment variables)
    return None


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=get_env_file_path(),
        env_file_encoding="utf-8",
        case_sensitive=False,
        # Allow environment variables to override .env file values
        env_ignore_empty=True,
    )

    MONARK_PW: SecretStr = Field(
        description="Password used to extract transaction data and budget data",
        env="MONARK_PW",
    )

    MONARK_USER: str = Field(
        description="Email to access Monark account", env="MONARK_USER"
    )

    MONARK_DD_ID: SecretStr = Field(
        description="Device ID for the Monark account", env="MONARK_DD_ID"
    )

    MONGO_URL: SecretStr = Field(
        description="MongoDB connection string", env="MONGO_URL"
    )

    MONGO_DB: str = Field(description="MongoDB database name", env="MONGO_DB")

    GROQ_API_KEY: SecretStr = Field(description="API key for Groq", env="GROQ_API_KEY")

    GROQ_LLAMA_VERSATILE: str = Field(default="llama-3.3-70b-versatile")

    GROQ_LLAMA_INSTRUCT: str = Field(default="llama-3.3-70b-instruct")

    GROQ_QWEN_REASONING: str = Field(default="qwen/qwen3-32b")

    GROQ_OPENAI_20B_MODE: str = Field(default="openai/gpt-oss-20b")

    SMTP_USER: str = Field(description="SMTP user for sending emails", env="SMTP_USER")

    SMTP_PASSWORD: SecretStr = Field(
        description="SMTP password for sending emails", env="SMTP_PASSWORD"
    )


Settings = Settings()
