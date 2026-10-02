from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    api_port: int = 8000
    database_url: str = ""
    llm_enabled: bool = False
    openai_api_key: str = ""
    openai_model: str = "gpt-5"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
