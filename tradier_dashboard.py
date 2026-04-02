"""
GEX Dashboard — Tradier API Edition
Uses Tradier option chains (production or sandbox) for reliable GEX data.
No WebSocket needed, no Tastytrade credentials needed.
Supports SPX, SPY, QQQ, IWM, NDX, and any optionable ticker.
"""
import streamlit as st
import requests
import math
import time
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
from utils.gex_calculator import GEXCalculator

st.set_page_config(page_title="GEX Dashboard", page_icon="📊", layout="wide")

# ---------------------------------------------------------------------------
# Tradier API config — tries production token first, falls back to sandbox
# ---------------------------------------------------------------------------
TOKENS = [
    # Production (live, real-time data)
    {"token": "7pD3m9AfnuZ0WIOnemLfH8FG9VfZ",
     "base": "https://api.tradier.com/v1", "label": "Production"},
    # Sandbox (free, 15-min delayed)
    {"token": "Trn12MGFAGPuGoVGXw3NsYbnIpwa",
     "base": "https://sandbox.tradier.com/v1", "label": "Sandbox"},
]

PRESET_SYMBOLS = {
    "SPX":  {"roots": ["SPXW"], "multiplier": 100, "increment": 5},
    "SPY":  {"roots": ["SPY"],  "multiplier": 100, "increment": 1},
    "QQQ":  {"roots": ["QQQ"],  "multiplier": 100, "increment": 1},
    "IWM":  {"roots": ["IWM"],  "multiplier": 100, "increment": 1},
    "NDX":  {"roots": ["NDXP"], "multiplier": 100, "increment": 25},
    "DIA":  {"roots": ["DIA"],  "multiplier": 100, "increment": 1},
}

RISK_FREE_RATE = 0.045


# ---------------------------------------------------------------------------
# Tradier API helpers
# ---------------------------------------------------------------------------
def get_api():
    """Return working (token, base_url, label) or raise."""
    for t in TOKENS:
        try:
            r = requests.get(
                f"{t['base']}/markets/quotes",
                params={"symbols": "SPY", "greeks": "false"},
                headers={"Authorization": f"Bearer {t['token']}",
                         "Accept": "application/json"},
                timeout=5,
            )
            if r.status_code == 200:
                return t["token"], t["base"], t["label"]
        except Exception:
            continue
    raise ConnectionError("No working Tradier API token")


def fetch_quote(token, base, symbol):
    """Get last price for underlying."""
    r = requests.get(
        f"{base}/markets/quotes",
        params={"symbols": symbol, "greeks": "false"},
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        timeout=10,
    )
    r.raise_for_status()
    q = r.json().get("quotes", {}).get("quote", {})
    return float(q.get("last", 0) or q.get("close", 0) or q.get("prevclose", 0))


def fetch_expirations(token, base, symbol):
    """Get available option expiration dates."""
    r = requests.get(
        f"{base}/markets/options/expirations",
        params={"symbol": symbol, "includeAllRoots": "true", "strikes": "false"},
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        timeout=10,
    )
    r.raise_for_status()
    data = r.json().get("expirations", {})
    dates = data.get("date", [])
    if isinstance(dates, str):
        dates = [dates]
    return dates


def fetch_chain(token, base, symbol, expiration, greeks=True):
    """Fetch full option chain for one expiration."""
    r = requests.get(
        f"{base}/markets/options/chains",
        params={
            "symbol": symbol,
            "expiration": expiration,
            "greeks": str(greeks).lower(),
        },
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        timeout=15,
    )
    r.raise_for_status()
    options = r.json().get("options", {}).get("option", [])
    if isinstance(options, dict):
        options = [options]
    return options


