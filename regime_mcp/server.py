"""
Regime MCP Server — Expose market regime classification to AI agents.

Tools:
  - get_spy_regime: Current SPY regime (trending/mean-reverting/neutral) via HMM
  - get_regime_history: Historical regime data with transitions
  - get_volatility_regime: VIX-based vol regime (low/normal/high/extreme)
  - get_market_context: Combined regime + vol + key levels snapshot
"""

import json
import datetime as dt
from typing import Any

import yfinance as yf
import numpy as np
import pandas as pd

try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent
    HAS_MCP = True
except ImportError:
    HAS_MCP = False

# ---------------------------------------------------------------------------
# Regime Classification (simplified HMM-inspired approach using public data)
# ---------------------------------------------------------------------------

def _fetch_spy_data(days: int = 120) -> pd.DataFrame:
    """Fetch SPY OHLCV from Yahoo Finance."""
    end = dt.datetime.now()
    start = end - dt.timedelta(days=days)
    df = yf.download("SPY", start=start, end=end, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


def _fetch_vix(days: int = 120) -> pd.DataFrame:
    end = dt.datetime.now()
    start = end - dt.timedelta(days=days)
    df = yf.download("^VIX", start=start, end=end, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


def classify_regime(df: pd.DataFrame) -> dict:
    """
    Classify current market regime using:
    - 20-day return momentum
    - 20-day realized volatility
    - ADX-like directional metric
    - Mean reversion z-score
    """
    close = df["Close"].values.flatten()
    returns = np.diff(np.log(close))

    # Realized vol (20-day annualized)
    rv20 = float(np.std(returns[-20:]) * np.sqrt(252) * 100)

    # Momentum (20-day return)
    mom20 = float((close[-1] / close[-21] - 1) * 100) if len(close) > 21 else 0.0

    # Mean reversion z-score (price vs 20-day SMA)
    sma20 = float(np.mean(close[-20:]))
    std20 = float(np.std(close[-20:]))
    zscore = float((close[-1] - sma20) / std20) if std20 > 0 else 0.0

    # Classify
    if rv20 > 25:
        regime = "HIGH_VOLATILITY"
        description = "Elevated volatility — wide ranges, mean reversion likely"
    elif abs(mom20) > 3 and abs(zscore) > 1.0:
        regime = "TRENDING"
        direction = "BULLISH" if mom20 > 0 else "BEARISH"
        regime = f"TRENDING_{direction}"
        description = f"Strong {direction.lower()} trend — momentum strategies favored"
    elif abs(zscore) < 0.5 and rv20 < 15:
        regime = "LOW_VOL_NEUTRAL"
        description = "Quiet market — premium selling (PCS) optimal"
    else:
        regime = "NEUTRAL"
        description = "Mixed signals — balanced approach recommended"

    return {
        "regime": regime,
        "description": description,
        "metrics": {
            "realized_vol_20d": round(rv20, 2),
            "momentum_20d_pct": round(mom20, 2),
            "zscore_vs_sma20": round(zscore, 2),
            "sma20": round(sma20, 2),
            "last_close": round(float(close[-1]), 2),
        },
        "timestamp": dt.datetime.now().isoformat(),
        "trading_implications": _get_implications(regime, rv20),
    }


def classify_vol_regime(vix_df: pd.DataFrame) -> dict:
    """Classify volatility regime from VIX."""
    vix = float(vix_df["Close"].values.flatten()[-1])
    vix_20d_avg = float(np.mean(vix_df["Close"].values.flatten()[-20:]))

    if vix < 14:
        level = "LOW"
        desc = "Complacency — cheap options, premium selling less rewarding"
    elif vix < 20:
        level = "NORMAL"
        desc = "Healthy vol — good for premium selling strategies"
    elif vix < 30:
        level = "ELEVATED"
        desc = "Fear rising — wider strikes needed, juicy premiums"
    else:
        level = "EXTREME"
        desc = "Panic — cash is king, wait for mean reversion"

    return {
        "vix_level": level,
        "vix_current": round(vix, 2),
        "vix_20d_avg": round(vix_20d_avg, 2),
        "description": desc,
        "timestamp": dt.datetime.now().isoformat(),
    }


def _get_implications(regime: str, rv: float) -> list[str]:
    implications = []
    if "TRENDING" in regime:
        implications.append("Follow the trend — avoid counter-trend entries")
        implications.append("Tighten stops on mean-reversion positions")
    if "NEUTRAL" in regime or "LOW_VOL" in regime:
        implications.append("Put credit spreads (PCS) are optimal in this regime")
        implications.append("Sell premium — theta decay is your friend")
    if "HIGH_VOL" in regime:
        implications.append("Widen strikes on credit spreads")
        implications.append("Reduce position size — tail risk elevated")
    if rv < 12:
        implications.append("Consider buying cheap options for asymmetric bets")
    return implications


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

def create_server() -> "Server":
    server = Server("regime-mcp-server")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="get_spy_regime",
                description="Get current SPY market regime classification (trending/neutral/high-vol) with actionable trading implications.",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="get_volatility_regime",
                description="Get current VIX-based volatility regime (low/normal/elevated/extreme).",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="get_market_context",
                description="Full market context snapshot: regime + volatility + key metrics + trading implications. The all-in-one market briefing.",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="get_regime_history",
                description="Get regime classifications for the last N trading days.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "days": {
                            "type": "integer",
                            "description": "Number of trading days (default 10, max 60)",
                            "default": 10,
                        }
                    },
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        if name == "get_spy_regime":
            df = _fetch_spy_data()
            result = classify_regime(df)
        elif name == "get_volatility_regime":
            vdf = _fetch_vix()
            result = classify_vol_regime(vdf)
        elif name == "get_market_context":
            df = _fetch_spy_data()
            vdf = _fetch_vix()
            result = {
                "spy_regime": classify_regime(df),
                "vol_regime": classify_vol_regime(vdf),
                "summary": _build_summary(classify_regime(df), classify_vol_regime(vdf)),
            }
        elif name == "get_regime_history":
            days = min(arguments.get("days", 10), 60)
            df = _fetch_spy_data(days=days + 30)
            result = _regime_history(df, days)
        else:
            result = {"error": f"Unknown tool: {name}"}

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    return server


