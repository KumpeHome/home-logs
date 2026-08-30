from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.auth.scopes import oidc_requested_scopes


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Home Logs"
    database_url: str = "mysql+pymysql://homelogs:homelogs@localhost:3306/homelogs"
    upload_dir: str = "./uploads"
    cors_origins: str = "http://localhost:4200"

    oidc_issuer: str = "http://localhost:3301"
    oidc_audience: str = "https://homelogs.app/api"
    oidc_jwks_url: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_scopes: str = oidc_requested_scopes()

    oidc_m2m_client_id: str = ""
    oidc_m2m_client_secret: str = ""
    oidc_management_api: str = ""

    auth_disabled: bool = False
    auth_bypass_email: str = "dev@homelogs.local"
    auth_bypass_subject: str = "dev-bypass"


@lru_cache
def get_settings() -> Settings:
    return Settings()
