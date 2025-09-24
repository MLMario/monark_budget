from typing import Optional
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field
from urllib.parse import quote_plus

import os


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), ".env"),  
        env_file_encoding="utf-8",
        case_sensitive=False
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