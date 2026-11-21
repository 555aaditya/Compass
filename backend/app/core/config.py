"""Application settings, loaded from environment / .env. Every integration is optional."""
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    app_env: str = "development"
    database_url: str = f"sqlite:///{REPO_ROOT / 'data' / 'compass.db'}"

    # Candidate knowledge base: the Resume Wiki inside a local Quant-Journal checkout.
    wiki_path: Path = Path("~/Documents/GitHub/Quant-Journal/V2.0/10-Resume-Wiki").expanduser()
    # Wiki pages that describe the product itself, never the candidate (product_context).
    wiki_product_context_pages: list[str] = Field(default_factory=lambda: ["projects/compass.md"])

    master_resume_path: Path = REPO_ROOT / "resumes" / "master" / "main.tex"
    generated_resumes_path: Path = REPO_ROOT / "resumes" / "generated"

    claim_overrides_path: Path = REPO_ROOT / "resumes" / "claim_overrides.json"

    github_token: str = ""

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    email_address: str = ""
    email_password: str = ""
    email_to: str = ""
    whatsapp_enabled: bool = False
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_to: str = ""

    job_scan_interval_hours: int = 12
    wiki_sync_interval_hours: int = 24
    scheduler_enabled: bool = True

    minimum_match_score: int = 70
    job_freshness_days: int = 14
    auto_generate_resumes: bool = True
    require_resume_approval: bool = True

    @field_validator("wiki_path", "master_resume_path", "generated_resumes_path", "claim_overrides_path", mode="after")
    @classmethod
    def _expand(cls, v: Path) -> Path:
        v = v.expanduser()
        return v if v.is_absolute() else (REPO_ROOT / v).resolve()

    def redacted(self) -> dict:
        secret = {"github_token", "telegram_bot_token", "email_password", "whatsapp_access_token"}
        out = {}
        for k, v in self.model_dump().items():
            out[k] = ("***" if v else "") if k in secret else str(v) if isinstance(v, Path) else v
        return out


@lru_cache
def get_settings() -> Settings:
    return Settings()
