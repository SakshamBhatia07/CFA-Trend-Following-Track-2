import unittest
from dataclasses import replace
import numpy as np
import pandas as pd
from strategy import Config, indicators, wilder, backtest, metrics


def fixture():
    ix=pd.date_range('2024-01-01',periods=6,freq='B')
    return pd.DataFrame(dict(Open=[100.]*6,High=[102.]*6,Low=[99.]*6,
        Close=[100.]*6,Volume=[1000]*6,bull=[True]*6,atr=[2.]*6,adx=[30.]*6),index=ix)


class BacktestTests(unittest.TestCase):
    def test_wilder_seed(self):
        r=wilder(pd.Series([1.,2.,3.,4.,5.]),3)
        self.assertTrue(r.iloc[:2].isna().all())
        self.assertAlmostEqual(r.iloc[2],2)
        self.assertAlmostEqual(r.iloc[3],8/3)

    def test_indicator_causality(self):
        rng=np.random.default_rng(42)
        close=100+np.cumsum(rng.normal(size=180))
        d=pd.DataFrame({'Close':close,'Open':close,'High':close+2,'Low':close-2,'Volume':100},index=pd.date_range('2020-01-01',periods=180))
        first=indicators(d)
        changed=d.copy(); changed.iloc[140:,0:4] *= 2
        second=indicators(changed)
        pd.testing.assert_frame_equal(first.iloc[:140],second.iloc[:140])

    def test_next_open_and_cost_reconciliation(self):
        d=fixture(); d.loc[d.index[:2],'bull']=False
        d.loc[d.index[3],'Open']=101
        a,t=backtest(d,str(d.index[1].date()),str(d.index[-1].date()))
        self.assertEqual(t.iloc[0].signal_date,d.index[2])
        self.assertEqual(t.iloc[0].entry_date,d.index[3])
        self.assertAlmostEqual(t.iloc[0].entry_price,101*1.0005)
        self.assertAlmostEqual(t.pnl.sum(),a.equity.iloc[-1]-100000)
        self.assertTrue((a.cash>=0).all())

    def test_gap_stop(self):
        d=fixture(); d.loc[d.index[2],['Open','High','Low','Close']]=[90,92,89,91]
        a,t=backtest(d,str(d.index[1].date()),str(d.index[-1].date()))
        self.assertEqual(t.iloc[0].reason,'gap_stop')
        self.assertAlmostEqual(t.iloc[0].exit_price,90*.9995)

    def test_stop_not_raised_intraday(self):
        d=fixture(); d.loc[d.index[1],['High','Low','Close']]=[111,95,110]
        a,t=backtest(d,str(d.index[1].date()),str(d.index[-1].date()))
        self.assertGreater(a.units.iloc[0],0)
        self.assertEqual(t.iloc[0].exit_date,d.index[2])
        self.assertEqual(t.iloc[0].reason,'gap_stop')

    def test_entry_day_stop(self):
        d=fixture(); d.loc[d.index[1],'Low']=90
        a,t=backtest(d,str(d.index[1].date()),str(d.index[-1].date()))
        self.assertEqual(t.iloc[0].reason,'entry_day_stop')
        self.assertEqual(t.iloc[0].holding_sessions,1)

    def test_adx_is_entry_filter(self):
        d=fixture(); d['adx']=10
        a,t=backtest(d,str(d.index[1].date()),str(d.index[-1].date()),True)
        self.assertEqual(len(t),0)
        self.assertTrue((a.equity==100000).all())
        _,basic=backtest(d,str(d.index[1].date()),str(d.index[-1].date()),False)
        self.assertGreater(len(basic),0)

    def test_first_day_return_included(self):
        m=metrics(pd.Series([90000.,90000.]))
        self.assertAlmostEqual(m['max_drawdown'],-.1)
        self.assertLess(m['sharpe'],0)

    def test_undefined_ratios(self):
        m=metrics(pd.Series([100000.]*3),pd.DataFrame({'pnl':[]}))
        self.assertTrue(np.isnan(m['sharpe']))
        self.assertTrue(np.isnan(m['sortino']))
        self.assertTrue(np.isnan(m['profit_factor']))
        self.assertEqual(m['trades'],0)

    def test_no_cost_flat_price(self):
        d=fixture(); c=replace(Config(),fee=0,slippage=0)
        a,t=backtest(d,str(d.index[1].date()),str(d.index[-1].date()),c=c)
        self.assertAlmostEqual(a.equity.iloc[-1],100000)
        self.assertEqual(t.iloc[-1].reason,'period_end')

if __name__=='__main__': unittest.main()
