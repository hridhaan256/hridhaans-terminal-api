from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import json

app = Flask(__name__)
CORS(app)

# NSE India headers — must mimic a real browser or NSE blocks the request
NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.nseindia.com/",
    "Connection": "keep-alive",
}

# Session to maintain cookies (NSE requires cookies)
session = requests.Session()
session.headers.update(NSE_HEADERS)

def init_nse_session():
    """Visit NSE homepage first to get cookies — required for API calls."""
    try:
        session.get("https://www.nseindia.com", timeout=10)
        session.get("https://www.nseindia.com/market-data/live-equity-market", timeout=10)
    except Exception:
        pass

# Initialize session on startup
init_nse_session()

def get_nse_quote(symbol):
    """Get live quote for a single NSE symbol."""
    try:
        url = f"https://www.nseindia.com/api/quote-equity?symbol={symbol.upper()}"
        res = session.get(url, timeout=10)
        if res.status_code == 401 or res.status_code == 403:
            # Session expired — reinitialize
            init_nse_session()
            res = session.get(url, timeout=10)
        if res.status_code != 200:
            return None
        data = res.json()
        pd = data.get("priceInfo", {})
        md = data.get("metadata", {})
        price  = round(float(pd.get("lastPrice") or 0), 2)
        prev   = round(float(pd.get("previousClose") or price), 2)
        chg    = round(float(pd.get("change") or (price - prev)), 2)
        chgPct = round(float(pd.get("pChange") or ((chg/prev)*100 if prev else 0)), 2)
        wk52   = pd.get("weekHighLow", {})
        return {
            "price":    price,
            "chg":      chg,
            "chgPct":   chgPct,
            "prev":     prev,
            "name":     md.get("companyName") or symbol,
            "sector":   md.get("industry") or "",
            "mktCap":   0,
            "pe":       0,
            "high52":   round(float(wk52.get("max") or 0), 2),
            "low52":    round(float(wk52.get("min") or 0), 2),
            "volume":   int(data.get("marketDeptOrderBook", {}).get("tradeInfo", {}).get("totalTradedVolume") or 0),
            "exchange": "NSE",
            "open":     round(float(pd.get("open") or price), 2),
            "high":     round(float(pd.get("intraDayHighLow", {}).get("max") or price), 2),
            "low":      round(float(pd.get("intraDayHighLow", {}).get("min") or price), 2),
        }
    except Exception as e:
        return None

def get_nse_index(index_name):
    """Get live index data — NIFTY 50, BANK NIFTY etc."""
    try:
        url = f"https://www.nseindia.com/api/allIndices"
        res = session.get(url, timeout=10)
        if res.status_code != 200:
            init_nse_session()
            res = session.get(url, timeout=10)
        data = res.json()
        for idx in data.get("data", []):
            if idx.get("index", "").upper() == index_name.upper():
                price  = round(float(idx.get("last") or 0), 2)
                prev   = round(float(idx.get("previousClose") or price), 2)
                chg    = round(float(idx.get("change") or (price - prev)), 2)
                chgPct = round(float(idx.get("percentChange") or 0), 2)
                return {
                    "price":   price,
                    "chg":     chg,
                    "chgPct":  chgPct,
                    "prev":    prev,
                    "name":    idx.get("index"),
                    "high52":  round(float(idx.get("yearHigh") or 0), 2),
                    "low52":   round(float(idx.get("yearLow") or 0), 2),
                    "exchange":"NSE",
                }
        return None
    except Exception:
        return None

def get_usd_inr():
    """Get USD/INR rate from a free forex API."""
    try:
        res = requests.get("https://open.er-api.com/v6/latest/USD", timeout=8)
        data = res.json()
        rate = round(float(data["rates"]["INR"]), 2)
        return {"price": rate, "chg": 0, "chgPct": 0, "prev": rate, "name": "USD/INR", "exchange": "FOREX"}
    except Exception:
        return None

DEFAULT_SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "HINDUNILVR", "ITC", "SBIN", "BAJFINANCE", "WIPRO",
    "BHARTIARTL", "KOTAKBANK", "LT", "ASIANPAINT", "MARUTI",
    "SUNPHARMA", "TATAMOTORS", "TATASTEEL", "AXISBANK", "HCLTECH",
    "NTPC", "POWERGRID", "ONGC", "ULTRACEMCO", "INDUSINDBK",
    "MANAPPURAM", "KPITTECH", "COALINDIA", "THOMASCOOK",
]

@app.route("/prices", methods=["GET"])
def get_prices():
    extra = request.args.get("symbols", "")
    symbols = list(DEFAULT_SYMBOLS)
    if extra:
        for sym in extra.upper().split(","):
            sym = sym.strip()
            if sym and sym not in symbols:
                symbols.append(sym)

    result = {}

    # Fetch all stock quotes
    for sym in symbols:
        result[sym] = get_nse_quote(sym)

    # Fetch indices
    result["NIFTY"]     = get_nse_index("NIFTY 50")
    result["SENSEX"]    = get_nse_index("SENSEX")
    result["BANKNIFTY"] = get_nse_index("NIFTY BANK")

    # Fetch USD/INR
    result["USDINR"] = get_usd_inr()

    return jsonify(result)

@app.route("/search", methods=["GET"])
def search():
    q = request.args.get("q", "").strip().upper()
    if not q:
        return jsonify({"error": "No symbol provided"}), 400
    data = get_nse_quote(q)
    if data:
        data["symbol"] = q
        return jsonify(data)
    return jsonify({"error": f"{q} not found on NSE"}), 404

@app.route("/quote/<symbol>", methods=["GET"])
def quote(symbol):
    symbol = symbol.upper().strip()
    data = get_nse_quote(symbol)
    if data:
        data["symbol"] = symbol
        return jsonify(data)
    return jsonify({"error": f"{symbol} not found"}), 404

@app.route("/history/<symbol>", methods=["GET"])
def history(symbol):
    """Get historical price data for charts."""
    symbol = symbol.upper().strip()
    try:
        url = f"https://www.nseindia.com/api/historical/cm/equity?symbol={symbol}&series=[%22EQ%22]&from=2024-01-01&to=2026-03-16"
        res = session.get(url, timeout=15)
        if res.status_code != 200:
            init_nse_session()
            res = session.get(url, timeout=15)
        data = res.json()
        prices = []
        for item in data.get("data", []):
            prices.append({
                "t": item.get("CH_TIMESTAMP"),
                "c": float(item.get("CH_CLOSING_PRICE") or 0),
                "o": float(item.get("CH_OPENING_PRICE") or 0),
                "h": float(item.get("CH_TRADE_HIGH_PRICE") or 0),
                "l": float(item.get("CH_TRADE_LOW_PRICE") or 0),
                "v": int(item.get("CH_TOT_TRADED_QTY") or 0),
            })
        return jsonify({"symbol": symbol, "prices": prices})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health():
    # Test NSE connection
    test = get_nse_quote("RELIANCE")
    return jsonify({
        "status": "ok",
        "service": "Hridhaan Terminal API",
        "data_source": "NSE India (Real-time)",
        "nse_connected": test is not None,
        "reliance_price": test.get("price") if test else None,
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
