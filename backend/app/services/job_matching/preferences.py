"""Job preferences: defaults here, overridable from the dashboard (stored in user_settings)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields

DEFAULT_WEIGHTS = {"skills": 30, "role": 20, "experience": 20, "projects": 15, "location": 10, "freshness": 5}

INDIA_CITIES = ["india", "bangalore", "bengaluru", "hyderabad", "pune", "mumbai", "gurgaon", "gurugram",
                "noida", "delhi", "new delhi", "ncr", "chennai", "kolkata", "ahmedabad", "kochi", "jaipur",
                "chandigarh", "indore", "coimbatore", "trivandrum", "thiruvananthapuram", "mohali"]


@dataclass
class Preferences:
    max_experience_years: float = 2.0
    freshness_days: int = 14
    min_match_score: int = 70
    weights: dict = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    allow_unpaid: bool = False
    allow_relocation_outside_india: bool = False
    include_uncertain: bool = True   # keep uncertain jobs visible (flagged), never notify on them
    india_locations: list = field(default_factory=lambda: list(INDIA_CITIES))
    target_roles: list = field(default_factory=lambda: [
        "software development engineer", "sde", "software engineer", "backend engineer", "full stack",
        "fullstack", "python developer", "java developer", "data engineer", "platform engineer",
        "developer tools", "devtools", "developer experience", "ai engineer", "ml engineer",
        "machine learning engineer", "research engineer", "member of technical staff", "software developer",
        "application developer", "associate software", "site reliability", "devops engineer",
    ])
    notification_channels: dict = field(default_factory=lambda: {"telegram": True, "email": False, "whatsapp": False})
    daily_notification_limit: int = 10

    @classmethod
    def from_dict(cls, data: dict | None) -> "Preferences":
        base = cls()
        valid = {f.name for f in fields(cls)}
        for k, v in (data or {}).items():
            if k in valid:
                setattr(base, k, v)
        return base

    def to_dict(self) -> dict:
        return asdict(self)