def _build_summary(regime: dict, vol: dict) -> str:
    r = regime["regime"]
    v = vol["vix_level"]
    close = regime["metrics"]["last_close"]
    vix = vol["vix_current"]
    return (
        f"SPY at ${close} | Regime: {r} | VIX: {vix} ({v}) | "
        f"RV20: {regime['metrics']['realized_vol_20d']}% | "
        f"Z-Score: {regime['metrics']['zscore_vs_sma20']}"
    )


def _regime_history(df: pd.DataFrame, days: int) -> dict:
    """Compute rolling regime for last N days."""
    close = df["Close"].values.flatten()
    dates = df.index[-days:]
    history = []
    for i in range(days):
        idx = len(close) - days + i
        if idx < 21:
            continue
        window = close[:idx + 1]
        rv = float(np.std(np.diff(np.log(window[-20:]))) * np.sqrt(252) * 100)
        mom = float((window[-1] / window[-21] - 1) * 100)
        sma = float(np.mean(window[-20:]))
        std = float(np.std(window[-20:]))
        z = float((window[-1] - sma) / std) if std > 0 else 0
        if rv > 25:
            reg = "HIGH_VOL"
        elif abs(mom) > 3 and abs(z) > 1.0:
            reg = f"TREND_{'UP' if mom > 0 else 'DN'}"
        elif abs(z) < 0.5 and rv < 15:
            reg = "LOW_VOL"
        else:
            reg = "NEUTRAL"
        history.append({
            "date": str(dates[i].date()) if hasattr(dates[i], 'date') else str(dates[i]),
            "regime": reg,
            "rv20": round(rv, 1),
            "mom20": round(mom, 1),
            "zscore": round(z, 2),
        })
    return {"history": history, "days": days}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    from mcp.server.stdio import stdio_server
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
