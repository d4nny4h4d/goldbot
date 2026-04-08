"""Bot Trades page — trade history with P&L distribution chart."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.theme import (
    COLOR_LOSS,
    COLOR_PROFIT,
    PLOTLY_CONFIG,
    apply_chart_style,
)


def render_trades(db, bot_name: str = "GoldBot"):
    """Render the trade history page for a single bot."""
    st.title(f"{bot_name} — Trade History")

    n_trades = st.slider("Number of trades", 10, 200, 50, key="trades_slider")
    trades = db.get_closed_trades(n_trades)

    if trades:
        df = pd.DataFrame(trades)

        # ── Summary metrics ───────────────────────────────────────────────────
        col1, col2, col3 = st.columns(3)
        wins = [t for t in trades if (t.get("profit_usd") or 0) > 0]
        losses = [t for t in trades if (t.get("profit_usd") or 0) <= 0]

        col1.metric("Trades Shown", len(trades))
        col2.metric("Wins / Losses", f"{len(wins)} / {len(losses)}")
        total_pct = sum(t.get("profit_pct", 0) or 0 for t in trades)
        col3.metric("Total Return %", f"{total_pct:+.2f}%")

        # ── P&L Distribution Chart ────────────────────────────────────────────
        if "profit_pct" in df.columns:
            fig = go.Figure()
            colors = [COLOR_PROFIT if x > 0 else COLOR_LOSS for x in df["profit_pct"].fillna(0)]
            fig.add_trace(go.Bar(
                x=list(range(1, len(df) + 1)),
                y=df["profit_pct"].fillna(0),
                marker_color=colors,
                name="Trade P&L %",
                hovertemplate="Trade #%{x}<br>P&L: %{y:.2f}%<extra></extra>",
            ))
            fig = apply_chart_style(fig, height=380)
            fig.update_layout(
                title=dict(text="Trade P&L Distribution", font=dict(size=16)),
                xaxis_title="Trade #",
                yaxis_title="P&L %",
                xaxis=dict(dtick=max(1, len(df) // 20)),
                showlegend=False,
            )
            # Zero line
            fig.add_hline(y=0, line_width=1, line_color="#2A3441")
            st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

        # ── Full trade table ──────────────────────────────────────────────────
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No trade history available")
