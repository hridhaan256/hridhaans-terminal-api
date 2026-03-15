from flask import Flask, jsonify, request
from flask_cors import CORS
import yfinance as yf

app = Flask(__name__)
CORS(app)

DEFAULT_SYMBOLS = {
    "RELIANCE":   "RELIANCE.NS",
    "TCS":        "TCS.NS",
    "HDFCBANK":   "HDFCBANK.NS",
    "INFY":       "INFY.NS",
    "ICICIBANK":  "ICICIBANK.NS",
    "HINDUNILVR": "HINDUNILVR.NS",
    "ITC":        "ITC.NS",
    "SBIN":       "SBIN.NS",
    "BAJFINANCE": "BAJFINANCE.NS",
    "WIPRO":      "WIPRO.NS",
    "BHARTIARTL": "BHARTIARTL.NS",
    "KOTAKBANK":  "KOTAKBANK.NS",
    "LT":         "LT.NS",
    "ASIANPAINT": "ASIANPAINT.NS",
    "MARUTI":     "MARUTI.NS",
    "SUNPHARMA":  "SUNPHARMA.NS",
    "TATAMOTORS": "TATAMOTORS.NS",
    "TATASTEEL":  "TATASTEEL.NS",
    "AXISBANK":   "AXISBANK.NS",
    "HCLTECH":    "HCLTECH.NS",
    "NTPC":       "NTPC.NS",
    "POWERGRID":  "POWERGRID.NS",
    "ONGC":       "ONGC.NS",
    "ULTRACEMCO": "ULTRACEMCO.NS",
    "INDUSINDBK": "INDUSINDBK.NS",
    "NIFTY":      "^NSEI",
    "SENSEX":     "^BSESN",
    "BANKNIFTY":  "^NSEBANK",
    "USDINR":     "INR=X",
}

def fetch_symbol(yf_sym):
    try:
        ticker = yf.Ticker(yf_sym)
        hist = ticker.history(period="2d")
        if hist.empty:
            return None
        price  = round(float(hist["Close"].iloc[-1]), 2)
        prev   = round(float(hist["Close"].iloc[-2]), 2) if len(hist) > 1 else price
        chg    = round(price - prev, 2)
        chgPct = round((chg / prev) * 100, 2) if prev else 0
        info   = ticker.info
        return {
            "price":    price,
            "chg":      chg,
            "chgPct":   chgPct,
            "prev":     prev,
            "name":     info.get("longName") or info.get("shortName") or yf_sym,
            "sector":   info.get("sector", ""),
            "mktCap":   info.get("marketCap", 0),
            "pe":       info.get("trailingPE") or info.get("forwardPE") or 0,
            "high52":   info.get("fiftyTwoWeekHigh", 0),
            "low52":    info.get("fiftyTwoWeekLow", 0),
            "volume":   info.get("volume", 0),
            "exchange": info.get("exchange", ""),
        }
    except Exception:
        return None

@app.route("/prices", methods=["GET"])
def get_prices():
    extra = request.args.get("symbols", "")
    symbols = dict(DEFAULT_SYMBOLS)
    if extra:
        for sym in extra.upper().split(","):
            sym = sym.strip()
            if sym and sym not in symbols:
                symbols[sym] = sym + ".NS"
    result = {}
    for local_sym, yf_sym in symbols.items():
        result[local_sym] = fetch_symbol(yf_sym)
    return jsonify(result)

@app.route("/search", methods=["GET"])
def search():
    q = request.args.get("q", "").strip().upper()
    exchange = request.args.get("exchange", "NSE").upper()
    if not q:
        return jsonify({"error": "No symbol provided"}), 400
    suffixes = [".NS", ".BO", ""] if exchange == "NSE" else [".BO", ".NS", ""]
    for suffix in suffixes:
        data = fetch_symbol(q + suffix)
        if data:
            data["symbol"] = q
            data["yf_symbol"] = q + suffix
            return jsonify(data)
    return jsonify({"error": f"Symbol {q} not found on NSE or BSE"}), 404

@app.route("/quote/<symbol>", methods=["GET"])
def quote(symbol):
    symbol = symbol.upper().strip()
    exchange = request.args.get("exchange", "NSE").upper()
    suffix = ".BO" if exchange == "BSE" else ".NS"
    data = fetch_symbol(symbol + suffix)
    if not data:
        alt = ".NS" if suffix == ".BO" else ".BO"
        data = fetch_symbol(symbol + alt)
    if data:
        data["symbol"] = symbol
        return jsonify(data)
    return jsonify({"error": f"Symbol {symbol} not found"}), 404

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "Hridhaan Terminal API"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
