from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    llm_provider: str = "anthropic"
    anthropic_api_key: str = ""
    model_id: str = "claude-sonnet-4-20250514"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    aws_profile: str = ""
    database_path: str = "data/app.db"
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
