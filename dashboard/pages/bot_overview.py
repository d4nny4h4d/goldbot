"""Bot Overview page — key metrics, open positions, recent trades."""

import pandas as pd
import streamlit as st

from dashboard.components import section_header, status_bar
from dashboard.theme import COLOR_LOSS, COLOR_PROFIT


def render_overview(db, bot_name: str = "GoldBot"):
    """Render the overview page for a single bot."""
    st.title(f"{bot_name} — Overview")

    # ── Top metrics ───────────────────────────────────────────────────────────
    equity_data = db.get_equity_curve(1)
    current_equity = equity_data[-1]["equity"] if equity_data else 0
    current_balance = equity_data[-1]["balance"] if equity_data else 0

    today_trades = db.get_today_trades()
    closed_today = [t for t in today_trades if t["status"] == "closed"]
    today_pnl = sum(t.get("profit_usd", 0) or 0 for t in closed_today)
    # Use start-of-day equity (current minus today's P&L) for correct percentage
    start_of_day_equity = current_equity - today_pnl if current_equity > 0 else 500
    today_pnl_pct = (today_pnl / start_of_day_equity * 100) if start_of_day_equity > 0 else 0

    today_wins = sum(1 for t in closed_today if (t.get("profit_usd") or 0) > 0)
    today_losses = sum(1 for t in closed_today if (t.get("profit_usd") or 0) <= 0)

    open_trades = db.get_open_trades()

    # Status bar
    status_bar(
        bot_name=bot_name,
        is_active=True,
        last_refresh=equity_data[-1].get("timestamp", "—")[:19] if equity_data else "—",
        open_positions=len(open_trades),
    )

    # Key metrics row
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Equity", f"${current_equity:,.2f}")
    col2.metric("Balance", f"${current_balance:,.2f}")
    col3.metric("Today P&L", f"{today_pnl_pct:+.2f}%", f"${today_pnl:+.2f}")
    col4.metric("Open Positions", len(open_trades))

    st.markdown("---")

    # ── Today's breakdown ─────────────────────────────────────────────────────
    if closed_today:
        tc1, tc2, tc3 = st.columns(3)
        tc1.metric("Today Trades", len(closed_today))
        tc2.metric("Wins / Losses", f"{today_wins} / {today_losses}")
        today_wr = (today_wins / len(closed_today) * 100) if closed_today else 0
        tc3.metric("Today Win Rate", f"{today_wr:.0f}%")
        st.markdown("---")

    # ── Open Positions ────────────────────────────────────────────────────────
    section_header("trades", "Open Positions")
    if open_trades:
        df_open = pd.DataFrame(open_trades)
        display_cols = ["ticket", "direction", "lots", "entry_price", "sl", "tp", "strategy", "entry_time"]
        available_cols = [c for c in display_cols if c in df_open.columns]
        st.dataframe(df_open[available_cols], use_container_width=True, hide_index=True)
    else:
        st.info("No open positions")

    # ── Recent Closed Trades ──────────────────────────────────────────────────
    section_header("reports", "Recent Closed Trades")
    closed = db.get_closed_trades(10)
    if closed:
        df_closed = pd.DataFrame(closed)
        display_cols = [
            "ticket", "direction", "lots", "entry_price", "exit_price",
            "profit_usd", "profit_pct", "strategy", "exit_time",
        ]
        available_cols = [c for c in display_cols if c in df_closed.columns]

        # Color formatting for P&L columns
        def style_pnl(df):
            styles = pd.DataFrame("", index=df.index, columns=df.columns)
            if "profit_usd" in df.columns:
                styles["profit_usd"] = df["profit_usd"].apply(
                    lambda v: f"color: {COLOR_PROFIT}" if (v or 0) > 0 else f"color: {COLOR_LOSS}"
                )
            if "profit_pct" in df.columns:
                styles["profit_pct"] = df["profit_pct"].apply(
                    lambda v: f"color: {COLOR_PROFIT}" if (v or 0) > 0 else f"color: {COLOR_LOSS}"
                )
            return styles

        st.dataframe(
            df_closed[available_cols].style.apply(style_pnl, axis=None),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No closed trades yet")
