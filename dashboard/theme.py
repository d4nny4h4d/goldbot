"""Theme constants — colors, icons, CSS, and Plotly template for the dashboard."""

import plotly.graph_objects as go

# ── Color Palette ─────────────────────────────────────────────────────────────

COLOR_BG = "#0E1117"
COLOR_CARD = "#1E2530"
COLOR_BORDER = "#2A3441"
COLOR_GOLD = "#FFD700"
COLOR_GOLD_DIM = "#BFA100"
COLOR_PROFIT = "#00D26A"
COLOR_LOSS = "#FF4B4B"
COLOR_TEXT = "#FAFAFA"
COLOR_MUTED = "#8B95A5"
COLOR_BLUE = "#4B9EFF"
COLOR_PURPLE = "#A78BFA"

# ── Line Icons (Unicode) ─────────────────────────────────────────────────────

ICONS = {
    # Navigation
    "hub":          "\u25C8",   # ◈
    "portfolio":    "\u25A1",   # □
    "performance":  "\u25B3",   # △
    "overview":     "\u25CB",   # ○
    "trades":       "\u2261",   # ≡
    "equity":       "\u2197",   # ↗
    "reports":      "\u25A4",   # ▤
    # Status
    "active":       "\u25CF",   # ●
    "inactive":     "\u25CB",   # ○
    # P&L
    "profit":       "\u25B2",   # ▲
    "loss":         "\u25BC",   # ▼
    # Misc
    "clock":        "\u25F7",   # ◷
    "connected":    "\u25C9",   # ◉
    "disconnected": "\u25CE",   # ◎
}

# ── Custom CSS ────────────────────────────────────────────────────────────────

