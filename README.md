# Options Gamma Exposure (GEX) Dashboard

A real-time Streamlit dashboard for monitoring options gamma exposure (GEX), volume, and open interest using the Tastytrade API and dxFeed WebSocket.

**Supports:** SPX, NDX, SPY, QQQ, IWM, DIA, and custom symbols

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-Latest-red)

---

## Quick Start

### Prerequisites

1. **Python 3.8+** - [Download here](https://www.python.org/downloads/)
   - Check "Add Python to PATH" during installation

2. **Tastytrade Account with API Access**
   - [Sign up at tastytrade.com](https://tastytrade.com)

### Installation

**Option 1: Easy Install (Windows)**
```bash
# Double-click to install everything automatically:
install_requirements.bat
```

**Option 2: Manual Install**
```bash
pip install -r requirements.txt
copy .env.example .env
# Edit .env with your credentials
start_simple_dashboard.bat
```

Dashboard opens at: **http://localhost:8501**

---

## Try the Demo (No API Required!)

```bash
start_demo_dashboard.bat
```

- No API credentials needed
- SPX and SPY confirmed working
- Data is delayed (~15-20 min)

---

## Getting Tastytrade API Credentials

1. **Log into Tastytrade** > **Manage** > **My Profile** > **API**
2. **Enable API access** and agree to terms
3. **Copy** Client ID and Client Secret
4. **Create OAuth Application** and copy the Refresh Token (shown only once!)
5. **Add to `.env` file:**
   ```
   CLIENT_ID=your_client_id_here
   CLIENT_SECRET=your_client_secret_here
   REFRESH_TOKEN=your_refresh_token_here
   ```
6. **Test:** `python get_access_token.py`

---

## Features

### GEX Analysis
- Three visualization modes: Calls vs Puts, Net GEX, Absolute GEX
- Zero Gamma (Gamma Flip) level
- Max GEX Strike (gamma magnet)

### Market Data
- Implied Volatility Skew
- Volume Analysis by strike
- Open Interest distribution
- Top Strikes tables (by OI, Volume, Put/Call Ratio)

### Technical
- Auto-refresh (30-300 second intervals)
- Automatic token management
- Custom symbol support
- Weekend compatible (Friday's closing data)

---

## Architecture

```
User clicks "Fetch Data"
  > OAuth access token (from .env or cache)
  > dxFeed streamer token
  > WebSocket: wss://tasty-openapi-ws.dxfeed.com/realtime
  > Fetch underlying price (Trade/Quote events)
  > Generate option symbols around current price
  > Subscribe to Greeks, Summary (OI), Trade (Volume)
  > Calculate GEX and aggregate by strike
  > Display charts and tables
```

### GEX Formula
```
GEX = Gamma x Open Interest x 100 x Spot Price
```

### Files
- `simple_dashboard.py` - Main dashboard (real-time data, all symbols)
- `demo_dashboard.py` - Demo dashboard (no API required, delayed data)
- `utils/auth.py` - Token management with auto-refresh
- `utils/gex_calculator.py` - Thread-safe GEX calculations

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "python is not recognized" | Reinstall Python, check "Add Python to PATH" |
| "ModuleNotFoundError" | `pip install -r requirements.txt` |
| Token Errors (401) | Verify `.env` credentials (no quotes, no spaces) |
| No Data on Weekends | Expected - shows Friday's closing data |

---

## License

This project is for educational and personal use. Not financial advice.
