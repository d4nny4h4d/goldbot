"""Reusable UI components — metric cards, status bars, section headers."""

import streamlit as st

from dashboard.theme import (
    COLOR_GOLD,
    COLOR_LOSS,
    COLOR_MUTED,
    COLOR_PROFIT,
    ICONS,
)


def section_header(icon_key: str, title: str):
    """Render a styled section header with a line icon."""
    icon = ICONS.get(icon_key, "")
    st.markdown(
        f"<h2 style='display:flex;align-items:center;gap:10px;margin:8px 0 12px 0;'>"
        f"<span style='color:{COLOR_GOLD};font-size:20px;'>{icon}</span> {title}</h2>",
        unsafe_allow_html=True,
    )


def status_bar(bot_name: str, is_active: bool, last_refresh: str, open_positions: int):
    """Render a compact status bar at the top of a page."""
    dot_class = "green" if is_active else "red"
    status_text = "Connected" if is_active else "Disconnected"
    st.markdown(
        f"""<div class="status-bar">
            <div class="item">
                <span class="dot {dot_class}"></span>
                <span>{bot_name}: <b>{status_text}</b></span>
            </div>
            <div class="item">
                <span style="color:{COLOR_MUTED};">{ICONS['clock']}</span>
                <span>{last_refresh}</span>
            </div>
            <div class="item">
                <span style="color:{COLOR_GOLD};">{ICONS['trades']}</span>
                <span>{open_positions} open position{'s' if open_positions != 1 else ''}</span>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )


def sidebar_section_label(text: str):
    """Render a small uppercase section label in the sidebar."""
    st.sidebar.markdown(
        f'<p class="sidebar-section-label">{text}</p>',
        unsafe_allow_html=True,
    )


def sidebar_bot_header(name: str, symbol: str, active: bool = True):
    """Render a bot header with status dot in the sidebar."""
    dot_cls = "active" if active else "inactive"
    st.sidebar.markdown(
        f"""<div class="sidebar-bot-header">
            <span class="status-dot {dot_cls}"></span>
            {name}
            <span class="sidebar-bot-symbol">{symbol}</span>
        </div>""",
        unsafe_allow_html=True,
    )


def sidebar_divider():
    """Render a subtle divider in the sidebar."""
    st.sidebar.markdown('<hr class="sidebar-divider">', unsafe_allow_html=True)


def sidebar_stat(label: str, value: str):
    """Render a compact stat row in the sidebar."""
    st.sidebar.markdown(
        f"""<div class="sidebar-stat">
            <span class="label">{label}</span>
            <span class="value">{value}</span>
        </div>""",
        unsafe_allow_html=True,
    )


def format_pnl(value: float, is_pct: bool = False) -> str:
    """Format a P&L value with color."""
    color = COLOR_PROFIT if value >= 0 else COLOR_LOSS
    icon = ICONS["profit"] if value >= 0 else ICONS["loss"]
    if is_pct:
        text = f"{value:+.2f}%"
    else:
        text = f"${value:+.2f}"
    return f'<span style="color:{color};font-weight:600;">{icon} {text}</span>'


def footer_caption(text: str):
    """Render a centered footer caption."""
    st.markdown(f'<div class="footer-caption">{text}</div>', unsafe_allow_html=True)
