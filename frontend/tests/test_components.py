"""Smoke and functional tests for the current Streamlit application."""

import os
import sys
import gc
import pytest

from streamlit.testing.v1 import AppTest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
# Explicitly force backend disconnected in testing to use fast, mock responses
config.BACKEND_CONNECTED = False

from utils import api_client

APP_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")

ALL_PAGES = [
    "pages/1_💬_Chat.py",
    "pages/2_📊_Health_Metrics.py",
    "pages/3_📁_Documents.py",
    "pages/4_📋_History.py",
    "pages/5_👨‍⚕️_Patients.py",
    "pages/6_🩺_Clinical_Support.py",
    "pages/7_⚙️_Settings.py",
    "pages/8_📖_About.py",
    "pages/9_🔬_Symptom_Checker.py",
    "pages/10_🚨_Outbreak_Alerts.py",
    "pages/11_💊_Medications.py",
    "pages/12_📈_Admin.py",
]


@pytest.fixture(autouse=True)
def run_gc():
    """Active garbage collection fixture to prevent memory bloat and AppTest timeouts."""
    yield
    gc.collect()


def open_authenticated_page(page_path):
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=60)
    at.session_state["access_token"] = "stub_token"
    at.switch_page(page_path)
    at.run(timeout=60)
    return at


def test_disconnected_online_status_is_offline_without_network_probe():
    assert api_client.get_online_status() == {
        "status": "offline",
        "hybrid_mode_active": False,
        "search_engine": None,
    }


def test_landing_page_boots():
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=60)
    assert not at.exception


@pytest.mark.parametrize("page", ALL_PAGES)
def test_page_boots_without_exception(page):
    at = open_authenticated_page(page)
    assert not at.exception, f"{page} raised: {at.exception}"


def test_chat_input_produces_response():
    at = open_authenticated_page("pages/1_💬_Chat.py")
    assert len(at.chat_input) == 1
    at.chat_input[0].set_value("What is malaria?").run(timeout=60)
    assert len(at.session_state["messages"]) == 2


def test_health_metric_form_has_current_controls():
    at = open_authenticated_page("pages/2_📊_Health_Metrics.py")
    assert any("Select Metric" in (widget.label or "") for widget in at.selectbox)
    assert any("Save Metric" in (widget.label or "") for widget in at.button)


def test_history_page_has_search_and_date_filter():
    at = open_authenticated_page("pages/4_📋_History.py")
    assert len(at.text_input) > 0
    assert len(at.date_input) > 0


def test_patient_page_boots_with_backend_disconnected():
    at = open_authenticated_page("pages/5_👨‍⚕️_Patients.py")
    assert any("Patient Management" in (element.value or "") for element in at.title)


def test_settings_page_has_model_controls():
    at = open_authenticated_page("pages/7_⚙️_Settings.py")
    assert len(at.color_picker) > 0
    assert len(at.slider) == 3


def test_about_page_boots():
    at = open_authenticated_page("pages/8_📖_About.py")
    assert any("About AfriHealth Assistant" in (element.value or "") for element in at.markdown)
