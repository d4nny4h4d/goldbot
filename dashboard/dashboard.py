"""AhadAI Trading Hub — multi-bot dashboard with dark gold theme."""

import sys
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.db.database import Database

from dashboard.theme import CUSTOM_CSS, ICONS
from dashboard.components import (
    footer_caption,
    sidebar_divider,
    sidebar_section_label,
    sidebar_stat,
)
from dashboard.pages.bot_overview import render_overview
from dashboard.pages.bot_trades import render_trades
from dashboard.pages.bot_equity import render_equity
from dashboard.pages.bot_reports import render_reports
from dashboard.pages.bot_calendar import render_calendar
from dashboard.pages.portfolio import render_portfolio_overview, render_portfolio_performance

# ── Page Config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="AhadAI Trading Hub",
    page_icon="\u25C8",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject custom CSS
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ── Bot Registry ──────────────────────────────────────────────────────────────
# To add a new bot: add an entry here with its own db_path.
# Each bot gets its own SQLite database — no schema changes needed.

BOT_REGISTRY = {
    "goldbot": {
        "name": "GoldBot",
        "symbol": "XAU/USD",
        "db_path": "data/goldbot.db",
        "active": True,
    },
    "hft_london_1pct": {
        "name": "HFT London 1%",
        "symbol": "XAU/USD (M1)",
        "db_path": str(PROJECT_ROOT.parent / "HFTbot" / "data" / "hft_london_1pct.db"),
        "active": True,
    },
    "hft_london_2pct": {
        "name": "HFT London 2%",
        "symbol": "XAU/USD (M1)",
        "db_path": str(PROJECT_ROOT.parent / "HFTbot" / "data" / "hft_london_2pct.db"),
        "active": True,
    },
    "hft_ldnny_1pct": {
        "name": "HFT LDN+NY 1%",
        "symbol": "XAU/USD (M1)",
        "db_path": str(PROJECT_ROOT.parent / "HFTbot" / "data" / "hft_ldnny_1pct.db"),
        "active": True,
    },
}


@st.cache_resource
def get_db(db_path: str):
    """Get or create a Database instance per bot."""
    return Database(db_path)


def get_bots():
    bots = {}
    for bot_id, cfg in BOT_REGISTRY.items():
        bots[bot_id] = {
            **cfg,
            "db": get_db(cfg["db_path"]),
        }
    return bots


BOTS = get_bots()

# ── Page definitions per bot ─────────────────────────────────────────────────

BOT_PAGES = {
    "overview":  {"label": f"{ICONS['overview']}  Overview",      "icon": "overview"},
    "trades":    {"label": f"{ICONS['trades']}  Trades",          "icon": "trades"},
    "calendar":  {"label": f"{ICONS['clock']}  Calendar",         "icon": "clock"},
    "equity":    {"label": f"{ICONS['equity']}  Equity Curve",    "icon": "equity"},
    "reports":   {"label": f"{ICONS['reports']}  Daily Reports",  "icon": "reports"},
}

# ── Session State ─────────────────────────────────────────────────────────────

if "selected_page" not in st.session_state:
    st.session_state.selected_page = "portfolio_overview"

# ── Sidebar ───────────────────────────────────────────────────────────────────


def render_sidebar():
    """Build the sidebar with AhadAI branding, portfolio nav, and collapsible bot sections."""

    # ── AhadAI title (gold) ────────────────────────────────────────────────
    st.sidebar.markdown(
        "<div style='padding:4px 14px 4px 14px;'>"
        "<span style='color:#FFD700;font-size:20px;font-weight:700;'>"
        f"{ICONS['hub']}  AhadAI Trading Hub</span></div>",
        unsafe_allow_html=True,
    )

    # ── Dashboard subtitle (white) ─────────────────────────────────────────
    st.sidebar.markdown(
        "<div style='padding:0 14px 8px 14px;'>"
        "<span style='color:#FAFAFA;font-size:13px;font-weight:500;'>"
        "Dashboard</span></div>",
        unsafe_allow_html=True,
    )

    sidebar_divider()

    # ── Portfolio section ──────────────────────────────────────────────────
    sidebar_section_label("PORTFOLIO")
    portfolio_pages = {
        "portfolio_overview": f"{ICONS['portfolio']}  All Bots Overview",
        "portfolio_performance": f"{ICONS['performance']}  Performance",
    }
    for page_id, label in portfolio_pages.items():
        if st.sidebar.button(label, key=f"nav_{page_id}", use_container_width=True):
            st.session_state.selected_page = page_id
            st.rerun()

    sidebar_divider()

    # ── Bot sections (collapsible) ────────────────────────────────────────
    for bot_id, bot_cfg in BOT_REGISTRY.items():
        is_active = bot_cfg["active"]
        dot = "\u25CF" if is_active else "\u25CB"
        dot_color = "#00D26A" if is_active else "#8B95A5"

        label = f"{dot} {bot_cfg['name']}  \u2014  {bot_cfg['symbol']}"

        with st.sidebar.expander(label, expanded=False):
            for page_key, page_info in BOT_PAGES.items():
                page_id = f"{bot_id}_{page_key}"
                if st.button(
                    page_info["label"],
                    key=f"nav_{page_id}",
                    use_container_width=True,
                ):
                    st.session_state.selected_page = page_id
                    st.rerun()

    sidebar_divider()

    # ── Account Stats ─────────────────────────────────────────────────────
    sidebar_section_label("ACCOUNT")
    total_equity = 0
    for bot_id, bot in BOTS.items():
        db = bot["db"]
        perf = db.get_performance_stats()
        equity_data = db.get_equity_curve(1)
        equity = equity_data[-1]["equity"] if equity_data else 0
        total_equity += equity

        sidebar_stat(f"{bot['name']}", f"${equity:,.2f}")

    if len(BOTS) > 1:
        sidebar_stat("Total Equity", f"${total_equity:,.2f}")


# ── Page Routing ──────────────────────────────────────────────────────────────

def route_page():
    """Dispatch to the correct page based on session state."""
    page = st.session_state.selected_page

    # Portfolio pages
    if page == "portfolio_overview":
        render_portfolio_overview(BOTS)
        return
    if page == "portfolio_performance":
        render_portfolio_performance(BOTS)
        return

    for bot_id, bot in BOTS.items():
        prefix = f"{bot_id}_"
        if page.startswith(prefix):
            subpage = page[len(prefix):]
            db = bot["db"]
            name = bot["name"]

            if subpage == "overview":
                render_overview(db, bot_name=name)
            elif subpage == "trades":
                render_trades(db, bot_name=name)
            elif subpage == "calendar":
                render_calendar(db, bot_name=name)
            elif subpage == "equity":
                render_equity(db, bot_name=name)
            elif subpage == "reports":
                render_reports(db, bot_name=name)
            return

    # Fallback — portfolio overview
    render_portfolio_overview(BOTS)


# ── Auto-refresh fragment ─────────────────────────────────────────────────────

@st.fragment(run_every=15)
def live_section():
    """Auto-refreshing content — updates data without full page reload."""
    route_page()
    footer_caption(
        f"AhadAI Trading Hub v1.0  \u2502  "
        f"Last refresh: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )


# ── Main ──────────────────────────────────────────────────────────────────────

render_sidebar()
live_section()
