import yfinance as yf
import pandas as pd
import requests
import gspread
from google.oauth2.service_account import Credentials
import datetime

# -------------------------------------------------------------
# ⚠️ ഇവിടെ നിങ്ങളുടെ ഗൂഗിൾ ഷീറ്റിന്റെ ലിങ്ക് പേസ്റ്റ് ചെയ്യുക
# -------------------------------------------------------------
GOOGLE_SHEET_LINK = "YOUR_GOOGLE_SHEET_LINK_HERE"
H0nWror8jHtgkfjQna_ua2uCxFtDRx47eTWiD8
def get_nifty250_tickers():
    # NSE വെബ്‌സൈറ്റിൽ നിന്ന് നിഫ്റ്റി 250 ലിസ്റ്റ് തനിയെ എടുക്കുന്നു
    url = "https://archives.nseindia.com/content/indices/ind_niftylargemidcap250_list.csv"
    try:
        df = pd.read_csv(url)
        tickers = df['Symbol'].tolist()
        return [t + ".NS" for t in tickers]
    except Exception as e:
        print("NSE ലിസ്റ്റ് എടുക്കാൻ സാധിച്ചില്ല, സാമ്പിൾ ലിസ്റ്റ് ഉപയോഗിക്കുന്നു:", e)
        return ["BEL.NS", "POLYCAB.NS", "TATACHEM.NS", "ASTRAL.NS", "VOLTAS.NS"]

def analyze_stocks():
    tickers = get_nifty250_tickers()
    screened_data = []
    
    print(f"മൊത്തം {len(tickers)} കമ്പനികൾ പരിശോധിക്കുന്നു...")
    
    for ticker in tickers[:40]: # പരീക്ഷണാർത്ഥം ആദ്യത്തെ 40 കമ്പനികൾ നോക്കുന്നു
        try:
            stock = yf.Ticker(ticker)
            
            # 1. ക്വാളിറ്റി ചെക്ക് (Debt to Equity)
            info = stock.info
            debt_to_equity = info.get('debtToEquity', 0)
            if debt_to_equity is not None:
                debt_to_equity = debt_to_equity / 100.0 # yfinance തരുന്ന ഫോർമാറ്റ് മാറ്റുന്നു
            else:
                debt_to_equity = 0
                
            # കടം 0.5-ൽ കൂടുതൽ ആണെങ്കിൽ ഒഴിവാക്കുന്നു
            if debt_to_equity > 0.5:
                continue
                
            # 2. വിലയും ചാർട്ട് ഇൻഡിക്കേറ്ററുകളും (RSI, DMA)
            hist = stock.history(period="1y")
            if len(hist) < 200:
                continue
                
            close_prices = hist['Close']
            current_price = close_prices.iloc[-1]
            
            # Moving Averages
            dma_50 = close_prices.rolling(window=50).mean().iloc[-1]
            dma_200 = close_prices.rolling(window=200).mean().iloc[-1]
            
            # RSI Calculation
            delta = close_prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi_series = 100 - (100 / (1 + rs))
            
            current_rsi = rsi_series.iloc[-1]
            prev_rsi = rsi_series.iloc[-2] # തലേദിവസത്തെ RSI
            
            # 3. നമ്മുടെ പുതിയ സ്ട്രാറ്റജി കണ്ടീഷനുകൾ
            # വില 50 DMA-യ്ക്ക് മുകളിലും 200 DMA സപ്പോർട്ടിന് അടുത്തും ആയിരിക്കണം
            is_above_dma = current_price > dma_50 and current_price > dma_200
            is_near_support = current_price < (dma_50 * 1.05) # ഒരുപാട് മുകളിലേക്ക് പോയിട്ടില്ല
            
            # RSI കുറവായിരിക്കണം, എന്നാൽ മുകളിലേക്ക് വളയാൻ തുടങ്ങണം (RSI Hook)
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
            
        except Exception as e:
            continue
            
    # ഗൂഗിൾ ഷീറ്റിലേക്ക് മാറ്റുന്നു
    try:
        # ഗൂഗിൾ ഷീറ്റ് കണക്ഷൻ ഇവിടെ വരും
        print("ഡാറ്റ റെഡിയായിട്ടുണ്ട്. ഷീറ്റിലേക്ക് അപ്‌ലോഡ് ചെയ്യാൻ തയാറാണ്.")
        print(screened_data[:5]) # സാമ്പിൾ കാണിക്കുന്നു
    except Exception as e:
        print("ഷീറ്റിലേക്ക് എഴുതാൻ പറ്റിയില്ല:", e)

if __name__ == "__main__":
    analyze_stocks()