CUSTOM_CSS = """
<style>
/* ── Global ─────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Push content up — remove Streamlit's default top padding */
.stMainBlockContainer, [data-testid="stMainBlockContainer"] {
    padding-top: 0 !important;
}
[data-testid="stAppViewBlockContainer"] {
    padding-top: 0 !important;
}
.stApp > div:first-child {
    padding-top: 0 !important;
}
section[data-testid="stSidebar"] {
    padding-top: 0 !important;
}
section[data-testid="stSidebar"] > div {
    padding-top: 0 !important;
}
section[data-testid="stSidebar"] > div:first-child {
    padding-top: 0 !important;
}

h1 {
    font-size: 26px !important;
    font-weight: 600 !important;
    letter-spacing: -0.3px;
    color: #FAFAFA !important;
}

h2, h3 {
    font-size: 18px !important;
    font-weight: 600 !important;
    color: #FAFAFA !important;
}

hr {
    border-color: #2A3441 !important;
    margin: 1rem 0 !important;
}

/* ── Metric Cards ───────────────────────────────────── */
div[data-testid="stMetric"] {
    background: #1E2530;
    border: 1px solid #2A3441;
    border-radius: 10px;
    padding: 14px 18px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
    overflow: visible;
}

div[data-testid="stMetric"] label {
    color: #8B95A5 !important;
    font-size: 9px !important;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    white-space: nowrap !important;
    overflow: visible !important;
    text-overflow: unset !important;
}

div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
    font-size: 16px !important;
    font-weight: 700 !important;
    color: #FAFAFA !important;
    white-space: nowrap !important;
    overflow: visible !important;
    text-overflow: unset !important;
    display: inline !important;
}

/* Place delta tag inline to the right of the value */
div[data-testid="stMetric"] > div:last-child {
    display: flex !important;
    flex-direction: row !important;
    align-items: baseline !important;
    gap: 8px !important;
}

div[data-testid="stMetric"] div[data-testid="stMetricDelta"] {
    white-space: nowrap !important;
    overflow: visible !important;
    text-overflow: unset !important;
    font-size: 10px !important;
}

/* ── Sidebar ────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: #0A0E14 !important;
    border-right: 1px solid #2A3441;
}

/* Style sidebar buttons as clean nav items */
section[data-testid="stSidebar"] button[kind="secondary"] {
    background: transparent !important;
    border: none !important;
    border-left: 3px solid transparent !important;
    border-radius: 0 6px 6px 0 !important;
    color: #8B95A5 !important;
    font-size: 13.5px !important;
    font-weight: 500 !important;
    text-align: left !important;
    padding: 8px 14px !important;
    transition: all 0.15s ease;
    justify-content: flex-start !important;
}

section[data-testid="stSidebar"] button[kind="secondary"]:hover {
    background: rgba(255, 215, 0, 0.06) !important;
    color: #FAFAFA !important;
    border-color: transparent !important;
}

section[data-testid="stSidebar"] button[kind="secondary"]:focus {
    background: rgba(255, 215, 0, 0.10) !important;
    color: #FFD700 !important;
    border-left: 3px solid #FFD700 !important;
    font-weight: 600 !important;
    box-shadow: none !important;
}

section[data-testid="stSidebar"] button[kind="secondary"]:active {
    background: rgba(255, 215, 0, 0.10) !important;
    color: #FFD700 !important;
}

/* ── Sidebar Section Labels ─────────────────────────── */
.sidebar-section-label {
    color: #8B95A5;
    font-size: 10.5px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    padding: 12px 14px 4px 14px;
    margin: 0;
}

.sidebar-bot-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 14px 4px 14px;
    color: #FAFAFA;
    font-size: 14px;
    font-weight: 600;
}

.sidebar-bot-header .status-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 2px;
}

.sidebar-bot-header .status-dot.active {
    background: #00D26A;
    box-shadow: 0 0 6px rgba(0, 210, 106, 0.4);
}

.sidebar-bot-header .status-dot.inactive {
    background: #8B95A5;
}

.sidebar-bot-symbol {
    color: #8B95A5;
    font-size: 11px;
    font-weight: 400;
    margin-left: 4px;
}

.sidebar-divider {
    border: none;
    border-top: 1px solid #2A3441;
    margin: 8px 14px;
}

/* ── Sidebar Stats (bottom) ─────────────────────────── */
.sidebar-stat {
    display: flex;
    justify-content: space-between;
    padding: 4px 14px;
    font-size: 12px;
}

.sidebar-stat .label {
    color: #8B95A5;
}

.sidebar-stat .value {
    color: #FAFAFA;
    font-weight: 600;
}

/* ── DataFrames ─────────────────────────────────────── */
div[data-testid="stDataFrame"] {
    border: 1px solid #2A3441;
    border-radius: 8px;
    overflow: hidden;
}

/* ── Status Bar ─────────────────────────────────────── */
.status-bar {
    display: flex;
    align-items: center;
    gap: 20px;
    padding: 8px 16px;
    background: #1E2530;
    border: 1px solid #2A3441;
    border-radius: 8px;
    margin-bottom: 16px;
    font-size: 13px;
    color: #8B95A5;
}

.status-bar .item {
    display: flex;
    align-items: center;
    gap: 6px;
}

.status-bar .dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    display: inline-block;
}

.status-bar .dot.green { background: #00D26A; box-shadow: 0 0 4px rgba(0,210,106,0.4); }
.status-bar .dot.red { background: #FF4B4B; }
.status-bar .dot.gold { background: #FFD700; }

/* ── Page Footer ────────────────────────────────────── */
.footer-caption {
    text-align: center;
    color: #8B95A5;
    font-size: 11px;
    padding: 20px 0 8px 0;
    letter-spacing: 0.3px;
}

/* ── Hide ALL Streamlit chrome ──────────────────────── */
#MainMenu {display: none !important;}
footer {display: none !important;}
header {display: none !important;}

/* Hide auto-generated page navigation (fallback if config doesn't work) */
[data-testid="stSidebarNav"] {display: none !important;}
nav[data-testid="stSidebarNav"] {display: none !important;}
ul[data-testid="stSidebarNavItems"] {display: none !important;}

/* ── Expander styling (main content) ───────────────── */
div[data-testid="stExpander"] {
    border: 1px solid #2A3441 !important;
    border-radius: 8px !important;
    background: #1E2530 !important;
}

/* ── Sidebar expander styling (bot nav) ────────────── */
section[data-testid="stSidebar"] div[data-testid="stExpander"] {
    border: 1px solid #2A3441 !important;
    border-radius: 8px !important;
    background: #0A0E14 !important;
    margin-bottom: 4px !important;
}

section[data-testid="stSidebar"] div[data-testid="stExpander"] summary {
    color: #FAFAFA !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    padding: 8px 12px !important;
}

section[data-testid="stSidebar"] div[data-testid="stExpander"] summary:hover {
    color: #FFD700 !important;
}

section[data-testid="stSidebar"] div[data-testid="stExpander"] div[data-testid="stExpanderDetails"] {
    padding: 0 4px 4px 4px !important;
}

/* ── Plotly charts ──────────────────────────────────── */
div[data-testid="stPlotlyChart"] {
    border: 1px solid #2A3441;
    border-radius: 8px;
    overflow: hidden;
}

/* ── Trade Calendar ────────────────────────────────── */
.trade-calendar {
    border: 1px solid #2A3441;
    border-radius: 10px;
    background: #1E2530;
    padding: 12px;
    overflow: hidden;
}

.cal-header-row {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 4px;
    margin-bottom: 4px;
}

.cal-header-cell {
    text-align: center;
    color: #8B95A5;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    padding: 6px 0;
}

.cal-row {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 4px;
    margin-bottom: 4px;
}

.cal-cell {
    aspect-ratio: 1.3;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 6px 8px;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    justify-content: flex-start;
    min-height: 70px;
    transition: all 0.15s ease;
}

.cal-cell:hover:not(.empty) {
    border-color: #FFD700;
    box-shadow: 0 0 8px rgba(255,215,0,0.1);
}

.cal-cell.empty {
    background: transparent;
}

.cal-cell.today {
    border-color: #FFD700 !important;
    box-shadow: 0 0 10px rgba(255,215,0,0.15);
}

.cal-cell.today .cal-day {
    background: #FFD700;
    color: #0E1117;
    border-radius: 50%;
    width: 22px;
    height: 22px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
}

.cal-day {
    color: #FAFAFA;
    font-size: 12px;
    font-weight: 500;
    margin-bottom: 4px;
}

.cal-pnl {
    font-size: 14px;
    font-weight: 700;
    line-height: 1.2;
}

.cal-count {
    font-size: 10px;
    color: #8B95A5;
    margin-top: 2px;
}

.cal-cell.has-trades {
    border: 1px solid;
}

/* ── Weekly Summary Strip ──────────────────────────── */
.weekly-summary {
    border: 1px solid #2A3441;
    border-radius: 10px;
    background: #1E2530;
    padding: 14px;
}

.weekly-title {
    color: #8B95A5;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 12px;
    text-align: center;
}

.week-row {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 8px 0;
    border-bottom: 1px solid #2A3441;
}

.week-row:last-child {
    border-bottom: none;
}

.week-row.total {
    padding-top: 10px;
}

.week-label {
    color: #8B95A5;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.week-pnl {
    font-size: 15px;
    font-weight: 700;
    margin: 2px 0;
}

.week-count {
    font-size: 10px;
    color: #8B95A5;
}

.week-divider {
    border-top: 2px solid #FFD700;
    margin: 4px 0;
    opacity: 0.3;
}
</style>
"""

