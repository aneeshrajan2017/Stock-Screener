import yfinance as yf
import pandas as pd
import requests
import json
import time

# -------------------------------------------------------------
# ⚠️ ഇവിടെ നിങ്ങളുടെ ഗൂഗിൾ ആപ്പ് സ്ക്രിപ്റ്റ് യുആർഎൽ (Web App URL) പേസ്റ്റ് ചെയ്യുക
# -------------------------------------------------------------
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbyqhxOvby8sLiy4Pcxigk4G2RVpEelh1yhZ8IH-O1ZL0VJYqqDSuRb1glRt1dxzW_VlCA/exec"

def get_nifty250_tickers():
    url = "https://archives.nseindia.com/content/indices/ind_niftylargemidcap250_list.csv"
    try:
        # NSE നമ്മളെ ബ്ലോക്ക് ചെയ്യാതിരിക്കാൻ ഒറിജിനൽ ബ്രൗസർ ആണെന്ന് കാണിക്കുന്ന ഹെഡറുകൾ
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive'
        }
        
        # ഒരു സെഷൻ ഉണ്ടാക്കി വെബ്‌സൈറ്റ് സന്ദർശിക്കുന്നു
        session = requests.Session()
        # ആദ്യം മെയിൻ സൈറ്റിൽ കയറി കുക്കീസ് (Cookies) എടുക്കുന്നു
        session.get("https://www.nseindia.com", headers=headers, timeout=10)
        
        # ഇനി ലിങ്ക് ഡൗൺലോഡ് ചെയ്യുന്നു
        response = session.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            with open("nifty250.csv", "w", encoding='utf-8') as f:
                f.write(response.text)
            df = pd.read_csv("nifty250.csv")
            tickers = df['Symbol'].tolist()
            print(f"NSE-ൽ നിന്ന് {len(tickers)} കമ്പനികളുടെ ലിസ്റ്റ് വിജയകരമായി എടുത്തു!")
            return [str(t).strip() + ".NS" for t in tickers if pd.notna(t)]
            
    except Exception as e:
        print("NSE ഡയറക്റ്റ് ലിസ്റ്റ് എടുക്കാൻ പറ്റിയില്ല, ബാക്കപ്പ് ഉപയോഗിക്കുന്നു:", e)
    
    # ഒരു കാരണവശാലും കോഡ് നിന്നുപോകാതിരിക്കാൻ നൽകുന്ന സുരക്ഷിത ബാക്കപ്പ് കമ്പനികൾ
    return ["BEL.NS", "POLYCAB.NS", "TATACHEM.NS", "ASTRAL.NS", "VOLTAS.NS"]

def analyze_stocks():
    tickers = get_nifty250_tickers()
    screened_data = []
    
    print(f"മൊത്തം {len(tickers)} കമ്പനികൾ പരിശോധിക്കുന്നു...")
    
    for count, ticker in enumerate(tickers, 1):
        time.sleep(1.2) # യാഹൂ ഫിനാൻസ് ബ്ലോക്ക് ചെയ്യാതിരിക്കാൻ ചെറിയ ഗ്യാപ്പ്
        
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
