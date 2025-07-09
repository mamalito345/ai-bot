from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openai_api_key: str
    database_url: str
    port: int
    woo_cus: str
    woo_secret: str
    base_url: str

    class Config:
        env_file = ".env"

settings = Settings()

