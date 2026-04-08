"""Portfolio pages — aggregated view across all bots."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.components import section_header
from dashboard.theme import (
    COLOR_BLUE,
    COLOR_GOLD,
    COLOR_LOSS,
    COLOR_MUTED,
    COLOR_PROFIT,
    COLOR_PURPLE,
    PLOTLY_CONFIG,
    apply_chart_style,
)


# Colors for multi-bot charts
BOT_COLORS = [COLOR_GOLD, COLOR_BLUE, COLOR_PURPLE, COLOR_PROFIT]


def render_portfolio_overview(bots: dict):
    """Aggregated overview across all bots.

    Args:
        bots: dict of {bot_id: {"name", "symbol", "db", "active"}}
    """
    st.title("Portfolio Overview")

    # ── Aggregate metrics ─────────────────────────────────────────────────────
    total_equity = 0
    total_balance = 0
    total_today_pnl = 0
    total_open = 0
    bot_rows = []

    for bot_id, bot in bots.items():
        db = bot["db"]
        equity_data = db.get_equity_curve(1)
        equity = equity_data[-1]["equity"] if equity_data else 0
        balance = equity_data[-1]["balance"] if equity_data else 0

        today_trades = db.get_today_trades()
        closed_today = [t for t in today_trades if t["status"] == "closed"]
        today_pnl = sum(t.get("profit_usd", 0) or 0 for t in closed_today)
        open_count = len(db.get_open_trades())

        start_eq = equity - today_pnl if equity > 0 else 0
        today_pnl_pct = (today_pnl / start_eq * 100) if start_eq > 0 else 0

        total_equity += equity
        total_balance += balance
        total_today_pnl += today_pnl
        total_open += open_count

        status = "Active" if bot["active"] else "Inactive"
        bot_rows.append({
            "Bot": bot["name"],
            "Symbol": bot["symbol"],
            "Equity": f"${equity:,.2f}",
            "Today P&L": f"{today_pnl_pct:+.2f}%",
            "Open": open_count,
            "Status": status,
        })

    total_start = total_equity - total_today_pnl if total_equity > 0 else 0
    total_today_pnl_pct = (total_today_pnl / total_start * 100) if total_start > 0 else 0

    # ── Top metrics ───────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Equity", f"${total_equity:,.2f}")
    col2.metric("Total Balance", f"${total_balance:,.2f}")
    col3.metric("Today P&L", f"{total_today_pnl_pct:+.2f}%", f"${total_today_pnl:+.2f}")
    col4.metric("Active Bots", f"{sum(1 for b in bots.values() if b['active'])}/{len(bots)}")

    st.markdown("---")

    # ── Bot Summary Table ─────────────────────────────────────────────────────
    section_header("portfolio", "Bot Summary")
    if bot_rows:
        st.dataframe(pd.DataFrame(bot_rows), use_container_width=True, hide_index=True)

    # ── Allocation Chart ──────────────────────────────────────────────────────
    if len(bots) > 1:
        section_header("performance", "Allocation")
        equities = []
        labels = []
        for bot_id, bot in bots.items():
            db = bot["db"]
            eq_data = db.get_equity_curve(1)
            eq = eq_data[-1]["equity"] if eq_data else 0
            equities.append(eq)
            labels.append(bot["name"])

        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=equities,
            hole=0.55,
            marker=dict(colors=BOT_COLORS[:len(bots)]),
            textinfo="label+percent",
            textfont=dict(color="#FAFAFA"),
        )])
        fig = apply_chart_style(fig, height=350)
        fig.update_layout(
            title=dict(text="Portfolio Allocation", font=dict(size=16)),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)


def render_portfolio_performance(bots: dict):
    """Aggregated performance metrics and combined equity curve.

    Args:
        bots: dict of {bot_id: {"name", "symbol", "db", "active"}}
    """
    st.title("Portfolio Performance")

    # ── Per-bot performance stats ─────────────────────────────────────────────
    section_header("performance", "Performance by Bot")
    perf_rows = []
    for bot_id, bot in bots.items():
        db = bot["db"]
        perf = db.get_performance_stats()
        perf_rows.append({
            "Bot": bot["name"],
            "Symbol": bot["symbol"],
            "Total Trades": perf["total_trades"],
            "Win Rate": f"{perf['win_rate_pct']}%",
            "Profit Factor": f"{perf['profit_factor']:.2f}" if perf["profit_factor"] != float("inf") else "N/A",
            "Total Return": f"{perf['total_pnl_pct']}%",
            "Avg Win": f"{perf['avg_win_pct']}%",
            "Avg Loss": f"{perf['avg_loss_pct']}%",
        })

    if perf_rows:
        st.dataframe(pd.DataFrame(perf_rows), use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── Combined Equity Curve ─────────────────────────────────────────────────
    section_header("equity", "Combined Equity Curve")

    fig = go.Figure()
    for i, (bot_id, bot) in enumerate(bots.items()):
        db = bot["db"]
        equity_data = db.get_equity_curve(1000)
        if equity_data:
            df = pd.DataFrame(equity_data)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            color = BOT_COLORS[i % len(BOT_COLORS)]
            fig.add_trace(go.Scatter(
                x=df["timestamp"],
                y=df["equity"],
                mode="lines",
                name=bot["name"],
                line=dict(color=color, width=2),
                hovertemplate="$%{y:,.2f}<extra>" + bot["name"] + "</extra>",
            ))

    if fig.data:
        fig = apply_chart_style(fig, height=480)
        fig.update_layout(
            title=dict(text="Equity Over Time", font=dict(size=16)),
            xaxis_title="",
            yaxis_title="USD",
            yaxis=dict(tickprefix="$"),
        )
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
    else:
        st.info("No equity data yet")
