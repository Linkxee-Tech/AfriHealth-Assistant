"""
Frontend configuration for AfriHealth Assistant.
Central place for theme colours, defaults, and constants used across pages.
"""

APP_NAME = "AfriHealth Assistant"
APP_VERSION = "0.2.0"
APP_TAGLINE = "Intelligent Healthcare, Offline. For Africa."

# --- Colour palette (per project blueprint) ---
THEMES = {
    "Dark": {
        "primary_bg": "#0A192F",
        "card_bg": "#112240",
        "accent_green": "#2EAA7D",
        "secondary_grey": "#8892B0",
        "text": "#FFFFFF",
        "border": "#1d2d50",
    },
    "Light": {
        "primary_bg": "#F5F7FA",
        "card_bg": "#FFFFFF",
        "accent_green": "#1E8E62",
        "secondary_grey": "#5B6478",
        "text": "#0A192F",
        "border": "#D9DEE8",
    },
}

DEFAULT_THEME = "Dark"

LANGUAGES = ["English", "Hausa", "Swahili"]

QUICK_QUESTIONS = [
    "What should I do if I have a fever?",
    "What is malaria?",
    "How do I treat dehydration?",
    "What are signs of typhoid?",
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

# --- Backend connection (not yet live) ---
BACKEND_BASE_URL = "http://localhost:8000"
BACKEND_CONNECTED = False  # flip to True once FastAPI backend is running
