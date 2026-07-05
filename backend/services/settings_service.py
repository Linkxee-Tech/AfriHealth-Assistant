from typing import Dict, Any
from sqlalchemy.orm import Session
from backend.database.models import Settings
import logging

logger = logging.getLogger(__name__)

class SettingsService:
    @staticmethod
    def get_settings(db: Session) -> Dict[str, str]:
        settings_rows = db.query(Settings).all()
        return {s.key: s.value for s in settings_rows}

    @staticmethod
    def update_settings(db: Session, settings_data: Dict[str, str]) -> Dict[str, str]:
        for key, value in settings_data.items():
            setting = db.query(Settings).filter(Settings.key == key).first()
            if setting:
                setting.value = str(value)
            else:
                new_setting = Settings(key=key, value=str(value))
                db.add(new_setting)
        db.commit()
        return SettingsService.get_settings(db)

    @staticmethod
    def reset_defaults(db: Session) -> Dict[str, str]:
        defaults = {
            "model_temperature": "0.7",
            "max_tokens": "512",
            "top_p": "0.9",
            "thread_count": "4",
            "enable_web_search": "True",
            "enable_cloud_fallback": "True",
            "theme": "System"
        }
        db.query(Settings).delete()
        db.commit()
        return SettingsService.update_settings(db, defaults)
