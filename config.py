from typing import Optional
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field
from urllib.parse import quote_plus

import os


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


class Settings(BaseSettings):git 

    model_config = SettingsConfigDict(
        env_file=get_env_file_path(),
        env_file_encoding="utf-8",
        case_sensitive=False,
        # Allow environment variables to override .env file values
        env_ignore_empty=True
    )

    MONARK_PW: str = Field(
        description = "Password used to extract transaction data and budget data",
        env = "MONARK_PW"
    )

    MONARK_USER: str = Field(
        description= "Email to access Monark account",
        env = "MONARK_USER"
    )

    MONARK_DD_ID: str = Field(
        description = "Device ID for the Monark account",
        env = "MONARK_DD_ID"
    )

    MONGO_URL: str = Field(
        description = "MongoDB connection string",  
        env = "MONGO_URL"
    )

    MONGO_DB: str = Field(
        description = "MongoDB database name",
        env = "MONGO_DB"
    )


Settings = Settings()