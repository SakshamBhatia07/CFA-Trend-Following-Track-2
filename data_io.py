"""Download once; reruns use the saved CSV snapshot without internet."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import urllib.request
import urllib.parse
import time
import pandas as pd
ROOT = Path(__file__).resolve().parent
SYMBOLS = {'INFY':'INFY.NS', 'TCS':'TCS.NS', 'NIFTY':'^NSEI'}


def download():
    folder = ROOT/'data'
    folder.mkdir(exist_ok=True)
    manifest = {'retrieved_utc':datetime.now(timezone.utc).isoformat(),
        'source':'Yahoo Finance chart API', 'start':'2017-01-01','end_exclusive':'2026-01-01',
        'adjustment':'Adjusted OHLC = vendor OHLC * AdjClose / Close; vendor volume unchanged.',
        'files':{}}
    for name, symbol in SYMBOLS.items():
        p1 = int(datetime(2017,1,1,tzinfo=timezone.utc).timestamp())
        p2 = int(datetime(2026,1,1,tzinfo=timezone.utc).timestamp())
        url = ('https://query1.finance.yahoo.com/v8/finance/chart/'+urllib.parse.quote(symbol)
               +f'?period1={p1}&period2={p2}&interval=1d&events=div%2Csplits')
        req = urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(req,timeout=60) as response:
            raw = response.read()
        (folder/f'{name}_source.json').write_bytes(raw)
        data = json.loads(raw)['chart']['result'][0]
        q = data['indicators']['quote'][0]
        df = pd.DataFrame({k.capitalize():q[k] for k in ['open','high','low','close','volume']})
        df['AdjClose'] = data['indicators']['adjclose'][0]['adjclose']
        df['Date'] = pd.to_datetime(data['timestamp'],unit='s',utc=True).tz_convert('Asia/Kolkata').date
        df = df.set_index('Date')
        df.to_csv(folder/f'{name}.csv',float_format='%.10f')
        manifest['files'][name] = {'symbol':symbol,'url':url,'rows':len(df),
            'csv_sha256':hashlib.sha256((folder/f'{name}.csv').read_bytes()).hexdigest(),
            'raw_sha256':hashlib.sha256(raw).hexdigest(),'corporate_events':data.get('events',{})}
        print(f'Downloaded {name}: {len(df)} sessions')
        time.sleep(1)
    (folder/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')


def load(name):
    path = ROOT/'data'/f'{name}.csv'
    if not path.exists():
        raise FileNotFoundError('Missing data. Run: python run_project.py --download')
    d = pd.read_csv(path,parse_dates=['Date']).set_index('Date').sort_index()
    before, duplicates = len(d), int(d.index.duplicated().sum())
    d = d[~d.index.duplicated(keep='last')]
    missing = d.isna().sum().to_dict()
    d = d.dropna(subset=['Open','High','Low','Close','AdjClose','Volume'])
    valid = ((d[['Open','High','Low','Close','AdjClose']] > 0).all(axis=1)
             & (d.Volume >= 0) & (d.High >= d[['Open','Close','Low']].max(axis=1)-1e-6)
             & (d.Low <= d[['Open','Close','High']].min(axis=1)+1e-6))
    invalid = int((~valid).sum())
    d = d[valid].copy()
    factor = d.AdjClose/d.Close
    d[['Open','High','Low','Close']] = d[['Open','High','Low','Close']].mul(factor,axis=0)
    quality = dict(raw_rows=before,clean_rows=len(d),duplicates=duplicates,
        missing_by_column=missing,invalid_rows=invalid,
        zero_volume_rows=int((d.Volume == 0).sum()),
        first_date=str(d.index.min().date()),last_date=str(d.index.max().date()))
    return d, quality
