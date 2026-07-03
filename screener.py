import yfinance as yf
import pandas as pd
import requests
import json
import time

# -------------------------------------------------------------
# ⚠️ ഇവിടെ നിങ്ങളുടെ ഗൂഗിൾ ആപ്പ് സ്ക്രിപ്റ്റ് യുആർഎൽ (Web App URL) പേസ്റ്റ് ചെയ്യുക
# -------------------------------------------------------------
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwRtdiFNoc-WIroNoCtNUUWQNAplzusjRHJvf1S76iWooWsLyxl3RLLPg8WpryIoW_LFA/exec"

def get_nifty250_tickers():
    url = "https://archives.nseindia.com/content/indices/ind_niftylargemidcap250_list.csv"
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            with open("nifty250.csv", "w") as f:
                f.write(response.text)
            df = pd.read_csv("nifty250.csv")
            tickers = df['Symbol'].tolist()
            return [str(t).strip() + ".NS" for t in tickers if pd.notna(t)]
    except Exception as e:
        print("NSE ലിസ്റ്റ് എടുക്കാൻ പറ്റിയില്ല, ബാക്കപ്പ് ഉപയോഗിക്കുന്നു:", e)
    
    return ["BEL.NS", "POLYCAB.NS", "TATACHEM.NS", "ASTRAL.NS", "VOLTAS.NS"]

def analyze_stocks():
    tickers = get_nifty250_tickers()
    screened_data = []
    
    print(f"മൊത്തം {len(tickers)} കമ്പനികൾ പരിശോധിക്കുന്നു...")
    
    for count, ticker in enumerate(tickers, 1):
        # യാഹൂ ഫിനാൻസ് ബ്ലോക്ക് ചെയ്യാതിരിക്കാൻ 1 സെക്കൻഡ് ഗ്യാപ്പ് നൽകുന്നു
        time.sleep(1)
        
        company_name = ticker.replace(".NS", "")
        current_price = 0
        dma_200 = 0
        current_rsi = 0
        debt_to_equity = 0
        status = "⏳ WAIT"
        signal = "⚪ WAIT"
        
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            company_name = info.get('longName', company_name)
            
            # Debt to Equity
            debt = info.get('debtToEquity', None)
            debt_to_equity = round(debt / 100.0, 2) if debt is not None else 0
            
            if debt_to_equity > 0.5:
                status = "⚠️ HIGH DEBT"
                screened_data.append([company_name, ticker.replace(".NS", ""), 0, 0, 0, debt_to_equity, status, signal])
                continue
                
            # Prices History
            hist = stock.history(period="1y")
            if len(hist) < 200:
                status = "⚠️ NO HISTORY"
                screened_data.append([company_name, ticker.replace(".NS", ""), 0, 0, 0, debt_to_equity, status, signal])
                continue
                
            close_prices = hist['Close']
            current_price = round(close_prices.iloc[-1], 2)
            dma_50 = close_prices.rolling(window=50).mean().iloc[-1]
            dma_200 = round(close_prices.rolling(window=200).mean().iloc[-1], 2)
            
            # RSI
            delta = close_prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi_series = 100 - (100 / (1 + rs))
            current_rsi = round(rsi_series.iloc[-1], 2)
            prev_rsi = rsi_series.iloc[-2]
            
            # Strategy Conditions
            is_above_dma = current_price > dma_50 and current_price > dma_200
            is_near_support = current_price < (dma_50 * 1.05)
            is_rsi_good = 30 <= current_rsi <= 48
            is_rsi_turning_up = current_rsi > prev_rsi
            
            if is_rsi_good:
                status = "📉 CHEAP"
                if is_above_dma and is_near_support and is_rsi_turning_up:
                    signal = "🟢 PERFECT BUY"
                    
        except Exception as e:
            print(f"{ticker} എറർ: {e}")
            status = "❌ DATA ERROR"
            
        screened_data.append([company_name, ticker.replace(".NS", ""), current_price, dma_200, current_rsi, debt_to_equity, status, signal])
        print(f"({count}/{len(tickers)}) {company_name} - പരിശോധന കഴിഞ്ഞു")
            
    # Upload to Sheets
    if screened_data and WEB_APP_URL != "YOUR_WEB_APP_URL_HERE":
        try:
            headers = {'Content-Type': 'application/json'}
            response = requests.post(WEB_APP_URL, data=json.dumps(screened_data), headers=headers, timeout=60)
            print("ഷീറ്റ് അപ്‌ഡേറ്റ് സ്റ്റാറ്റസ്:", response.text)
        except Exception as e:
            print("ഷീറ്റിലേക്ക് അയക്കാൻ പറ്റിയില്ല:", e)

if __name__ == "__main__":
    analyze_stocks()
