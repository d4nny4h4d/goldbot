"""Bot Calendar page — Tradefy-style monthly trade calendar with weekly summary."""

import calendar
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import streamlit as st

from dashboard.theme import (
    COLOR_BG,
    COLOR_BORDER,
    COLOR_CARD,
    COLOR_GOLD,
    COLOR_LOSS,
    COLOR_MUTED,
    COLOR_PROFIT,
    COLOR_TEXT,
)


def _get_trade_data_by_date(db) -> dict:
    """Group closed trades by exit date. Returns {date_str: {pnl, count, wins, losses}}."""
    trades = db.get_closed_trades(500)
    by_date = defaultdict(lambda: {"pnl": 0.0, "count": 0, "wins": 0, "losses": 0})

    for t in trades:
        exit_time = t.get("exit_time", "")
        if not exit_time:
            continue
        date_str = exit_time[:10]  # "YYYY-MM-DD"
        pnl = t.get("profit_usd", 0) or 0
        by_date[date_str]["pnl"] += pnl
        by_date[date_str]["count"] += 1
        if pnl > 0:
            by_date[date_str]["wins"] += 1
        else:
            by_date[date_str]["losses"] += 1

    return dict(by_date)


def _build_calendar_html(year: int, month: int, trade_data: dict, today_str: str) -> str:
    """Build an HTML calendar grid (Mon-Sun) with trade data overlay."""
    cal = calendar.Calendar(firstweekday=0)  # Monday first
    weeks = cal.monthdayscalendar(year, month)

    # Day headers (Mon-Sun)
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    header_cells = "".join(
        f'<div class="cal-header-cell">{d}</div>' for d in day_names
    )

    # Weekly summary data
    weekly_data = []

    rows_html = ""
    for week in weeks:
        week_pnl = 0.0
        week_trades = 0
        cells = ""

        for day in week:
            if day == 0:
                cells += '<div class="cal-cell empty"></div>'
                continue

            date_str = f"{year}-{month:02d}-{day:02d}"
            is_today = date_str == today_str
            data = trade_data.get(date_str)

            today_cls = " today" if is_today else ""

            if data:
                pnl = data["pnl"]
                count = data["count"]
                week_pnl += pnl
                week_trades += count

                pnl_color = COLOR_PROFIT if pnl >= 0 else COLOR_LOSS
                bg_color = "rgba(0,210,106,0.12)" if pnl >= 0 else "rgba(255,75,75,0.12)"
                border_color = "rgba(0,210,106,0.3)" if pnl >= 0 else "rgba(255,75,75,0.3)"

                cells += (
                    f'<div class="cal-cell has-trades{today_cls}" '
                    f'style="background:{bg_color};border-color:{border_color};">'
                    f'<span class="cal-day">{day}</span>'
                    f'<span class="cal-pnl" style="color:{pnl_color};">${pnl:+,.0f}</span>'
                    f'<span class="cal-count">{count} trade{"s" if count != 1 else ""}</span>'
                    f'</div>'
                )
            else:
                cells += (
                    f'<div class="cal-cell{today_cls}">'
                    f'<span class="cal-day">{day}</span>'
                    f'</div>'
                )

        rows_html += f'<div class="cal-row">{cells}</div>'
        weekly_data.append({"pnl": week_pnl, "trades": week_trades})

    return header_cells, rows_html, weekly_data


def _build_weekly_summary_html(weekly_data: list, month_name: str) -> str:
    """Build the vertical weekly summary strip."""
    rows = ""
    for i, week in enumerate(weekly_data):
        if week["trades"] == 0:
            rows += (
                f'<div class="week-row">'
                f'<span class="week-label">W{i+1}</span>'
                f'<span class="week-pnl" style="color:{COLOR_MUTED};">—</span>'
                f'<span class="week-count" style="color:{COLOR_MUTED};">0 trades</span>'
                f'</div>'
            )
        else:
            pnl = week["pnl"]
            pnl_color = COLOR_PROFIT if pnl >= 0 else COLOR_LOSS
            rows += (
                f'<div class="week-row">'
                f'<span class="week-label">W{i+1}</span>'
                f'<span class="week-pnl" style="color:{pnl_color};">${pnl:+,.0f}</span>'
                f'<span class="week-count">{week["trades"]} trade{"s" if week["trades"] != 1 else ""}</span>'
                f'</div>'
            )

    # Monthly total
    total_pnl = sum(w["pnl"] for w in weekly_data)
    total_trades = sum(w["trades"] for w in weekly_data)
    total_color = COLOR_PROFIT if total_pnl >= 0 else COLOR_LOSS

    return f"""
    <div class="weekly-summary">
        <div class="weekly-title">Weekly Summary</div>
        {rows}
        <div class="week-divider"></div>
        <div class="week-row total">
            <span class="week-label">{month_name}</span>
            <span class="week-pnl" style="color:{total_color};font-weight:700;">${total_pnl:+,.0f}</span>
            <span class="week-count">{total_trades} trades</span>
        </div>
    </div>
    """