# ---------------------------------------------------------------------------
# GEX computation from Tradier chain
# ---------------------------------------------------------------------------
def compute_gex_from_chain(chain, spot, multiplier=100):
    """
    Compute GEX by strike from a Tradier option chain response.
    Returns (gex_df, metrics_dict, strike_df).
    """
    calc = GEXCalculator(spot_price=spot)

    strike_agg = {}

    for opt in chain:
        strike = float(opt.get("strike", 0))
        otype = opt.get("option_type", "").lower()  # "call" or "put"
        oi = int(opt.get("open_interest", 0) or 0)
        volume = int(opt.get("volume", 0) or 0)

        greeks = opt.get("greeks", {}) or {}
        gamma = greeks.get("gamma")
        delta = greeks.get("delta")
        iv = greeks.get("mid_iv") or greeks.get("smv_vol")

        if gamma is not None:
            try:
                gamma = float(gamma)
            except (ValueError, TypeError):
                gamma = None
        if gamma is None or math.isnan(gamma):
            gamma = None

        # Feed into GEX calculator using symbol format it expects
        if gamma is not None and oi > 0:
            cp = "C" if otype == "call" else "P"
            fake_symbol = f".OPT000000{cp}{int(strike)}"
            calc.update_gamma(fake_symbol, gamma, oi)

        # Aggregate for volume/OI charts
        if strike not in strike_agg:
            strike_agg[strike] = {
                "call_oi": 0, "put_oi": 0,
                "call_volume": 0, "put_volume": 0,
                "call_iv": None, "put_iv": None,
            }
        if otype == "call":
            strike_agg[strike]["call_oi"] += oi
            strike_agg[strike]["call_volume"] += volume
            if iv:
                strike_agg[strike]["call_iv"] = float(iv)
        else:
            strike_agg[strike]["put_oi"] += oi
            strike_agg[strike]["put_volume"] += volume
            if iv:
                strike_agg[strike]["put_iv"] = float(iv)

    gex_df = calc.get_gex_by_strike()
    metrics = calc.get_total_gex_metrics()

    # Build strike DataFrame
    rows = []
    for strike, d in strike_agg.items():
        rows.append({
            "strike": strike,
            "call_oi": d["call_oi"], "put_oi": d["put_oi"],
            "call_volume": d["call_volume"], "put_volume": d["put_volume"],
            "total_oi": d["call_oi"] + d["put_oi"],
            "total_volume": d["call_volume"] + d["put_volume"],
            "call_iv": d["call_iv"], "put_iv": d["put_iv"],
        })
    strike_df = pd.DataFrame(rows)
    if not strike_df.empty:
        strike_df = strike_df.sort_values("strike").reset_index(drop=True)

    return gex_df, metrics, strike_df


