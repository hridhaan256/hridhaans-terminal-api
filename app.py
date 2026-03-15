from flask import Flask, jsonify, request
from flask_cors import CORS
import yfinance as yf
import traceback

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
        # Use fast_info first
        try:
            fi = ticker.fast_info
            price = round(float(fi.last_price), 2)
            prev  = round(float(fi.previous_close), 2)
            chg   = round(price - prev, 2)
            chgPct = round((chg / prev) * 100, 2) if prev else 0
            return {
                "price":   price,
                "chg":     chg,
                "chgPct":  chgPct,
                "prev":    prev,
                "name":    yf_sym,
                "sector":  "",
                "mktCap":  0,
                "pe":      0,
                "high52":  round(float(fi.year_high), 2) if fi.year_high else 0,
                "low52":   round(float(fi.year_low), 2) if fi.year_low else 0,
                "volume":  0,
                "exchange":"",
            }
        except Exception:
            pass

        # Fallback to history
        hist = ticker.history(period="5d", interval="1d")
        if hist.empty:
            return None
        price  = round(float(hist["Close"].iloc[-1]), 2)
        prev   = round(float(hist["Close"].iloc[-2]), 2) if len(hist) > 1 else price
        chg    = round(price - prev, 2)
        chgPct = round((chg / prev) * 100, 2) if prev else 0
        return {
            "price":   price,
            "chg":     chg,
            "chgPct":  chgPct,
            "prev":    prev,
            "name":    yf_sym,
            "sector":  "",
            "mktCap":  0,
            "pe":      0,
            "high52":  round(float(hist["High"].max()), 2),
            "low52":   round(float(hist["Low"].min()), 2),
            "volume":  int(hist["Volume"].iloc[-1]),
            "exchange":"",
        }
    except Exception as e:
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
    # Try multiple suffix formats
    suffixes = [".NS", ".BO", ""] if exchange == "NSE" else [".BO", ".NS", ""]
    for suffix in suffixes:
        sym = q if q.endswith(suffix) else q.replace(".NS","").replace(".BO","") + suffix
        data = fetch_symbol(sym)
        if data:
            data["symbol"] = q.replace(".NS","").replace(".BO","")
            data["yf_symbol"] = sym
            return jsonify(data)
    return jsonify({"error": f"Symbol {q} not found", "tried": [q+s for s in suffixes]}), 404

@app.route("/quote/<symbol>", methods=["GET"])
def quote(symbol):
    symbol = symbol.upper().strip().replace(".NS","").replace(".BO","")
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

@app.route("/debug/<symbol>", methods=["GET"])
def debug(symbol):
    """Debug endpoint to see exactly what yfinance returns"""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="5d")
        return jsonify({
            "symbol": symbol,
            "hist_empty": hist.empty,
            "hist_len": len(hist),
            "hist_tail": hist.tail(2).to_dict() if not hist.empty else {},
        })
    except Exception as e:
        return jsonify({"error": str(e), "trace": traceback.format_exc()})

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "Hridhaan Terminal API"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