def render_calendar(db, bot_name: str = "GoldBot"):
    """Render the Tradefy-style trade calendar."""

    # ── Month navigation ─────────────────────────────────────────────────────
    today = datetime.now(timezone.utc)
    today_str = today.strftime("%Y-%m-%d")

    if "cal_year" not in st.session_state:
        st.session_state.cal_year = today.year
    if "cal_month" not in st.session_state:
        st.session_state.cal_month = today.month

    year = st.session_state.cal_year
    month = st.session_state.cal_month
    month_name = calendar.month_name[month]

    # Navigation row
    nav_cols = st.columns([1, 1, 4, 1, 1, 2])
    with nav_cols[0]:
        if st.button("\u00AB", key="cal_prev_year", help="Previous year"):
            st.session_state.cal_year -= 1
            st.rerun()
    with nav_cols[1]:
        if st.button("\u2039", key="cal_prev_month", help="Previous month"):
            if st.session_state.cal_month == 1:
                st.session_state.cal_month = 12
                st.session_state.cal_year -= 1
            else:
                st.session_state.cal_month -= 1
            st.rerun()
    with nav_cols[2]:
        st.markdown(
            f"<div style='text-align:center;font-size:18px;font-weight:600;"
            f"color:{COLOR_TEXT};padding:6px 0;'>"
            f"{month_name} {year}</div>",
            unsafe_allow_html=True,
        )
    with nav_cols[3]:
        if st.button("\u203A", key="cal_next_month", help="Next month"):
            if st.session_state.cal_month == 12:
                st.session_state.cal_month = 1
                st.session_state.cal_year += 1
            else:
                st.session_state.cal_month += 1
            st.rerun()
    with nav_cols[4]:
        if st.button("\u00BB", key="cal_next_year", help="Next year"):
            st.session_state.cal_year += 1
            st.rerun()
    with nav_cols[5]:
        if st.button("Today", key="cal_today"):
            st.session_state.cal_year = today.year
            st.session_state.cal_month = today.month
            st.rerun()

    # ── Get trade data ───────────────────────────────────────────────────────
    trade_data = _get_trade_data_by_date(db)
    header_cells, rows_html, weekly_data = _build_calendar_html(year, month, trade_data, today_str)
    weekly_html = _build_weekly_summary_html(weekly_data, month_name[:3])

    # ── Calendar + Weekly Summary layout ─────────────────────────────────────
    cal_col, summary_col = st.columns([5, 1.5])

    with cal_col:
        st.markdown(
            f"""
            <div class="trade-calendar">
                <div class="cal-header-row">{header_cells}</div>
                {rows_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with summary_col:
        st.markdown(weekly_html, unsafe_allow_html=True)

    # ── Monthly stats below calendar ─────────────────────────────────────────
    month_dates = [d for d in trade_data if d.startswith(f"{year}-{month:02d}")]
    if month_dates:
        month_trades = sum(trade_data[d]["count"] for d in month_dates)
        month_pnl = sum(trade_data[d]["pnl"] for d in month_dates)
        month_wins = sum(trade_data[d]["wins"] for d in month_dates)
        month_losses = sum(trade_data[d]["losses"] for d in month_dates)
        win_rate = (month_wins / (month_wins + month_losses) * 100) if (month_wins + month_losses) > 0 else 0
        profit_days = sum(1 for d in month_dates if trade_data[d]["pnl"] > 0)
        loss_days = sum(1 for d in month_dates if trade_data[d]["pnl"] <= 0)

        st.markdown("---")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total Trades", month_trades)
        pnl_delta = f"${month_pnl:+,.2f}"
        m2.metric("Month P&L", f"${month_pnl:+,.2f}")
        m3.metric("Win Rate", f"{win_rate:.0f}%")
        m4.metric("Profit Days", f"{profit_days}")
        m5.metric("Loss Days", f"{loss_days}")
