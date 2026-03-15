from flask import Flask, jsonify
from flask_cors import CORS
import yfinance as yf

app = Flask(__name__)
CORS(app)  # Allow requests from any browser/HTML file

# All Nifty 50 stocks mapped to Yahoo Finance symbols
SYMBOLS = {
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
    # Indices
    "NIFTY":      "^NSEI",
    "SENSEX":     "^BSESN",
    "BANKNIFTY":  "^NSEBANK",
    # Currency & Commodities
    "USDINR":     "INR=X",
    "GOLD":       "GC=F",
}

@app.route("/prices", methods=["GET"])
def get_prices():
    result = {}
    try:
        all_symbols = list(SYMBOLS.values())
        # Fetch all at once — much faster
        tickers = yf.Tickers(" ".join(all_symbols))
        for local_sym, yf_sym in SYMBOLS.items():
            try:
                info = tickers.tickers[yf_sym].fast_info
                price = round(float(info.last_price), 2)
                prev  = round(float(info.previous_close), 2)
                chg   = round(price - prev, 2)
                chgPct = round((chg / prev) * 100, 2) if prev else 0
                result[local_sym] = {
                    "price":  price,
                    "chg":    chg,
                    "chgPct": chgPct,
                    "prev":   prev,
                }
            except Exception:
                result[local_sym] = None
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify(result)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "Hridhaan Terminal API"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
