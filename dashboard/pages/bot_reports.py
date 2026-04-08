"""Bot Daily Reports page — daily P&L bar chart and summary stats."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.theme import (
    COLOR_GOLD,
    COLOR_LOSS,
    COLOR_PROFIT,
    PLOTLY_CONFIG,
    apply_chart_style,
)


def render_reports(db, bot_name: str = "GoldBot"):
    """Render the daily reports page for a single bot."""
    st.title(f"{bot_name} — Daily Reports")

    summaries = db.get_daily_summaries(60)

    if summaries:
        df = pd.DataFrame(summaries)

        # ── Daily P&L Bar Chart ───────────────────────────────────────────────
        fig = go.Figure()
        colors = [COLOR_PROFIT if x >= 0 else COLOR_LOSS for x in df["pnl_pct"]]
        fig.add_trace(go.Bar(
            x=df["date"],
            y=df["pnl_pct"],
            marker_color=colors,
            name="Daily P&L %",
            hovertemplate="%{x}<br>P&L: %{y:+.2f}%<extra></extra>",
        ))

        # Rolling average overlay
        if len(df) >= 5:
            rolling_avg = df["pnl_pct"].rolling(5, min_periods=1).mean()
            fig.add_trace(go.Scatter(
                x=df["date"],
                y=rolling_avg,
                mode="lines",
                name="5-Day Avg",
                line=dict(color=COLOR_GOLD, width=2, dash="dot"),
                hovertemplate="%{y:+.2f}%<extra>5-Day Avg</extra>",
            ))

        fig = apply_chart_style(fig, height=400)
        fig.update_layout(
            title=dict(text="Daily P&L %", font=dict(size=16)),
            xaxis_title="",
            yaxis_title="P&L %",
            yaxis=dict(ticksuffix="%"),
            showlegend=True,
        )
        fig.add_hline(y=0, line_width=1, line_color="#2A3441")
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

        # ── Summary Metrics ───────────────────────────────────────────────────
        col1, col2, col3, col4 = st.columns(4)
        positive_days = sum(1 for s in summaries if s["pnl_pct"] > 0)
        col1.metric("Positive Days", f"{positive_days}/{len(summaries)}")
        avg_pnl = sum(s["pnl_pct"] for s in summaries) / len(summaries)
        col2.metric("Avg Daily P&L", f"{avg_pnl:+.2f}%")
        best = max(s["pnl_pct"] for s in summaries)
        col3.metric("Best Day", f"{best:+.2f}%")
        worst = min(s["pnl_pct"] for s in summaries)
        col4.metric("Worst Day", f"{worst:+.2f}%")

        # ── Full table ────────────────────────────────────────────────────────
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No daily summaries yet")
