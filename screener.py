import yfinance as yf
import pandas as pd
import requests

def get_nifty250_tickers():
    # NSE ഒഫീഷ്യൽ വെബ്‌സൈറ്റിൽ നിന്ന് നിഫ്റ്റി 250 ലിസ്റ്റ് നേരിട്ട് എടുക്കുന്നു
    url = "https://archives.nseindia.com/content/indices/ind_niftylargemidcap250_list.csv"
    try:
        df = pd.read_csv(url)
        tickers = df['Symbol'].tolist()
        return [t + ".NS" for t in tickers]
    except Exception as e:
        print("NSE ലിസ്റ്റ് എടുക്കാൻ സാധിച്ചില്ല, സാമ്പിൾ ലിസ്റ്റ് ഉപയോഗിക്കുന്നു.")
        return ["BEL.NS", "POLYCAB.NS", "TATACHEM.NS", "ASTRAL.NS", "VOLTAS.NS"]

def analyze_stocks():
    tickers = get_nifty250_tickers()
    screened_data = []
    
    print(f"മൊത്തം {len(tickers)} കമ്പനികൾ പരിശോധിക്കുന്നു...")
    
    # തൽക്കാലം ടെസ്റ്റ് ചെയ്യാൻ ആദ്യത്തെ 20 കമ്പനികൾ മാത്രം നോക്കുന്നു
    for ticker in tickers[:20]:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # 1. കടം പരിശോധിക്കുന്നു (Debt to Equity)
            debt_to_equity = info.get('debtToEquity', 0)
            if debt_to_equity is not None:
                debt_to_equity = debt_to_equity / 100.0
            else:
                debt_to_equity = 0
                
            # കടം 0.5-ൽ കൂടുതൽ ഉള്ളവയെ ഇവിടെ വെച്ച് തന്നെ ഒഴിവാക്കുന്നു
            if debt_to_equity > 0.5:
                continue
                
            # 2. വില വിവരങ്ങൾ (RSI, DMA)
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
            
            # 3. സ്ട്രാറ്റജി കണ്ടീഷനുകൾ
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
            
    # റിസൾട്ട് സ്ക്രീനിൽ കാണിക്കുന്നു
    print("\n🎯 സ്ട്രാറ്റജി പ്രകാരം കണ്ടെത്തിയ കമ്പനികൾ താഴെ പറയുന്നവയാണ്:")
    print("-" * 80)
    print(f"{'Company Name':<30} | {'Price':<8} | {'RSI':<6} | {'Debt':<5} | {'Signal'}")
    print("-" * 80)
    for row in screened_data:
        print(f"{row[0][:30]:<30} | {row[2]:<8} | {row[4]:<6} | {row[5]:<5} | {row[7]}")

if __name__ == "__main__":
    analyze_stocks()
