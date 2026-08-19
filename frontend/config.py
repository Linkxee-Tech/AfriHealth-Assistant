"""
Frontend configuration for AfriHealth Assistant.
Central place for theme colours, defaults, and constants used across pages.
"""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    # The frontend still runs in its local fallback mode if python-dotenv is
    # not installed; environment variables provided by the shell remain usable.
    pass


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

APP_NAME = "AfriHealth Assistant"
APP_VERSION = "1.0.0"
APP_TAGLINE = "Intelligent Healthcare, Offline. For Africa."

# --- Colour palette (per project blueprint) ---
THEMES = {
    "Dark": {
        "primary_bg": "#0A192F",
        "card_bg": "#1A2A44",
        "accent_green": "#2EAA7D",
        "accent_gold": "#F5A623",
        "secondary_grey": "#8892B0",
        "text": "#FFFFFF",
        "border": "#2A3A54",
    },
    "Light": {
        "primary_bg": "#F5F7FA",
        "card_bg": "#FFFFFF",
        "accent_green": "#1AB394",
        "accent_gold": "#F5A623",
        "secondary_grey": "#8892B0",
        "text": "#0A192F",
        "border": "#D9DEE8",
    },
}

DEFAULT_THEME = "Dark"

LANGUAGES = ["English", "Hausa", "Swahili", "Yoruba", "Igbo", "French", "Pidgin"]

QUICK_QUESTIONS = [
    "Patient has fever, headache, muscle aches. Rules out malaria?",
    "Adult with severe dehydration — fluid resuscitation protocol?",
    "Child with fast breathing and chest indrawing. Assess?",
    "Signs of sepsis — immediate management steps?",
]

CLINICAL_MODES = [
    "Assess Case",
    "Differential",
    "Investigations",
    "Treatment",
    "Medication Check",
    "Referral",
]

HEALTH_METRICS = [
    "Blood Pressure",
    "Heart Rate",
    "Blood Sugar",
    "Weight",
    "Temperature",
    "Oxygen Saturation (SpO2)",
    "Sleep Hours",
]

HEALTH_METRIC_UNITS = {
    "Blood Pressure": "mmHg",
    "Heart Rate": "bpm",
    "Blood Sugar": "mg/dL",
    "Weight": "kg",
    "Temperature": "°C",
    "Oxygen Saturation (SpO2)": "%",
    "Sleep Hours": "hrs",
}

# --- Model settings defaults (sent to backend once connected) ---
DEFAULT_MODEL_SETTINGS = {
    "temperature": 0.7,
    "max_tokens": 512,
    "top_p": 0.9,
    "num_threads": 4,
}

# --- Backend connection ---
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000").rstrip("/")
BACKEND_CONNECTED = _env_bool("BACKEND_CONNECTED", False)
