# CFA intermediate project: trend following

Complete, reproducible Python project for Track 2 of the supplied assignment.
The results are historical research, not a recommendation to trade.

## What you need to do today

1. Open this entire folder in VS Code (File > Open Folder).
2. Read `results/Technical_Report.pdf` and the result interpretation below.
3. Open Terminal > New Terminal. Use the commands below to run it yourself.
4. Read `WALKTHROUGH.md` and trace one trade in a trade-log CSV.
5. Add your name/roll number if your club requires it. The report generator is
   `report.py`; keep the assistance acknowledgement accurate.
6. Submit the PDF plus the source project, data snapshot and requirements.
   Do not submit `.venv`, `__pycache__` or temporary package files.

## Run on this computer

A local virtual environment is prepared in `.venv`. In the VS Code PowerShell
terminal, run these commands from this project folder (activation is unnecessary):

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe run_project.py
```

The first command checks execution logic. The second regenerates all results and
`results/Technical_Report.pdf` from the saved real historical data, without internet.

If using the Python extension, press Ctrl+Shift+P, choose **Python: Select
Interpreter**, then choose `.venv\Scripts\python.exe`. Open `run_project.py` and
use Run Python File or the included debug configuration.

## Fresh setup on another computer

Install Python 3.11 or newer and the Microsoft Python extension for VS Code.
Open the project folder, then run:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe run_project.py
```

No `Activate.ps1` is needed, avoiding PowerShell execution-policy problems.
If `python` is not found, try `py -3` for the first command.

Only if you deliberately want to replace the included data snapshot:

```powershell
.\.venv\Scripts\python.exe run_project.py --download
```

Yahoo can throttle downloads; the included snapshot avoids that dependency.
Refreshing can change adjusted history and numerical results. Preserve the
original `data` folder if you need to retain the submitted experiment.

## Experiment

- Stocks: Infosys (primary) and TCS (cross-stock check); separate accounts.
- Daily OHLCV: January 2017 through December 2025; 2017 indicator warm-up.
- Development: 2018-2022. Fixed chronological test: 2023-2025.
- EMA 20 > EMA 50 and ADX 14 >= 25 enables entry at next open.
- Basic comparison removes ADX only; other rules remain the same.
- Initial and close-based trailing stop: 3 ATR; no intraday stop ratcheting.
- Position risk target 1%; allocation ceiling 95%; capital INR 100,000.
- Assumed fees 15 bps + slippage 5 bps per side; no cash interest or leverage.
- Benchmarks: same-stock adjusted buy-and-hold after costs and gross Nifty price.
- No test-period optimization. Parameter sensitivity uses development only.

The strategy uses a bullish EMA **state**, so it can re-enter after a stop while
EMA20 remains above EMA50. It is not restricted to the day of a fresh crossover.
ADX measures strength, not direction. Falling ADX alone does not exit a trade.

## Files to understand

| File | Purpose |
|---|---|
| `run_project.py` | Runs data checks, backtests, comparisons, charts and report |
| `data_io.py` | Downloads/caches data and cleans/adjusts OHLC |
| `strategy.py` | Indicator math, event-driven ledger, metrics |
| `report.py` | Builds the PDF directly from computed results |
| `tests/test_strategy.py` | Deterministic tests of critical trading logic |
| `data/manifest.json` | URLs, retrieval time, checksums, corporate actions |
| `results/performance_metrics.csv` | All required metrics, both periods/stocks |
| `results/*_trades.csv` | Entries, exits, fees, net P&L and exit reasons |
| `results/*_account.csv` | Daily cash, units, equity and active-next-day stop |
| `results/development_sensitivity.csv` | Development-only parameter grid |
| `results/test_cost_stress.csv` | Frozen-test cost sensitivity |
| `results/test_regime_attribution.csv` | P&L in indicator-defined regimes |
| `WALKTHROUGH.md` | Explanation and presentation preparation |

Charts include EDA, development/test equity and drawdown, and both stocks' test
trade markers. The PDF includes all mandatory metrics and the primary charts;
additional TCS charts are saved alongside it.

## Methodological cautions to explain

Adjusted OHLC = vendor OHLC * AdjClose / Close. Fractional adjusted units
approximate total returns; this is not exact integer-share settlement accounting.
Do not add dividends again. Cost assumptions are a flat modelling allowance,
not an audited current Indian delivery-cost schedule. The 1% risk target is not a
loss guarantee in gaps. The index is a gross price benchmark without dividends.
The stocks were selected retrospectively and both are in IT, so evidence is narrow.
This is a retrospective holdout, not a live or prospective validation.

## Sources and assistance

- User-supplied `CFA_InductionTask2026 (1).pdf`, Track 2 and general deliverables.
- Yahoo Finance INFY.NS, TCS.NS and ^NSEI history; exact API URLs in manifest.
- StockCharts ChartSchool: Average Directional Index (ADX), including Wilder smoothing.
  https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/average-directional-index-adx
- NumPy, pandas, Matplotlib and ReportLab documentation.
- OpenAI Codex assisted with implementation, tests, analysis and report drafting.
  Review the work, understand it, and retain the acknowledgement when submitting.

## Measured findings from the included snapshot

For 2023-2025, Infosys EMA + ADX returned 1.41%, versus 0.30% for EMA only,
15.87% for adjusted buy-and-hold, and 44.11% for the gross Nifty price index.
The filtered Infosys maximum drawdown was -3.04%, with 9 completed trades.
TCS EMA + ADX returned -3.97%, versus 1.20% for EMA only and 6.96% for buy-and-hold.
The filter therefore did not improve results consistently across stocks.
The strategy held substantial cash; low drawdown is not proof of an edge.
Use the generated report/CSV for full precision and all development results.
