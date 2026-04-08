"""Bot Equity Curve page — account equity and cumulative return charts."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.theme import (
    COLOR_BLUE,
    COLOR_GOLD,
    COLOR_PROFIT,
    PLOTLY_CONFIG,
    apply_chart_style,
)

STARTING_CAPITAL = 500.0


def render_equity(db, bot_name: str = "GoldBot"):
    """Render the equity curve page for a single bot."""
    st.title(f"{bot_name} — Equity Curve")

    equity_data = db.get_equity_curve(1000)

    if equity_data:
        df = pd.DataFrame(equity_data)
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        # Ensure $500 starting balance is included as first data point
        first_ts = df["timestamp"].iloc[0]
        if df["equity"].iloc[0] != STARTING_CAPITAL:
            start_row = pd.DataFrame([{
                "timestamp": first_ts - pd.Timedelta(minutes=1),
                "equity": STARTING_CAPITAL,
                "balance": STARTING_CAPITAL,
                "unrealized_pnl": 0,
                "open_positions": 0,
            }])
            df = pd.concat([start_row, df], ignore_index=True)

        initial_equity = STARTING_CAPITAL
        df["return_pct"] = ((df["equity"] - initial_equity) / initial_equity) * 100

        # ── Equity & Balance Chart ────────────────────────────────────────────
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["timestamp"],
            y=df["equity"],
            mode="lines",
            name="Equity",
            line=dict(color=COLOR_GOLD, width=2.5),
            fill="tozeroy",
            fillcolor="rgba(255, 215, 0, 0.06)",
            hovertemplate="$%{y:,.2f}<extra>Equity</extra>",
        ))
        fig.add_trace(go.Scatter(
            x=df["timestamp"],
            y=df["balance"],
            mode="lines",
            name="Balance",
            line=dict(color=COLOR_BLUE, width=1.5, dash="dot"),
            hovertemplate="$%{y:,.2f}<extra>Balance</extra>",
        ))
        fig = apply_chart_style(fig, height=480)
        fig.update_layout(
            title=dict(text="Account Equity Over Time", font=dict(size=16)),
            xaxis_title="",
            yaxis_title="USD",
            yaxis=dict(tickprefix="$"),
        )
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

        # ── Cumulative Return Chart ───────────────────────────────────────────
        if "return_pct" in df.columns:
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=df["timestamp"],
                y=df["return_pct"],
                mode="lines",
                fill="tozeroy",
                name="Return %",
                line=dict(color=COLOR_PROFIT, width=2),
                fillcolor="rgba(0, 210, 106, 0.10)",
                hovertemplate="%{y:+.2f}%<extra>Return</extra>",
            ))
            fig2 = apply_chart_style(fig2, height=380)
            fig2.update_layout(
                title=dict(text="Cumulative Return %", font=dict(size=16)),
                xaxis_title="",
                yaxis_title="Return %",
                yaxis=dict(ticksuffix="%"),
            )
            fig2.add_hline(y=0, line_width=1, line_color="#2A3441")
            st.plotly_chart(fig2, use_container_width=True, config=PLOTLY_CONFIG)
    else:
        st.info("No equity data yet \u2014 start the bot to begin tracking")
