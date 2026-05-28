from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Voyage Assistant API"
    app_version: str = "0.1.0"
    debug: bool = False

    database_url: str = "sqlite:///./voyage.db"

    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    gemini_api_key: str = ""
    tavily_api_key: str = ""

    brevo_api_key: str = ""
    brevo_sender_email: str = ""
    brevo_sender_name: str = "Voyage Assistant"

    rag_index_dir: str = "./app/rag/store"

    admin_default_email: str = "admin@voyage.local"
    admin_default_password: str = ""

    auth_secret: str = ""

    frontend_url: str = "http://localhost:3000"

    # APIs externes
    pixabay_api_key: str = ""
    navitia_api_key: str = ""
    amadeus_client_id: str = ""
    amadeus_client_secret: str = ""


settings = Settings()
