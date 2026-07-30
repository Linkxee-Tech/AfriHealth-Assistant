"""
System status indicator component.

Spec requirements:
  - Model load status
  - Memory usage  (with st.progress bar)
  - CPU usage
  - Response time (last inference latency tracked in session_state)
"""

import streamlit as st
import psutil


def render_status_indicator():
    online  = st.session_state.get("model_loaded", False)
    mode = st.session_state.get("processing_mode", "OFFLINE")
    gemini_configured = st.session_state.get("gemini_configured", False)
    mem_gb  = st.session_state.get("memory_usage_gb", 0.0)
    last_ms = st.session_state.get("last_response_ms", None)

    # --- Live system metrics via psutil ---
    cpu_pct = psutil.cpu_percent(interval=0.1)
    sys_mem = psutil.virtual_memory()
    sys_mem_used_gb = round(sys_mem.used / (1024 ** 3), 1)
    sys_mem_total_gb = round(sys_mem.total / (1024 ** 3), 1)
    sys_mem_pct = sys_mem.percent

    dot_class = "status-dot" if online else "status-dot offline"
    status_text = "🟢 Model Loaded" if online else "🔴 Model Not Loaded"

    st.markdown(
        f"""
        <div class="status-card">
            <div style="margin-bottom:6px;">
                <span class="{dot_class}"></span>
                <span class="status-value">{status_text}</span>
            </div>
            <div style="margin-top:4px;">
                <span class="status-label">Mode:</span>
                <span class="status-value"> {mode}</span>
            </div>
            <div style="margin-top:4px;">
                <span class="status-label">Cloud fallback:</span>
                <span class="status-value"> {"Configured" if gemini_configured else "Unavailable"}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Memory usage bar (spec: "Memory usage bar")
    st.markdown(
        f'<span class="status-label">RAM  {sys_mem_used_gb} / {sys_mem_total_gb} GB</span>',
        unsafe_allow_html=True,
    )
    st.progress(int(sys_mem_pct), text=f"{sys_mem_pct:.0f}%")

    # CPU usage bar
    st.markdown(
        f'<span class="status-label">CPU Usage</span>',
        unsafe_allow_html=True,
    )
    st.progress(int(cpu_pct), text=f"{cpu_pct:.0f}%")

    # Response time (last inference latency)
    if last_ms is not None:
        st.markdown(
            f'<span class="status-label">Last Response: <b>{last_ms:.0f} ms</b></span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<span class="status-label">Last Response: —</span>',
            unsafe_allow_html=True,
        )

    # LLM memory allocation (model footprint, separate from system RAM)
    if mem_gb and mem_gb > 0:
        model_pct = min(int((mem_gb / sys_mem_total_gb) * 100), 100)
        st.markdown(
            f'<span class="status-label">Model RAM  {mem_gb} GB</span>',
            unsafe_allow_html=True,
        )
        st.progress(model_pct, text=f"{mem_gb} GB")
