import yfinance as yf
import pandas as pd
import requests
import json

# -------------------------------------------------------------
# ⚠️ ഇവിടെ നിങ്ങളുടെ ഗൂഗിൾ ആപ്പ് സ്ക്രിപ്റ്റ് യുആർഎൽ (Web App URL) പേസ്റ്റ് ചെയ്യുക
# -------------------------------------------------------------
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbxt4YkIwOTZxtga_xRFVGgOVAkRbbG1o29lmYJJlcB4pQmm0bugP83i3wCQWay9Y7sGzg/exec"

def get_nifty250_tickers():
    url = "https://archives.nseindia.com/content/indices/ind_niftylargemidcap250_list.csv"
    try:
        df = pd.read_csv(url)
        tickers = df['Symbol'].tolist()
        return [t + ".NS" for t in tickers if isinstance(t, str)]
    except Exception as e:
        print("NSE ലിസ്റ്റ് എടുക്കാൻ സാധിച്ചില്ല, സാമ്പിൾ ലിസ്റ്റ് ഉപയോഗിക്കുന്നു:", e)
        return ["BEL.NS", "POLYCAB.NS", "TATACHEM.NS", "ASTRAL.NS", "VOLTAS.NS"]

def analyze_stocks():
    tickers = get_nifty250_tickers()
    screened_data = []
    
    print(f"മൊത്തം {len(tickers)} കമ്പനികൾ പരിശോധിക്കുന്നു...")
    
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # കമ്പനിയുടെ പേര് കിട്ടുന്നുണ്ടോ എന്ന് നോക്കുന്നു
            company_name = info.get('longName', ticker)
            
            # കടം പരിശോധിക്കുന്നു (Debt to Equity)
            debt_to_equity = info.get('debtToEquity', 0)
            if debt_to_equity is not None:
                debt_to_equity = debt_to_equity / 100.0
            else:
                debt_to_equity = 0
                
            # കടം 0.5-ൽ കൂടുതൽ ഉള്ളവയെ ഒഴിവാക്കുന്നു
            if debt_to_equity > 0.5:
                continue
                
            # വില വിവരങ്ങൾ (RSI, DMA)
            hist = stock.history(period="1y")
            if len(hist) < 200:
                continue
                
            close_prices = hist['Close']
            current_price = close_prices.iloc[-1]
            
            # Moving Averages (50 DMA & 200 DMA)
            dma_50 = close_prices.rolling(window=50).mean().iloc[-1]
            dma_200 = close_prices.rolling(window=200).mean().iloc[-1]
            
            # RSI കണക്കുകൂട്ടൽ
            delta = close_prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi_series = 100 - (100 / (1 + rs))
            
            current_rsi = rsi_series.iloc[-1]
            prev_rsi = rsi_series.iloc[-2]
            
            # സ്ട്രാറ്റജി കണ്ടീഷനുകൾ
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
                company_name,
                ticker.replace(".NS", ""),
                round(current_price, 2),
                round(dma_200, 2),
                round(current_rsi, 2),
                round(debt_to_equity, 2),
                status,
                signal
            ])
            
        except Exception as e:
            # ഏതെങ്കിലും കമ്പനിയിൽ എറർ വന്നാൽ അതിനെ വിട്ട് അടുത്തതിലേക്ക് പോകുന്നു
            print(f"{ticker} പരിശോധിക്കുന്നതിൽ തടസ്സം നേരിട്ടു: {e}")
            continue
            
    # ഡാറ്റ ഗൂഗിൾ ഷീറ്റിലേക്ക് അയക്കുന്നു
    if screened_data and WEB_APP_URL != "YOUR_WEB_APP_URL_HERE":
        try:
            response = requests.post(WEB_APP_URL, json=screened_data, timeout=30)
            print("ഷീറ്റ് അപ്‌ഡേറ്റ് സ്റ്റാറ്റസ്:", response.text)
        except Exception as e:
            print("ഷീറ്റിലേക്ക് ഡാറ്റ അയക്കാൻ പറ്റിയില്ല:", e)
    else:
        print("അയക്കാൻ തക്കവണ്ണം ഡാറ്റ ഒന്നും കണ്ടെത്തിയില്ല അല്ലെങ്കിൽ URL തെറ്റാണ്.")

if __name__ == "__main__":
    analyze_stocks()
