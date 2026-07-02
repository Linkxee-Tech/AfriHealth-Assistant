"""
Smoke + functional tests for AfriHealth Assistant frontend.
Run with:  pytest frontend/tests/test_components.py -v
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamlit.testing.v1 import AppTest

APP_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")

ALL_PAGES = [
    "pages/1_💬_Chat.py",
    "pages/2_📊_Health_Metrics.py",
    "pages/3_📁_Document_Analysis.py",
    "pages/4_📋_Chat_History.py",
    "pages/5_⚙️_Settings.py",
    "pages/6_📖_About.py",
]


def test_landing_page_boots():
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=20)
    assert not at.exception


def test_all_pages_boot_without_exception():
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=20)
    for page in ALL_PAGES:
        at.switch_page(page)
        at.run(timeout=20)
        assert not at.exception, f"{page} raised: {at.exception}"


def test_chat_send_flow_and_response_timer():
    """Chat send produces 2 messages and sets last_response_ms."""
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=20)
    at.switch_page("pages/1_💬_Chat.py")
    at.run(timeout=20)
    at.text_area(key="typed_input").set_value("What is malaria?").run(timeout=20)
    [b for b in at.button if "Send" in b.label][0].click().run(timeout=30)
    assert len(at.session_state["messages"]) == 2
    assert at.session_state["last_response_ms"] is not None


def test_chat_empty_send_does_not_add_message():
    """Clicking Send with empty input must not add a message."""
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=20)
    at.switch_page("pages/1_💬_Chat.py")
    at.run(timeout=20)
    [b for b in at.button if "Send" in b.label][0].click().run(timeout=20)
    assert len(at.session_state["messages"]) == 0


def test_health_log_numeric_entry_creates_metric_card():
    """number_input entry for Heart Rate produces a st.metric card."""
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=20)
    at.switch_page("pages/2_📊_Health_Metrics.py")
    at.run(timeout=20)
    [s for s in at.selectbox if s.label == "Metric"][0].set_value("Heart Rate").run(timeout=20)
    # Heart Rate uses number_input (not text_input)
    assert len(at.number_input) > 0, "number_input not found for Heart Rate"
    at.number_input[0].set_value(78).run(timeout=20)
    [b for b in at.button if "Add Entry" in b.label][0].click().run(timeout=20)
    assert any(m.label == "Heart Rate" for m in at.metric)


def test_health_log_bp_uses_text_input():
    """Blood Pressure uses text_input (for '120/80' format)."""
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=20)
    at.switch_page("pages/2_📊_Health_Metrics.py")
    at.run(timeout=20)
    [s for s in at.selectbox if s.label == "Metric"][0].set_value("Blood Pressure").run(timeout=20)
    # BP should show text_input NOT number_input
    bp_inputs = [t for t in at.text_input if t.label == "Value"]
    assert len(bp_inputs) > 0, "text_input for Blood Pressure not found"


def test_settings_has_color_picker_and_four_sliders():
    """Settings page has the color_picker and all 4 model sliders."""
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=20)
    at.switch_page("pages/5_⚙️_Settings.py")
    at.run(timeout=20)
    assert len(at.color_picker) > 0, "color_picker missing from Settings"
    assert len(at.slider) == 4, f"Expected 4 model sliders, got {len(at.slider)}"


def test_settings_theme_switch():
    """Changing theme via radio updates session_state['theme']."""
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=20)
    at.switch_page("pages/5_⚙️_Settings.py")
    at.run(timeout=20)
    at.radio[0].set_value("Light").run(timeout=20)
    assert at.session_state["theme"] == "Light"


def test_history_page_has_date_input_and_sort():
    """History page has date_input and sort selectbox."""
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=20)
    at.switch_page("pages/4_📋_Chat_History.py")
    at.run(timeout=20)
    assert len(at.date_input) > 0, "date_input missing from History page"
    sort_sbs = [s for s in at.selectbox if "Sort" in (s.label or "")]
    assert len(sort_sbs) > 0, "Sort selectbox missing from History page"


def test_new_chat_archives_to_history():
    """New Chat button persists messages to SQLite and clears session."""
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=20)
    at.switch_page("pages/1_💬_Chat.py")
    at.run(timeout=20)
    at.text_area(key="typed_input").set_value("Archive test").run(timeout=20)
    [b for b in at.button if "Send" in b.label][0].click().run(timeout=30)
    assert len(at.session_state["messages"]) == 2
    # Click New Chat (sidebar button)
    [b for b in at.sidebar.button if "New Chat" in b.label][0].click().run(timeout=20)
    assert len(at.session_state["messages"]) == 0
    import db; db.init_db()
    assert len(db.list_sessions()) >= 1


def test_about_page_has_expanders():
    """About page renders at least 3 tech-stack expanders."""
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=20)
    at.switch_page("pages/6_📖_About.py")
    at.run(timeout=20)
    assert len(at.expander) >= 3