# ── Plotly Template ───────────────────────────────────────────────────────────

PLOTLY_LAYOUT = dict(
    paper_bgcolor=COLOR_BG,
    plot_bgcolor=COLOR_BG,
    font=dict(color=COLOR_TEXT, family="Inter, sans-serif", size=12),
    xaxis=dict(
        gridcolor=COLOR_BORDER,
        zerolinecolor=COLOR_BORDER,
        showline=False,
        tickfont=dict(color=COLOR_MUTED, size=11),
    ),
    yaxis=dict(
        gridcolor=COLOR_BORDER,
        zerolinecolor=COLOR_BORDER,
        showline=False,
        tickfont=dict(color=COLOR_MUTED, size=11),
    ),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLOR_MUTED, size=11),
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="left",
        x=0,
    ),
    margin=dict(l=20, r=20, t=50, b=20),
    hoverlabel=dict(
        bgcolor=COLOR_CARD,
        font_color=COLOR_TEXT,
        bordercolor=COLOR_BORDER,
    ),
)

PLOTLY_CONFIG = {"displayModeBar": False}


def apply_chart_style(fig: go.Figure, height: int = 420) -> go.Figure:
    """Apply the dark gold theme to any Plotly figure."""
    fig.update_layout(**PLOTLY_LAYOUT, height=height)
    return fig
