"""Run the entire project: python run_project.py (uses included data)."""
import argparse
from dataclasses import replace, asdict
import json
import platform
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from data_io import ROOT, load, download
from strategy import Config, indicators, backtest, buy_hold, metrics

PERIODS = {'Development':('2018-01-01','2022-12-31'), 'Test':('2023-01-01','2025-12-31')}
OUT = ROOT/'results'
COLORS = ['#147d92','#e5943b','#57657b','#7b4dad']
plt.rcParams.update({'figure.facecolor':'white','axes.spines.top':False,'axes.spines.right':False,
                    'axes.grid':True,'grid.alpha':0.18,'font.size':10,'axes.titleweight':'bold'})


def save(fig, name):
    fig.tight_layout()
    fig.savefig(OUT/name,dpi=160,bbox_inches='tight')
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download',action='store_true',help='Replace saved market data from Yahoo')
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    if args.download:
        download()
    data, quality = {}, {}
    for name in ['INFY','TCS','NIFTY']:
        data[name], quality[name] = load(name)
    common = data['INFY'].index.intersection(data['TCS'].index).intersection(data['NIFTY'].index)
    for name in data:
        quality[name]['excluded_noncommon_dates'] = [str(x.date()) for x in data[name].index.difference(common)]
        data[name] = data[name].loc[common]
    (OUT/'data_quality.json').write_text(json.dumps(quality,indent=2),encoding='utf-8')
    c = Config()
    (OUT/'configuration.json').write_text(json.dumps({'parameters':asdict(c),'periods':PERIODS,
        'selection':'Fixed before evaluation; sensitivity grid is development-only.',
        'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,
        'matplotlib':matplotlib.__version__},indent=2),encoding='utf-8')
    rows, accounts, logs, diagnostic_rows, year_rows, regime_rows = [], {}, {}, [], [], []
    prepared = {s:indicators(data[s],c) for s in ['INFY','TCS']}
    for name, d in prepared.items():
        d.to_csv(OUT/f'{name}_indicators.csv')
        for period,(start,end) in PERIODS.items():
            curves = pd.DataFrame(index=d.loc[start:end].index)
            for label, filtered in [('EMA + ADX',True),('EMA only',False)]:
                account, trades = backtest(d,start,end,filtered,c)
                key = (name,period,label)
                accounts[key], logs[key] = account, trades
                curves[label] = account.equity
                m = metrics(account.equity,trades,c.capital)
                rows.append(dict(stock=name,period=period,strategy=label,**m))
                stem = f'{name}_{period}_{"filtered" if filtered else "basic"}'
                account.to_csv(OUT/f'{stem}_account.csv')
                trades.to_csv(OUT/f'{stem}_trades.csv',index=False)
                winning = trades.loc[trades.pnl>0,'pnl']
                losing = trades.pnl.lt(0).astype(int).tolist()
                longest = run = 0
                for v in losing:
                    run = run+1 if v else 0
                    longest = max(longest,run)
                givebacks = []
                for t in trades.itertuples():
                    peak = d.loc[t.entry_date:t.exit_date,'Close'].max()
                    givebacks.append(max(0,1-t.exit_price/peak))
                diagnostic_rows.append(dict(stock=name,period=period,strategy=label,
                    exposure=account.exposure.mean(),avg_holding_sessions=trades.holding_sessions.mean(),
                    avg_entry_lag=trades.entry_lag_sessions.mean(),max_consecutive_losses=longest,
                    top3_share_gross_profit=winning.nlargest(3).sum()/winning.sum() if winning.sum()>0 else np.nan,
                    mean_close_peak_giveback=np.mean(givebacks) if givebacks else np.nan))
            curves['Buy & hold'] = buy_hold(d,start,end,c)
            idx = data['NIFTY'].loc[start:end]
            curves['Nifty 50 price'] = c.capital*idx.Close/idx.Open.iloc[0]
            for label in ['Buy & hold','Nifty 50 price']:
                rows.append(dict(stock=name,period=period,strategy=label,**metrics(curves[label])))
            curves.to_csv(OUT/f'{name}_{period}_curves.csv')
            fig, axes = plt.subplots(2,1,figsize=(10,6.8),sharex=True,height_ratios=[2,1])
            for label,color in zip(curves.columns,COLORS):
                axes[0].plot(curves.index,curves[label]/1000,label=label,color=color,lw=1.4)
                high = curves[label].cummax().clip(lower=c.capital)
                axes[1].plot(curves.index,100*(curves[label]/high-1),color=color,lw=1)
            axes[0].set(title=f'{name} | {period} | starting capital INR 100,000',ylabel='Equity (INR thousands)')
            axes[0].legend(loc='upper left',ncol=2,fontsize=8)
            axes[1].set(ylabel='Drawdown (%)')
            save(fig,f'{name}_{period}_performance.png')
            if period == 'Test':
                returns = curves.pct_change()
                returns.iloc[0] = curves.iloc[0]/c.capital-1
                for year, r in returns.groupby(returns.index.year):
                    for label in returns:
                        year_rows.append(dict(stock=name,year=int(year),strategy=label,
                                              return_value=(1+r[label]).prod()-1))
                prior = d.shift(1).loc[curves.index]
                regimes = pd.Series(np.where(prior.adx<25,'Weak / sideways',
                    np.where(prior.bull,'Strong up','Strong down')),index=curves.index)
                pnl = curves['EMA + ADX'].diff()
                pnl.iloc[0] = curves['EMA + ADX'].iloc[0]-c.capital
                for regime in ['Weak / sideways','Strong up','Strong down']:
                    mask = regimes.eq(regime)
                    regime_rows.append(dict(stock=name,regime=regime,sessions=int(mask.sum()),
                        pnl_inr=pnl[mask].sum(),mean_daily_return=returns.loc[mask,'EMA + ADX'].mean()))
    metrics_table = pd.DataFrame(rows)
    metrics_table.to_csv(OUT/'performance_metrics.csv',index=False)
    diagnostics = pd.DataFrame(diagnostic_rows)
    diagnostics.to_csv(OUT/'trade_diagnostics.csv',index=False)
    pd.DataFrame(year_rows).to_csv(OUT/'test_yearly_returns.csv',index=False)
    pd.DataFrame(regime_rows).to_csv(OUT/'test_regime_attribution.csv',index=False)

    # Sensitivity is intentionally restricted to development dates.
    sensitivity = []
    for stock in ['INFY','TCS']:
        for fast,slow in [(15,40),(20,50),(25,60)]:
            for threshold in [20,25,30]:
                cfg = replace(c,fast=fast,slow=slow,adx_min=threshold)
                a,t = backtest(indicators(data[stock],cfg),*PERIODS['Development'],True,cfg)
                sensitivity.append(dict(stock=stock,fast=fast,slow=slow,adx=threshold,
                                        **metrics(a.equity,t)))
    sensitivity = pd.DataFrame(sensitivity)
    sensitivity.to_csv(OUT/'development_sensitivity.csv',index=False)
    costs = []
    for stock in ['INFY','TCS']:
        for fee, slip in [(0,0),(.0015,.0005),(.003,.001)]:
            cfg = replace(c,fee=fee,slippage=slip)
            a,t = backtest(prepared[stock],*PERIODS['Test'],True,cfg)
            costs.append(dict(stock=stock,fee_bps=fee*10000,slippage_bps=slip*10000,
                              **metrics(a.equity,t)))
    pd.DataFrame(costs).to_csv(OUT/'test_cost_stress.csv',index=False)

    # Exploratory prices, volume, and daily-return distribution.
    fig, ax = plt.subplots(3,1,figsize=(10,7.8))
    for stock,color in zip(['INFY','TCS'],COLORS):
        x = data[stock]
        ax[0].plot(x.index,100*x.Close/x.Close.iloc[0],label=stock,color=color)
        ax[1].plot(x.index,x.Volume.rolling(20).mean()/1e6,label=stock,color=color,lw=1)
        ax[2].hist(100*x.Close.pct_change().dropna(),bins=80,alpha=.5,label=stock,color=color)
    ax[0].axvline(pd.Timestamp('2023-01-01'),color='#555555',ls='--')
    ax[0].set(title='Exploratory data | warm-up + development + test',ylabel='Adjusted price (start = 100)')
    ax[1].set(ylabel='20-day mean volume (million)')
    ax[2].set(xlabel='Daily adjusted close return (%)',ylabel='Sessions')
    ax[0].legend(); ax[2].legend()
    save(fig,'data_exploration.png')
    for stock in ['INFY','TCS']:
        d = prepared[stock].loc[slice(*PERIODS['Test'])]
        t = logs[(stock,'Test','EMA + ADX')]
        fig,ax = plt.subplots(2,1,figsize=(10,6.4),sharex=True,height_ratios=[2.5,1])
        for col,label,color in [('Close','Adjusted close','#34445a'),('fast','EMA 20',COLORS[0]),('slow','EMA 50',COLORS[1])]:
            ax[0].plot(d.index,d[col],label=label,color=color,lw=1)
        ax[0].scatter(t.entry_date,t.entry_price,marker='^',color='#16815d',label='Entry',s=30,zorder=5)
        ax[0].scatter(t.exit_date,t.exit_price,marker='v',color='#c73d4c',label='Exit',s=30,zorder=5)
        ax[0].set(title=f'{stock} | test trades | EMA + ADX',ylabel='Adjusted price units')
        ax[0].legend(ncol=5,fontsize=8)
        ax[1].plot(d.index,d.adx,color=COLORS[0],lw=1)
        ax[1].axhline(25,color=COLORS[1],ls='--')
        ax[1].set(ylabel='ADX (14)')
        save(fig,f'{stock}_test_trades.png')
    from report import build_report
    build_report(metrics_table,diagnostics,sensitivity,pd.DataFrame(costs),quality)
    print('\nTEST RESULTS (net of modelled costs; index is gross price return):')
    print(metrics_table[metrics_table.period=='Test'][['stock','strategy','cumulative_return','sharpe','max_drawdown','trades']].to_string(index=False))
    print('\nComplete: results/Technical_Report.pdf and result CSV/PNG files.')

if __name__ == '__main__':
    main()
