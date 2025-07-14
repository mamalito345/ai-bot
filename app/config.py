from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openai_api_key: str
    database_url: str
    port: int
    woo_cus: str
    woo_secret: str
    base_url: str
    gemini_api_key_1: str
    gemini_api_key_2: str
    gemini_api_key_3: str
    gemini_api_key_4: str
    gemini_api_key_5: str
    gemini_api_key_6: str

    class Config:
        env_file = ".env"

settings = Settings()

