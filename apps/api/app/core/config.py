from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    cors_origins: str = (
        "http://localhost:8081,"
        "http://127.0.0.1:8081,"
        "http://localhost:3000,"
        "http://localhost:5173,"
        "http://127.0.0.1:5173"
    )

    database_url: str = (
        "postgresql+psycopg://"
        "ev_user:change_me@localhost:5432/ev_smart_charging"
    )

    jwt_secret_key: str = "change_me_to_a_long_random_secret"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 30
    password_reset_token_expire_minutes: int = 30
    password_reset_return_token_for_development: bool = True
    password_reset_email_enabled: bool = False

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str = "no-reply@smartevcharging.local"
    smtp_use_starttls: bool = True

    charger_event_secret: str = "change_me_charger_event_secret"

    recommendation_policy_name: str = "weighted_score"
    topology_scenario_id: str | None = None
    dynamic_pricing_enabled: bool = True
    routing_provider_name: str = "simple_distance"
    osmnx_graph_path: str = "data/processed/routing/dundee_drive.graphml"

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
