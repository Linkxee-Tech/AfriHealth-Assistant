from typing import Dict, Any
from sqlalchemy.orm import Session
from backend.database.models import Settings
import logging

logger = logging.getLogger(__name__)

class SettingsService:
    @staticmethod
    def _key(user_id: int, key: str) -> str:
        return f"user:{user_id}:{key}"

    @staticmethod
    def get_settings(db: Session, user_id: int) -> Dict[str, str]:
        prefix = f"user:{user_id}:"
        settings_rows = db.query(Settings).filter(Settings.key.like(f"{prefix}%")).all()
        return {s.key[len(prefix):]: s.value for s in settings_rows}

    @staticmethod
    def update_settings(db: Session, user_id: int, settings_data: Dict[str, str]) -> Dict[str, str]:
        for key, value in settings_data.items():
            storage_key = SettingsService._key(user_id, key)
            setting = db.query(Settings).filter(Settings.key == storage_key).first()
            if setting:
                setting.value = str(value)
            else:
                new_setting = Settings(key=storage_key, value=str(value))
                db.add(new_setting)
        db.commit()
        return SettingsService.get_settings(db, user_id)

    @staticmethod
    def reset_defaults(db: Session, user_id: int) -> Dict[str, str]:
        defaults = {
            "model_temperature": "0.7",
            "max_tokens": "512",
            "top_p": "0.9",
            "thread_count": "4",
            "enable_web_search": "True",
            "enable_cloud_fallback": "True",
            "theme": "System"
        }
        prefix = f"user:{user_id}:"
        db.query(Settings).filter(Settings.key.like(f"{prefix}%")).delete(synchronize_session=False)
        db.commit()
        return SettingsService.update_settings(db, user_id, defaults)
