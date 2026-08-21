from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    binance_api_key: str = Field(default="")
    binance_api_secret: str = Field(default="")
    binance_base_url: str = "https://testnet.binance.vision"
    binance_recv_window: int = 5000
    bot_env: str = "testnet"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def is_testnet(self) -> bool:
        return self.bot_env.lower() == "testnet"

    def validate_credentials(self) -> None:
        if not self.binance_api_key:
            raise ValueError("BINANCE_API_KEY is missing")

        if not self.binance_api_secret:
            raise ValueError("BINANCE_API_SECRET is missing")

        if not self.is_testnet:
            raise ValueError(
                "Live environment requires explicit production configuration"
            )
