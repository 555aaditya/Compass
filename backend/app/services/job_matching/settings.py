from sqlalchemy.orm import Session

from app.models import UserSetting
from app.services.job_matching.preferences import Preferences


def load_preferences(db: Session) -> Preferences:
    row = db.get(UserSetting, "preferences")
    return Preferences.from_dict(row.value if row else None)


def save_preferences(db: Session, data: dict) -> Preferences:
    prefs = Preferences.from_dict({**load_preferences(db).to_dict(), **data})
    row = db.get(UserSetting, "preferences")
    if row is None:
        db.add(UserSetting(key="preferences", value=prefs.to_dict()))
    else:
        row.value = prefs.to_dict()
    db.commit()
    return prefs
