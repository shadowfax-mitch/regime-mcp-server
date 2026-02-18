# 📊 Regime MCP Server

**Give your AI agent market awareness.** Real-time SPY regime classification, volatility analysis, and trading context — via MCP.

> No more asking "what's the market doing?" — your AI already knows.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-compatible-green.svg)](https://modelcontextprotocol.io)

---

## Why?

AI trading assistants are blind to market context. They'll suggest the same strategy whether VIX is at 12 or 40. This server fixes that.

**Regime MCP** classifies the current market into actionable states:
- 🟢 **LOW_VOL_NEUTRAL** → Sell premium, put credit spreads shine
- 🔵 **TRENDING_BULLISH/BEARISH** → Follow momentum, avoid mean reversion
- 🟡 **NEUTRAL** → Mixed signals, balanced approach
- 🔴 **HIGH_VOLATILITY** → Widen strikes, reduce size, respect tail risk

## Tools

| Tool | Description |
|------|-------------|
| `get_spy_regime` | Current regime + metrics + trading implications |
| `get_volatility_regime` | VIX-based vol classification |
| `get_market_context` | All-in-one market briefing (regime + vol + summary) |
| `get_regime_history` | Last N days of regime data with transitions |

## Quick Start

```bash
# Install
pip install regime-mcp-server

# Or from source
git clone https://github.com/shadowfax-mitch/regime-mcp-server
cd regime-mcp-server
pip install -e .
```

### Claude Desktop Config

```json
{
  "mcpServers": {
    "regime": {
      "command": "python",
      "args": ["-m", "regime_mcp.server"]
    }
  }
}
```

## Example Output

```
Ask Claude: "What's the current market regime?"

→ SPY at $602.34 | Regime: LOW_VOL_NEUTRAL | VIX: 15.2 (NORMAL)
  RV20: 11.3% | Z-Score: 0.12
  
  Trading implications:
  • Put credit spreads (PCS) are optimal in this regime
  • Sell premium — theta decay is your friend
  • Consider buying cheap options for asymmetric bets
```

## How It Works

Regime classification uses:
- **20-day realized volatility** — actual market movement
- **20-day momentum** — directional strength
- **Z-score vs SMA(20)** — mean reversion signal
- **VIX level** — implied vol / fear gauge

No paid data feeds required — uses Yahoo Finance for real-time data.

## Roadmap

- [ ] **v0.2** — Intraday regime updates (5-min bars)
- [ ] **v0.3** — Multi-asset regimes (QQQ, IWM, crypto)
- [ ] **v0.4** — HMM-based classification (upgrade from rules)
- [ ] **v0.5** — Premium tier: fractal analysis, PCS signal generation

## Built By

[Sentinel Global Enterprises](https://sentinel-algo.com) — AI-powered trading systems.

Follow [@Sentinel_Algo](https://x.com/Sentinel_Algo) for market regime updates.
