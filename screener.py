import yfinance as yf
import pandas as pd
import requests
import json

# -------------------------------------------------------------
# ⚠️ https://script.google.com/macros/s/AKfycbxx1on49uwOmyNl-xnutHxxa4I6J4qbYU8mS-TBc26By5idnCxRs5qzDvftSUQEWtl1-Q/exec

# -------------------------------------------------------------
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwZAmfVaEtxW-ZwEIihnYORk0m5626jFRXLw3QMm0Y9xI8pSjWq1Ti4E6ljV8dpT0ij9A/exec"

def get_nifty250_tickers():
    url = "https://archives.nseindia.com/content/indices/ind_niftylargemidcap250_list.csv"
    try:
        df = pd.read_csv(url)
        tickers = df['Symbol'].tolist()
        return [t + ".NS" for t in tickers]
    except Exception:
        return ["BEL.NS", "POLYCAB.NS", "TATACHEM.NS", "ASTRAL.NS", "VOLTAS.NS"]

def analyze_stocks():
    tickers = get_nifty250_tickers()
    screened_data = []
    
    print("കമ്പനികൾ പരിശോധിക്കുന്നു...")
    
    # കൃത്യമായ ഫിൽട്ടറിങ്ങിനായി ആദ്യത്തെ 60 കമ്പനികൾ പരിശോധിക്കുന്നു
    for ticker in tickers[:60]:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            debt_to_equity = info.get('debtToEquity', 0)
            if debt_to_equity is not None:
                debt_to_equity = debt_to_equity / 100.0
            else:
                debt_to_equity = 0
                
            if debt_to_equity > 0.5:
                continue
                
            hist = stock.history(period="1y")
            if len(hist) < 200:
                continue
                
            close_prices = hist['Close']
            current_price = close_prices.iloc[-1]
            
            dma_50 = close_prices.rolling(window=50).mean().iloc[-1]
            dma_200 = close_prices.rolling(window=200).mean().iloc[-1]
            
            delta = close_prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi_series = 100 - (100 / (1 + rs))
            
            current_rsi = rsi_series.iloc[-1]
            prev_rsi = rsi_series.iloc[-2]
            
            is_above_dma = current_price > dma_50 and current_price > dma_200
            is_near_support = current_price < (dma_50 * 1.05)
            is_rsi_good = 30 <= current_rsi <= 48
            is_rsi_turning_up = current_rsi > prev_rsi
            
            status = "⏳ WAIT"
            signal = "⚪ WAIT"
            
            if is_rsi_good:
                status = "📉 CHEAP"
                if is_above_dma and is_near_support and is_rsi_turning_up:
                    signal = "🟢 PERFECT BUY"
            
            screened_data.append([
                info.get('longName', ticker),
                ticker.replace(".NS", ""),
                round(current_price, 2),
                round(dma_200, 2),
                round(current_rsi, 2),
                round(debt_to_equity, 2),
                status,
                signal
            ])
            
        except Exception:
            continue
            
    # ഡാറ്റ ഗൂഗിൾ ഷീറ്റിലേക്ക് അയക്കുന്നു
    if screened_data and WEB_APP_URL != "YOUR_WEB_APP_URL_HERE":
        try:
            response = requests.post(WEB_APP_URL, json=screened_data)
            print("ഷീറ്റ് അപ്‌ഡേറ്റ് സ്റ്റാറ്റസ്:", response.text)
        except Exception as e:
            print("ഷീറ്റിലേക്ക് ഡാറ്റ അയക്കാൻ പറ്റിയില്ല:", e)

if __name__ == "__main__":
    analyze_stocks()
