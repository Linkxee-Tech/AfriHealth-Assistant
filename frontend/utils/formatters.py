"""Shared formatting utilities for the frontend."""

from datetime import datetime


def now_time():
    return datetime.now().strftime("%H:%M")


def now_datetime():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def truncate(text: str, length: int = 60) -> str:
    text = text or ""
    return (text[:length] + "…") if len(text) > length else text


def messages_to_report(messages, app_name="AfriHealth Assistant"):
    """Format a message list into a plain-text report for export."""
    lines = [
        f"{app_name} — Conversation Report",
        f"Generated: {now_datetime()}",
        "Mode: 100% Offline",
        "=" * 50,
        "",
    ]
    for m in messages:
        speaker = "You" if m["role"] == "user" else app_name
        lines.append(f"[{m.get('time', '')}] {speaker}:")
        lines.append(m["content"])
        if m.get("source"):
            lines.append(f"(Source: {m['source']})")
        lines.append("")
    lines.append("=" * 50)
    lines.append(
        "Disclaimer: This report is for informational purposes only and "
        "does not replace professional medical advice."
    )
    return "\n".join(lines)
