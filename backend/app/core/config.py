from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "CodeSage API"
    API_V1_STR: str = "/api/v1"
    BACKEND_CORS_ORIGINS: list[str] = ["*"] # Adjust in production
    
    # Database
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "codesage_db"

    # GitHub API
    GITHUB_API_BASE_URL: str = "https://api.github.com"
    GITHUB_API_VERSION: str = "2022-11-28"
    GITHUB_TOKEN: str = ""  # Optional default token for testing

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
