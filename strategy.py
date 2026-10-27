"""Causal indicators, long-only accounting and performance metrics.
Prices are adjusted units; fractional units are a research approximation.
"""
from dataclasses import dataclass
import numpy as np
import pandas as pd

@dataclass(frozen=True)
class Config:
    fast: int = 20
    slow: int = 50
    length: int = 14
    adx_min: float = 25.0
    atr_multiple: float = 3.0
    risk: float = 0.01
    allocation: float = 0.95
    fee: float = 0.0015  # assumed 15 basis points per side
    slippage: float = 0.0005  # assumed 5 basis points per side
    capital: float = 100000.0


def wilder(s, n):
    """SMA seed followed by Wilder recursion, with no future observations."""
    out = pd.Series(np.nan, index=s.index, dtype=float)
    valid = s.dropna()
    if len(valid) < n:
        return out
    start = s.index.get_loc(valid.index[n-1])
    out.iloc[start] = valid.iloc[:n].mean()
    for i in range(start+1, len(s)):
        out.iloc[i] = (out.iloc[i-1]*(n-1)+s.iloc[i])/n
    return out


def indicators(df, c=Config()):
    d = df.copy()
    close = d.Close
    d['fast'] = close.ewm(span=c.fast, adjust=False, min_periods=c.fast).mean()
    d['slow'] = close.ewm(span=c.slow, adjust=False, min_periods=c.slow).mean()
    tr = pd.concat([d.High-d.Low, (d.High-close.shift()).abs(),
                    (d.Low-close.shift()).abs()], axis=1).max(axis=1)
    tr.iloc[0] = np.nan
    up, down = d.High.diff(), -d.Low.diff()
    plus = up.where((up > down) & (up > 0), 0.0)
    minus = down.where((down > up) & (down > 0), 0.0)
    plus.iloc[0] = minus.iloc[0] = np.nan
    d['atr'] = wilder(tr, c.length)
    pdi = 100*wilder(plus, c.length)/d.atr.replace(0, np.nan)
    mdi = 100*wilder(minus, c.length)/d.atr.replace(0, np.nan)
    dx = 100*(pdi-mdi).abs()/(pdi+mdi).replace(0, np.nan)
    dx = dx.where((pdi+mdi) != 0, 0.0)
    d['adx'] = wilder(dx, c.length)
    d['bull'] = d.fast > d.slow
    return d

TRADE_COLUMNS = ['signal_date','entry_date','exit_date','units','entry_price',
                 'exit_price','entry_fee','exit_fee','pnl','return_pct',
                 'holding_sessions','reason','entry_adx','entry_lag_sessions']


def backtest(d, start, end, filtered=True, c=Config()):
    """Prior-close signals trade next open. Updated stops apply tomorrow.
    Periods start in cash and liquidate at their scheduled final close.
    """
    positions = np.flatnonzero((d.index >= start) & (d.index <= end))
    if not len(positions) or positions[0] == 0:
        raise ValueError('Evaluation needs data and a preceding warm-up session.')
    cash, units, stop, peak = c.capital, 0.0, np.nan, np.nan
    entry, records, trades = None, [], []
    bull_start, bull_starts = None, {}
    for j in range(len(d)):
        if d.bull.iloc[j] and (j == 0 or not d.bull.iloc[j-1]):
            bull_start = j
        bull_starts[j] = bull_start

    def sell(raw, date, i, reason):
        nonlocal cash, units, entry
        fill = raw*(1-c.slippage)
        fee = units*fill*c.fee
        proceeds = units*fill-fee
        pnl = proceeds-entry['cost']
        cash += proceeds
        trades.append(dict(signal_date=entry['signal_date'], entry_date=entry['date'],
            exit_date=date, units=units, entry_price=entry['fill'], exit_price=fill,
            entry_fee=entry['fee'], exit_fee=fee, pnl=pnl,
            return_pct=100*pnl/entry['cost'], holding_sessions=i-entry['i']+1,
            reason=reason, entry_adx=entry['adx'], entry_lag_sessions=entry['lag']))
        units, entry = 0.0, None

    for i in positions:
        date, row, prev = d.index[i], d.iloc[i], d.iloc[i-1]
        exited = False
        exposed = units > 0
        if units and row.Open <= stop:
            sell(row.Open, date, i, 'gap_stop'); exited = True
        elif units and not prev.bull:
            sell(row.Open, date, i, 'ema_reversal'); exited = True
        elif units and row.Low <= stop:
            sell(stop, date, i, 'trailing_stop'); exited = True
        if not units and not exited and i != positions[-1]:
            eligible = prev.bull and pd.notna(prev.atr) and prev.atr > 0
            eligible = eligible and (not filtered or prev.adx >= c.adx_min)
            if eligible:
                fill = row.Open*(1+c.slippage)
                distance = c.atr_multiple*prev.atr
                units = min(cash*c.risk/distance, cash*c.allocation/(fill*(1+c.fee)))
                fee = units*fill*c.fee
                cost = units*fill+fee
                cash -= cost
                stop, peak = fill-distance, fill
                entry = dict(date=date, signal_date=d.index[i-1], i=i, fill=fill,
                             fee=fee, cost=cost, adx=prev.adx, lag=i-bull_starts[i-1])
                exposed = True
                if row.Low <= stop:
                    sell(min(row.Open, stop), date, i, 'entry_day_stop')
        if units and i == positions[-1]:
            sell(row.Close, date, i, 'period_end')
        if units:
            peak = max(peak, row.Close)
            stop = max(stop, peak-c.atr_multiple*row.atr)
        equity = cash+units*row.Close
        assert cash >= -1e-7 and units >= 0 and equity > 0
        records.append(dict(Date=date, cash=cash, units=units, equity=equity,
                            stop=stop if units else np.nan, exposure=float(exposed)))
    return pd.DataFrame(records).set_index('Date'), pd.DataFrame(trades, columns=TRADE_COLUMNS)


def buy_hold(d, start, end, c=Config()):
    """Same-stock passive benchmark with identical round-trip assumptions."""
    x = d.loc[start:end]
    units = c.capital/(x.Open.iloc[0]*(1+c.slippage)*(1+c.fee))
    equity = units*x.Close
    equity.iloc[-1] *= (1-c.slippage)*(1-c.fee)
    return equity


def metrics(equity, trades=None, capital=100000):
    r = equity.pct_change()
    r.iloc[0] = equity.iloc[0]/capital-1
    wealth = pd.concat([pd.Series([capital]), equity.reset_index(drop=True)], ignore_index=True)
    dd = wealth/wealth.cummax()-1
    sd = r.std(ddof=1)
    downside = np.sqrt(np.mean(np.minimum(r, 0)**2))
    result = dict(cumulative_return=equity.iloc[-1]/capital-1,
        annualized_return=(equity.iloc[-1]/capital)**(252/len(r))-1,
        sharpe=np.sqrt(252)*r.mean()/sd if sd > 1e-12 else np.nan,
        sortino=np.sqrt(252)*r.mean()/downside if downside > 1e-12 else np.nan,
        max_drawdown=dd.min())
    if trades is not None:
        p = trades.pnl
        wins, losses = p[p>0], p[p<0]
        result.update(trades=len(p), win_rate=(p>0).mean() if len(p) else np.nan,
            profit_factor=wins.sum()/abs(losses.sum()) if len(losses) else np.nan,
            average_profit=wins.mean(), average_loss=losses.mean(),
            maximum_profit=wins.max(), maximum_loss=losses.min(), net_profit=p.sum())
        assert np.isclose(p.sum(), equity.iloc[-1]-capital, atol=1e-6)
    return result
