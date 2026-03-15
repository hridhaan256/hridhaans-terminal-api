from flask import Flask, jsonify, request
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

API_KEY = "501d05e780a94b489d0673974a7c289b"
BASE_URL = "https://api.twelvedata.com"

# All symbols — NSE by default, BSE supported via exchange param
DEFAULT_SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "HINDUNILVR", "ITC", "SBIN", "BAJFINANCE", "WIPRO",
    "BHARTIARTL", "KOTAKBANK", "LT", "ASIANPAINT", "MARUTI",
    "SUNPHARMA", "TATAMOTORS", "TATASTEEL", "AXISBANK", "HCLTECH",
    "NTPC", "POWERGRID", "ONGC", "ULTRACEMCO", "INDUSINDBK",
    "MANAPPURAM", "KPITTECH", "COALINDIA", "THOMASCOOK",
]

def fetch_batch(symbols, exchange="NSE"):
    """Fetch multiple symbols in one API call — very efficient."""
    try:
        sym_str = ",".join([f"{s}:{exchange}" for s in symbols])
        url = f"{BASE_URL}/quote"
        params = {
            "symbol": sym_str,
            "apikey": API_KEY,
        }
        res = requests.get(url, params=params, timeout=15)
        data = res.json()
        result = {}

        # If single symbol, twelvedata returns object directly
        if len(symbols) == 1:
            sym = symbols[0]
            if "close" in data or "price" in data:
                result[sym] = parse_quote(data, sym)
            else:
                result[sym] = None
        else:
            for sym in symbols:
                key = f"{sym}:{exchange}"
                if key in data and isinstance(data[key], dict):
                    result[sym] = parse_quote(data[key], sym)
                else:
                    result[sym] = None

        return result
    except Exception as e:
        return {s: None for s in symbols}

def fetch_single(symbol, exchange="NSE"):
    """Fetch a single symbol."""
    try:
        url = f"{BASE_URL}/quote"
        params = {
            "symbol": f"{symbol}:{exchange}",
            "apikey": API_KEY,
        }
        res = requests.get(url, params=params, timeout=15)
        data = res.json()
        if "close" in data or "price" in data:
            return parse_quote(data, symbol)
        return None
    except Exception:
        return None

def parse_quote(data, symbol):
    """Parse Twelvedata quote response into our format."""
    try:
        price  = round(float(data.get("close") or data.get("price") or 0), 2)
        prev   = round(float(data.get("previous_close") or price), 2)
        chg    = round(price - prev, 2)
        chgPct = round(float(data.get("percent_change") or ((chg/prev)*100 if prev else 0)), 2)
        return {
            "price":    price,
            "chg":      chg,
            "chgPct":   chgPct,
            "prev":     prev,
            "name":     data.get("name") or symbol,
            "sector":   "",
            "mktCap":   0,
            "pe":       0,
            "high52":   round(float(data.get("fifty_two_week", {}).get("high") or 0), 2),
            "low52":    round(float(data.get("fifty_two_week", {}).get("low") or 0), 2),
            "volume":   int(data.get("volume") or 0),
            "exchange": data.get("exchange") or "NSE",
            "open":     round(float(data.get("open") or price), 2),
            "high":     round(float(data.get("high") or price), 2),
            "low":      round(float(data.get("low") or price), 2),
        }
    except Exception:
        return None

def fetch_indices():
    """Fetch NIFTY, SENSEX, BANKNIFTY separately."""
    indices = {
        "NIFTY":     ("NIFTY", "NSE"),
        "SENSEX":    ("BSE SENSEX", "BSE"),
        "BANKNIFTY": ("NIFTY BANK", "NSE"),
    }
    result = {}
    for local, (sym, exch) in indices.items():
        try:
            url = f"{BASE_URL}/quote"
            params = {"symbol": sym, "apikey": API_KEY, "exchange": exch}
            res = requests.get(url, params=params, timeout=15)
            data = res.json()
            if "close" in data or "price" in data:
                result[local] = parse_quote(data, local)
            else:
                result[local] = None
        except Exception:
            result[local] = None
    return result

@app.route("/prices", methods=["GET"])
def get_prices():
    extra = request.args.get("symbols", "")
    symbols = list(DEFAULT_SYMBOLS)
    if extra:
        for sym in extra.upper().split(","):
            sym = sym.strip()
            if sym and sym not in symbols:
                symbols.append(sym)

    # Twelvedata allows up to 8 symbols per batch on free tier
    # Split into batches of 8
    result = {}
    batch_size = 8
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i+batch_size]
        batch_result = fetch_batch(batch, "NSE")
        result.update(batch_result)

    # Add indices
    indices = fetch_indices()
    result.update(indices)

    # Add USD/INR
    try:
        url = f"{BASE_URL}/quote"
        params = {"symbol": "USD/INR", "apikey": API_KEY}
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        if "close" in data:
            result["USDINR"] = parse_quote(data, "USDINR")
    except Exception:
        result["USDINR"] = None

    return jsonify(result)

@app.route("/search", methods=["GET"])
def search():
    q = request.args.get("q", "").strip().upper()
    exchange = request.args.get("exchange", "NSE").upper()
    if not q:
        return jsonify({"error": "No symbol provided"}), 400

    # Try requested exchange first, then the other
    exchanges = [exchange, "BSE" if exchange == "NSE" else "NSE"]
    for exch in exchanges:
        data = fetch_single(q, exch)
        if data:
            data["symbol"] = q
            data["exchange"] = exch
            return jsonify(data)

    return jsonify({"error": f"{q} not found on NSE or BSE"}), 404

@app.route("/quote/<symbol>", methods=["GET"])
def quote(symbol):
    symbol = symbol.upper().strip()
    exchange = request.args.get("exchange", "NSE").upper()
    data = fetch_single(symbol, exchange)
    if not data:
        alt = "BSE" if exchange == "NSE" else "NSE"
        data = fetch_single(symbol, alt)
    if data:
        data["symbol"] = symbol
        return jsonify(data)
    return jsonify({"error": f"{symbol} not found"}), 404

@app.route("/history/<symbol>", methods=["GET"])
def history(symbol):
    """Get price history for charts."""
    symbol = symbol.upper().strip()
    exchange = request.args.get("exchange", "NSE").upper()
    interval = request.args.get("interval", "1day")
    outputsize = request.args.get("outputsize", "30")
    try:
        url = f"{BASE_URL}/time_series"
        params = {
            "symbol": f"{symbol}:{exchange}",
            "interval": interval,
            "outputsize": outputsize,
            "apikey": API_KEY,
        }
        res = requests.get(url, params=params, timeout=15)
        data = res.json()
        if "values" in data:
            prices = [{"t": v["datetime"], "c": float(v["close"]), "o": float(v["open"]), "h": float(v["high"]), "l": float(v["low"]), "v": int(v.get("volume",0))} for v in reversed(data["values"])]
            return jsonify({"symbol": symbol, "prices": prices})
        return jsonify({"error": "No data", "raw": data}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health():
    # Test API key with a quick call
    try:
        res = requests.get(f"{BASE_URL}/api_usage", params={"apikey": API_KEY}, timeout=5)
        usage = res.json()
        return jsonify({
            "status": "ok",
            "service": "Hridhaan Terminal API",
            "data_source": "Twelvedata",
            "api_usage": usage,
        })
    except Exception:
        return jsonify({"status": "ok", "service": "Hridhaan Terminal API", "data_source": "Twelvedata"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
