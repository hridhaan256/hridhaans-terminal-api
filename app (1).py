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
    for local_sym, yf_sym in SYMBOLS.items():
        try:
            ticker = yf.Ticker(yf_sym)
            hist = ticker.history(period="2d")
            if hist.empty:
                result[local_sym] = None
                continue
            price  = round(float(hist["Close"].iloc[-1]), 2)
            prev   = round(float(hist["Close"].iloc[-2]), 2) if len(hist) > 1 else price
            chg    = round(price - prev, 2)
            chgPct = round((chg / prev) * 100, 2) if prev else 0
            result[local_sym] = {
                "price":  price,
                "chg":    chg,
                "chgPct": chgPct,
                "prev":   prev,
            }
        except Exception as e:
            result[local_sym] = None
    return jsonify(result)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "Hridhaan Terminal API"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