# ---------------------------------------------------------------------------
# Dashboard UI
# ---------------------------------------------------------------------------
def main():
    st.title("📊 Options Gamma Exposure Dashboard")

    # Session state init
    for key, default in [
        ("data_fetched", False), ("gex_df", None), ("metrics", None),
        ("strike_df", None), ("underlying_price", 0), ("symbol", "SPX"),
        ("expiration", ""), ("api_label", ""), ("gex_view", "Calls vs Puts"),
        ("volume_view", "Calls vs Puts"),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    # --- Sidebar ---
    with st.sidebar:
        st.header("⚙️ Settings")

        symbol = st.selectbox("Underlying", list(PRESET_SYMBOLS.keys()))

        # Fetch expirations on symbol change
        exp_dates = []
        try:
            token, base, label = get_api()
            exp_dates = fetch_expirations(token, base, symbol)
        except Exception as e:
            st.error(f"API error: {e}")

        if exp_dates:
            # Default to nearest expiration
            expiration = st.selectbox("Expiration", exp_dates, index=0)
        else:
            expiration = st.text_input("Expiration (YYYY-MM-DD)")

        st.divider()

        fetch_triggered = st.button("🔄 Fetch GEX Data", type="primary",
                                    use_container_width=True)

        # Auto-refresh
        auto_refresh = st.checkbox("Auto-refresh", value=False)
        refresh_interval = st.slider("Interval (sec)", 30, 600, 120,
                                     disabled=not auto_refresh)

        if fetch_triggered or (auto_refresh and
            time.time() - st.session_state.get("_last_fetch", 0) > refresh_interval):

            with st.spinner(f"Fetching {symbol} {expiration}..."):
                try:
                    token, base, label = get_api()

                    price = fetch_quote(token, base, symbol)
                    chain = fetch_chain(token, base, symbol, expiration)

                    if not chain:
                        st.error("No option chain data returned")
                    else:
                        mult = PRESET_SYMBOLS.get(symbol, {}).get("multiplier", 100)
                        gex_df, metrics, strike_df = compute_gex_from_chain(
                            chain, price, mult)

                        st.session_state.gex_df = gex_df
                        st.session_state.metrics = metrics
                        st.session_state.strike_df = strike_df
                        st.session_state.underlying_price = price
                        st.session_state.symbol = symbol
                        st.session_state.expiration = expiration
                        st.session_state.api_label = label
                        st.session_state.data_fetched = True
                        st.session_state["_last_fetch"] = time.time()

                        st.success(
                            f"✅ {symbol} ${price:,.2f} | "
                            f"{len(chain)} contracts | {label}"
                        )
                        st.rerun()

                except Exception as e:
                    st.error(f"❌ {e}")
                    import traceback
                    st.code(traceback.format_exc())

        st.divider()
        if st.session_state.data_fetched:
            st.metric(f"{st.session_state.symbol}", f"${st.session_state.underlying_price:,.2f}")
            st.caption(f"API: {st.session_state.api_label} | Exp: {st.session_state.expiration}")

    # --- Main area ---
    if not st.session_state.data_fetched:
        st.info("👈 Select symbol & expiration, then click **Fetch GEX Data**")
        return

    gex_df = st.session_state.gex_df
    metrics = st.session_state.metrics
    strike_df = st.session_state.strike_df
    price = st.session_state.underlying_price

    if gex_df is None or gex_df.empty:
        st.warning("No GEX data. Try a different expiration with more open interest.")
        return

    # --- GEX Chart ---
    col1, col2 = st.columns([2, 1])

    with col1:
        gex_view = st.radio("GEX View",
                            ["Calls vs Puts", "Net GEX", "Absolute GEX"],
                            horizontal=True, key="gex_view_radio")

        fig = go.Figure()

        if gex_view == "Calls vs Puts":
            fig.add_trace(go.Bar(x=gex_df["strike"], y=gex_df["call_gex"],
                                 name="Call GEX", marker_color="green"))
            fig.add_trace(go.Bar(x=gex_df["strike"], y=-gex_df["put_gex"],
                                 name="Put GEX", marker_color="red"))
            barmode, ytitle = "relative", "Gamma Exposure ($)"
        elif gex_view == "Net GEX":
            colors = ["green" if x >= 0 else "red" for x in gex_df["net_gex"]]
            fig.add_trace(go.Bar(x=gex_df["strike"], y=gex_df["net_gex"],
                                 name="Net GEX", marker_color=colors))
            barmode, ytitle = "group", "Net GEX ($)"
        else:
            fig.add_trace(go.Bar(x=gex_df["strike"], y=abs(gex_df["net_gex"]),
                                 name="|Net GEX|", marker_color="blue"))
            barmode, ytitle = "group", "Absolute Net GEX ($)"

        fig.add_vline(x=price, line_dash="dash", line_color="orange",
                      line_width=2,
                      annotation_text=f"${price:,.2f}",
                      annotation_position="top")

        if metrics.get("zero_gamma"):
            fig.add_vline(x=metrics["zero_gamma"], line_dash="dot",
                          line_color="purple", line_width=2,
                          annotation_text=f"Zero Γ: ${metrics['zero_gamma']:,.0f}",
                          annotation_position="bottom")

        fig.update_layout(
            title=f"{st.session_state.symbol} GEX by Strike ({st.session_state.expiration})",
            xaxis_title="Strike", yaxis_title=ytitle,
            barmode=barmode, template="plotly_white", height=500,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("📈 GEX Summary")
        st.metric("Total Call GEX", f"${metrics['total_call_gex']:,.0f}")
        st.metric("Total Put GEX", f"${metrics['total_put_gex']:,.0f}")
        st.metric("Net GEX", f"${metrics['net_gex']:,.0f}")
        if metrics["max_gex_strike"]:
            st.divider()
            st.metric("Max GEX Strike", f"${metrics['max_gex_strike']:,.0f}")
        if metrics.get("zero_gamma"):
            st.metric("Gamma Flip", f"${metrics['zero_gamma']:,.0f}",
                       help="Strike where Net GEX crosses zero")

    # --- IV Skew ---
    if strike_df is not None and not strike_df.empty:
        has_iv = (strike_df["call_iv"].notna().any() or
                  strike_df["put_iv"].notna().any())
        if has_iv:
            st.divider()
            st.header("📈 Implied Volatility Skew")
            fig_iv = go.Figure()
            civ = strike_df[strike_df["call_iv"].notna()]
            piv = strike_df[strike_df["put_iv"].notna()]
            if not civ.empty:
                fig_iv.add_trace(go.Scatter(
                    x=civ["strike"], y=civ["call_iv"] * 100,
                    mode="lines+markers", name="Call IV",
                    line=dict(color="green", width=2)))
            if not piv.empty:
                fig_iv.add_trace(go.Scatter(
                    x=piv["strike"], y=piv["put_iv"] * 100,
                    mode="lines+markers", name="Put IV",
                    line=dict(color="red", width=2)))
            fig_iv.add_vline(x=price, line_dash="dash", line_color="orange",
                             line_width=2)
            fig_iv.update_layout(
                title=f"{st.session_state.symbol} IV Skew",
                xaxis_title="Strike", yaxis_title="IV (%)",
                template="plotly_white", height=400)
            st.plotly_chart(fig_iv, use_container_width=True)

        # --- Volume & OI ---
        st.divider()
        st.header("📊 Volume & Open Interest")
        c3, c4 = st.columns(2)

        with c3:
            fig_oi = go.Figure()
            fig_oi.add_trace(go.Bar(x=strike_df["strike"], y=strike_df["call_oi"],
                                    name="Call OI", marker_color="green"))
            fig_oi.add_trace(go.Bar(x=strike_df["strike"], y=-strike_df["put_oi"],
                                    name="Put OI", marker_color="red"))
            fig_oi.add_vline(x=price, line_dash="dash", line_color="orange",
                             line_width=2)
            fig_oi.update_layout(title="Open Interest", barmode="relative",
                                 template="plotly_white", height=400)
            st.plotly_chart(fig_oi, use_container_width=True)

        with c4:
            fig_vol = go.Figure()
            fig_vol.add_trace(go.Bar(x=strike_df["strike"],
                                     y=strike_df["call_volume"],
                                     name="Call Vol", marker_color="lightgreen"))
            fig_vol.add_trace(go.Bar(x=strike_df["strike"],
                                     y=-strike_df["put_volume"],
                                     name="Put Vol", marker_color="lightcoral"))
            fig_vol.add_vline(x=price, line_dash="dash", line_color="orange",
                              line_width=2)
            fig_vol.update_layout(title="Volume", barmode="relative",
                                  template="plotly_white", height=400)
            st.plotly_chart(fig_vol, use_container_width=True)

        # Top strikes table
        st.subheader("🔝 Top Strikes by OI")
        top = strike_df.nlargest(10, "total_oi")[
            ["strike", "call_oi", "put_oi", "total_oi"]].copy()
        top["strike"] = top["strike"].apply(lambda x: f"${x:,.0f}")
        top.columns = ["Strike", "Call OI", "Put OI", "Total OI"]
        st.dataframe(top, hide_index=True, use_container_width=True)


if __name__ == "__main__":
    main()
