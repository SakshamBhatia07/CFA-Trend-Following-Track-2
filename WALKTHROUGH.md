# Understand and present your project

## 1. The idea in plain language

A trend follower buys after an upward trend is visible and stays invested while
it continues. It accepts late entry/exit in exchange for a simple repeatable rule.
It loses when prices reverse repeatedly. We test whether ADX confirmation helps.

EMA gives more weight to recent prices. EMA20 above EMA50 defines upward
momentum. ADX14 estimates trend strength, with no bullish/bearish direction of its
own. ATR14 estimates recent price movement and sets a volatility-scaled stop.

## 2. Follow the code in this order

1. `data_io.load`: read the saved real data, sort dates, remove invalid rows and
   consistently adjust open/high/low/close for vendor corporate actions.
2. `strategy.indicators`: calculate EMA, ATR and ADX using information available
   through each date. One year of warm-up reduces initialization effects.
3. `strategy.backtest`: loop through sessions and decide using yesterday's signal.
   Track cash and units; equity = cash + units * today's close.
4. `strategy.metrics`: calculate performance from equity and completed trades.
5. `run_project.main`: compare strategies, test sensitivity and produce figures.
6. `report.build_report`: put actual computed numbers into the PDF.

## 3. Explain one hypothetical trade

Suppose yesterday EMA20 > EMA50, ADX = 30 and ATR = 20. Available cash is
INR 100,000. Today's open is 1,000.

- Buy fill after 5 bps slippage: 1,000.50.
- Stop distance: 3 * 20 = 60 adjusted price units.
- Risk-sized units: 1,000 / 60 = 16.6667.
- Allocation-cap units: 95,000 / (1,000.50 * 1.0015), about 94.81.
- Use the smaller number: 16.6667 adjusted units.
- Entry fee: 16.6667 * 1,000.50 * 0.0015, about INR 25.01.
- Initial stop: 940.50.

If a later close reaches 1,100 with ATR still 20, the next session's stop becomes
1,040. A gap down to 1,020 exits at the open, with adverse slippage and fees; it
cannot pretend to sell at 1,040. The stop only rises after the close, never based
on an intraday high that may have happened after the day's low.

The 1% target describes price-distance risk before costs and gaps. It is not a
guarantee of maximum loss. Fractional adjusted units are an explicit approximation.

## 4. Why the test period matters

Development is 2018-2022; evaluation is 2023-2025. The 20/50 and ADX25 rules were
fixed before running the test. The sensitivity grid only uses development data.
Both accounts start in cash, so there are no carried development positions.
Test indicators may use prior historical prices: that is valid past information.
Do not change rules after looking at the test and still call it untouched.

## 5. Interpret the mandatory metrics

- Cumulative return: total change in wealth after costs.
- Annualized return: geometric return using 252 trading sessions per year.
- Sharpe: average daily return divided by its standard deviation, annualized.
- Sortino: scales return by downside variation; target and risk-free rate are zero.
- Drawdown: fall from the previous peak, including the initial INR 100,000.
- Win rate: profitable completed trades / all completed trades.
- Profit factor: winning P&L sum / absolute losing P&L sum.
- Average and maximum profit/loss: calculated separately for winners and losers.
- Benchmark return: owning the same stock with costs; Nifty price also shown.

A strategy can have low win rate and still profit if a few wins are large. High
profit concentration also makes the estimate fragile. Cash reduces volatility and
can make benchmark comparisons look better unless exposure is considered.

## 6. Check a real trade yourself

Open `results/INFY_Test_filtered_trades.csv` in VS Code. Take the first row:

1. Check `signal_date` is earlier than `entry_date`.
2. Find both dates in `INFY_indicators.csv` and inspect EMA/ADX/ATR.
3. Entry price should equal that day's adjusted open * 1.0005.
4. Verify entry fee = units * entry price * 0.0015.
5. Net P&L = units * (exit price - entry price) - entry fee - exit fee.
6. Find the corresponding daily equity in the account CSV.

Summing all completed trade P&L equals final equity minus initial capital,
because all positions are closed at the evaluation boundary.

## 7. Questions you should be able to answer

**Why EMA20/50?** A simple medium-horizon starting pair, not an optimized claim.
We report nearby choices using development data to show sensitivity.

**Why use ADX?** To test whether avoiding weak-trend entries helps. It can also
miss opportunities and delay entry. Compare actual filtered versus basic results.

**Why not buy at today's close using today's close signal?** That usually assumes
information is known before the closing execution. Next open avoids that shortcut.

**Why can there be re-entry without a new crossover?** The strategy uses the
bullish EMA regime. After a stop it may enter on a later eligible session.

**Why do you not short?** This is a long-only cash-equity study, with no model of
Indian short availability, carry costs or derivative contracts.

**Are dividends included?** Indirectly through adjusted prices. This approximates
reinvested total returns, not actual dividend cash payment dates. No double credit.

**Why can buy-and-hold win?** The strategy is often mostly in cash, enters late,
pays repeated costs and can lose to long uninterrupted upward moves.

**Are these results statistically proven?** No. Few trades, two related stocks,
retrospective selection and one holdout limit evidence.

**What would you improve?** Forward paper trading, a point-in-time multi-sector
universe, exact costs/actions, capacity constraints and multiple walk-forward tests.

## 8. A five-minute presentation

1. 30 seconds: question and trend-following idea.
2. 45 seconds: data, adjustment, development/test split.
3. 60 seconds: exact entry/exit/sizing and the hypothetical trade above.
4. 90 seconds: actual result table, equity/drawdown and basic/benchmark comparison.
5. 45 seconds: concentration, sensitivity and limitations.
6. 30 seconds: lessons learned and possible improvements.

Use the actual PDF numbers, even if returns are poor. Explain what the experiment
shows rather than claiming the strategy must make money.
