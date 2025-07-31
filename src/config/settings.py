from pathlib import Path
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent.parent


class ConfigBase(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


class BotConfig(ConfigBase):
    model_config = SettingsConfigDict(env_prefix="BOT_")

    token: SecretStr = "token"
    webhook_secret: SecretStr = "DFer1234"
    webhook_url: str = "https://example.com/webhook"
    webhook_path: str = "/webhook"


class DatabaseConfig(ConfigBase):
    model_config = SettingsConfigDict(env_prefix="DB_")

    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    password: SecretStr = "postgres"
    database: str = "app_db"

    @property
    def async_url(self) -> str:
        return f"postgres://{self.user}:{self.password.get_secret_value()}@{self.host}:{self.port}/{self.database}"

    @property
    def sync_url(self) -> str:
        return f"postgresql://{self.user}:{self.password.get_secret_value()}@{self.host}:{self.port}/{self.database}"


class RedisConfig(ConfigBase):
    model_config = SettingsConfigDict(env_prefix="REDIS_")

    host: str = "localhost"
    port: int = 6379
    db: int = 0
    expiration: int = 3600

    @property
    def dsn(self) -> str:
        return f"redis://{self.host}:{self.port}/{self.db}"


class Config(ConfigBase):
    bot: BotConfig = BotConfig()
    database: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()


config = Config()


if __name__ == "__main__":
    print(config.bot.token.get_secret_value())
