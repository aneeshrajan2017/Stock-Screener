import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import requests
import zipfile
import io
from datetime import datetime, timedelta
import os
import json

# 1. Credentials Setup
creds_json = os.environ.get('GCP_CREDENTIALS')

if not creds_json:
    print("CRITICAL: GCP_CREDENTIALS secret missing!")
    exit(1)

creds_dict = json.loads(creds_json)

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

spreadsheet_id = "1FhVIdKHlPFGoMjwZFtcKTOv7MwYOLQB6fzj8bo6DBuw"
worksheet = client.open_by_key(spreadsheet_id).worksheet("Top 250 Stocks")

ETF_NAME_KEYWORDS = ['ETF', 'BEES', 'REIT', 'INVIT', 'INVT', 'LIQUIDBEES', 'GOLDBEES', 'NIFTYBEES']
MAX_PRICE = 15000

def fetch_nse_etf_symbols():
    url = "https://www.nseindia.com/api/etf"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json'
    }
    try:
        session = requests.Session()
        session.headers.update(headers)
        session.get("https://www.nseindia.com", timeout=10)
        response = session.get(url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            rows = data.get('data', [])
            return {row['symbol'].strip().upper() for row in rows if row.get('symbol')}
    except Exception as e:
        print(f"ETF Fetch fallback active: {e}")
    return set()

def is_etf_or_trust(symbol, name, etf_symbol_set):
    sym_u = (symbol or '').strip().upper()
    nm_u = (name or '').strip().upper()
    if sym_u in etf_symbol_set: return True
    for kw in ETF_NAME_KEYWORDS:
        if kw in sym_u or kw in nm_u: return True
    return False

# 3. NSE Data Fetcher
def fetch_bhavcopy_for_date(date_obj, etf_symbol_set):
    date_str = date_obj.strftime("%Y%m%d")
    url = f"https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{date_str}_F_0000.csv.zip"
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        print(f"Checking file for {date_str}")
        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code == 200:
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                csv_filename = z.namelist()[0]
                with z.open(csv_filename) as f:
                    df = pd.read_csv(f)
                    df.columns = [c.strip() for c in df.columns]

                    sym_col = next((c for c in ['TckrSymb', 'SYMBOL'] if c in df.columns), None)
                    close_col = next((c for c in ['ClsPric', 'CLOSE'] if c in df.columns), None)
                    series_col = next((c for c in ['SctySrs', 'SERIES'] if c in df.columns), None)
                    turnover_col = next((c for c in ['TtlTrfVal', 'TOTTRDVAL'] if c in df.columns), None)
                    name_col = next((c for c in ['FinInstrmNm', 'SECURITY'] if c in df.columns), None)

                    if not all([sym_col, close_col, series_col, turnover_col]): return None

                    df = df[df[series_col] == 'EQ']
                    df = df[~df.apply(lambda r: is_etf_or_trust(r[sym_col], r[name_col] if name_col else '', etf_symbol_set), axis=1)]
                    df = df[df[close_col] <= MAX_PRICE]
                    df = df.sort_values(by=turnover_col, ascending=False)
                    
                    top_250 = df.head(250)
                    
                    # ഫോർമുലകൾ ഗൂഗിൾ ഷീറ്റിലേക്ക് നേരിട്ട് ഇൻജക്ട് ചെയ്യുന്ന ലോജിക്
                    final_rows = []
                    for idx, row in top_250.iterrows():
                        ticker = str(row[sym_col]).strip()
                        yahoo_ticker = f"{ticker}.NS"
                        
                        # കോഡിങ് കൊട്ടേഷൻ എററുകൾ വരാത്ത രീതിയിൽ ഫോർമുലകൾ മാറ്റിയത്:
                        live_price_f = f'=GOOGLEFINANCE("{yahoo_ticker}", "price")'
                        dma200_f = f'=AVERAGE(INDEX(GOOGLEFINANCE("{yahoo_ticker}", "price", TODAY()-300, TODAY()), 0, 2))'
                        
                        final_rows.append([ticker, float(row[turnover_col]), live_price_f, dma200_f])
                        
                    return final_rows
    except Exception as e:
        print(f"Error logic: {str(e)}")
    return None

# 4. Execution Logic
date = datetime.utcnow() + timedelta(hours=5, minutes=30)
etf_symbol_set = fetch_nse_etf_symbols()
data_to_insert = None
fetched_date_str = ""

for i in range(7):
    test_date = date - timedelta(days=i)
    if test_date.weekday() >= 5: continue
    data_to_insert = fetch_bhavcopy_for_date(test_date, etf_symbol_set)
    if data_to_insert:
        fetched_date_str = test_date.strftime('%d-%b-%Y')
        break

# 5. Update Sheet
if data_to_insert:
    try:
        worksheet.batch_clear(['A2:D251'])
        worksheet.update(range_name='A2', values=data_to_insert)

        ist_now = (datetime.utcnow() + timedelta(hours=5, minutes=30)).strftime('%d-%b %H:%M')
        status_msg = f"Data Date: {fetched_date_str} | Last Update: {ist_now} (IST)"
        worksheet.update(range_name='K2', values=[[status_msg]])
        print(f"SUCCESS: Updated for {fetched_date_str}")
    except Exception as e:
        print(f"Google Sheet Error: {str(e)}")
else:
    print("FAILED: No file found.")
