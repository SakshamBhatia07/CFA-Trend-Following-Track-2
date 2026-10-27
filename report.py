"""Build a technical PDF from computed results."""
from html import escape
import json
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.utils import ImageReader
from data_io import ROOT
OUT = ROOT/'results'

def fmt(v, kind='number'):
    if pd.isna(v): return 'N/A'
    if kind == 'pct': return f'{100*v:.2f}%'
    if kind == 'money': return f'{v:,.2f}'
    if kind == 'int': return str(int(v))
    return f'{v:.2f}'

def build_report(m,diag,sensitivity,costs,quality):
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleCustom',fontSize=28,leading=32,textColor=colors.HexColor('#17334c'),spaceAfter=14))
    styles.add(ParagraphStyle(name='SectionCustom',fontSize=19,leading=23,textColor=colors.HexColor('#17334c'),spaceAfter=13))
    styles.add(ParagraphStyle(name='BodyCustom',fontSize=10,leading=14,spaceAfter=9))
    styles.add(ParagraphStyle(name='SmallCustom',fontSize=8,leading=11,spaceAfter=7))
    flow=[]
    def p(text,style='BodyCustom'): flow.append(Paragraph(text,styles[style]))
    def h(text): p(text,'SectionCustom')
    def page(): flow.append(PageBreak())
    def img(name,width=490):
        path = OUT/name
        w,h = ImageReader(str(path)).getSize()
        flow.append(Image(str(path),width=width,height=width*h/w))
        flow.append(Spacer(1,8))
    def table(headers,rows,widths=None):
        cells = [[Paragraph(escape(str(x)),styles['SmallCustom']) for x in row] for row in [headers]+rows]
        t=Table(cells,colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e4edf2')),
            ('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),5),
            ('TOPPADDING',(0,0),(-1,-1),5),('LINEBELOW',(0,0),(-1,0),.8,colors.HexColor('#147d92')),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f5f7f9')])]))
        flow.append(t); flow.append(Spacer(1,10))
    def get(stock,period,strategy):
        return m[(m.stock==stock)&(m.period==period)&(m.strategy==strategy)].iloc[0]
    a=get('INFY','Test','EMA + ADX'); b=get('INFY','Test','EMA only')
    bh=get('INFY','Test','Buy & hold'); ni=get('INFY','Test','Nifty 50 price')
    p('CFA CLUB | INTERMEDIATE TRACK','SmallCustom')
    p('Following the trend<br/>in Indian equities','TitleCustom')
    p('EMA crossover regime + ADX confirmation + ATR trailing stop','SectionCustom')
    p('Primary study: Infosys. Cross-stock check: TCS. Daily OHLCV, 2017-2025; evaluation begins in 2018. Prepared 27 October 2026.')
    p('<b>Research question.</b> Does requiring trend strength improve a long-only moving-average strategy after costs? Persistent moves can reward delayed entries; sideways prices can create repeated small losses. This experiment tests that trade-off.')
    table(['Infosys test: 2023-2025','Measured value'],[
        ['EMA + ADX net cumulative return',fmt(a.cumulative_return,'pct')],
        ['EMA only net cumulative return',fmt(b.cumulative_return,'pct')],
        ['Same-stock buy-and-hold net return',fmt(bh.cumulative_return,'pct')],
        ['Nifty 50 gross price return',fmt(ni.cumulative_return,'pct')],
        ['EMA + ADX maximum drawdown',fmt(a.max_drawdown,'pct')],
        ['Completed trades / Sharpe',f'{int(a.trades)} / {fmt(a.sharpe)}']],[330,160])
    p(f'<b>Finding.</b> Filtered return minus basic return is {100*(a.cumulative_return-b.cumulative_return):.2f} percentage points. '
      f'Filtered return minus same-stock buy-and-hold is {100*(a.cumulative_return-bh.cumulative_return):.2f} percentage points. '
      'Lower drawdown alone does not establish an edge: the strategy often holds substantial cash.')
    p('<b>Integrity.</b> Parameters were fixed before the test run. The test is a retrospective chronological holdout, not a prospective live trial. No test-period parameter optimization was performed. OpenAI Codex assisted with code, testing, analysis and drafting. The submitter should understand and review this work.','SmallCustom')
    page()
    h('01 / Data and exploration')
    p('Yahoo Finance daily data are saved as original JSON and vendor OHLCV CSVs, alongside corporate actions and checksums. The period ends in December 2025 to use complete years. Infosys and TCS are established Indian IT equities, but this narrow, non-random selection is not a market-wide universe.')
    table(['Series','Raw / clean rows','Duplicates / invalid','Zero volume'],[
        [s,f"{q['raw_rows']} / {q['clean_rows']}",f"{q['duplicates']} / {q['invalid_rows']}",q['zero_volume_rows']]
        for s,q in quality.items()],[100,145,145,100])
    missing=sum(sum(q['missing_by_column'].values()) for q in quality.values())
    dropped=sum(len(q['excluded_noncommon_dates']) for q in quality.values())
    p(f'Missing source cells: {missing}. Non-common session rows excluded: {dropped}. Sort dates; remove duplicates; drop missing or invalid OHLC rows; never forward-fill prices. Use the common observed session dates. An independent exchange calendar was not audited. Index zero-volume rows remain because index volume is not used.')
    img('data_exploration.png',440)
    p('The dashed line marks the test boundary. Volume and return distributions are inspected as context. This full-sample chart is descriptive and is not used to choose parameters.','SmallCustom')
    page()
    h('02 / Exact rules and assumptions')
    table(['Component','Rule'],[
        ['Indicators','EMA20/EMA50 on adjusted close. ATR14 and ADX14 use SMA seeds and Wilder recursion.'],
        ['Entry','While flat: prior-close EMA20 > EMA50 and ADX >= 25. Buy at next open. Basic strategy removes only ADX.'],
        ['Regime rule','Uses the bullish EMA state, not only the one-day crossover pulse. Re-entry after a stop is allowed on a later session.'],
        ['Sizing','Each stock/period starts with INR 100,000. Units = min(1% of cash / (3 x prior ATR), 95% of cash / fee-inclusive entry fill). No leverage or shorts.'],
        ['Stop','Initial stop = entry fill - 3 x prior ATR. At each close raise to max(old stop, highest close since entry - 3 x current ATR), effective next session. Entry fill initializes the peak.'],
        ['Exit priority','Gap below stop: sell at open. Else prior EMA bearish: sell at open. Else low reaches stop: sell at stop. New entries can stop on entry day. No re-entry on exit day. Falling ADX alone does not exit.'],
        ['Costs','15 bps turnover fee plus 5 bps adverse slippage on each side, approximately 40 bps round trip. Flat assumptions, not an audited tax/broker schedule.'],
        ['Split','2017 warm-up; 2018-2022 development; 2023-2025 test. Each period starts flat. Sell at final close with costs; no final-day entry.']],[100,390])
    p('<b>Corporate actions.</b> Adjust all OHLC by vendor AdjClose / Close; retain vendor volume. Fractional adjusted units approximate a dividend-reinvested account. Do not add dividends again. This is not an exact ledger of real historical rupee quotes, integer shares or dividend payment dates.')
    p('<b>Risk.</b> Gaps, fees and slippage can exceed the 1% nominal risk budget. No fill-capacity, circuit-limit or market-impact model. Idle cash earns zero. The basic comparison has the same stops, sizing and costs.','SmallCustom')
    page()
    h('03 / Complete performance metrics')
    specs=[('cumulative_return','Cumulative return','pct'),('annualized_return','Annualized return','pct'),
           ('sharpe','Sharpe','number'),('sortino','Sortino','number'),('max_drawdown','Maximum drawdown','pct'),
           ('win_rate','Win rate','pct'),('trades','Completed trades','int'),('profit_factor','Profit factor','number'),
           ('average_profit','Average profit (INR)','money'),('average_loss','Average loss (INR)','money'),
           ('maximum_profit','Maximum profit (INR)','money'),('maximum_loss','Maximum loss (INR)','money')]
    for stock in ['INFY','TCS']:
        p(f'<b>{stock}: independent INR 100,000 accounts; net of modelled costs</b>')
        columns=[get(stock,period,label) for period,label in [('Development','EMA + ADX'),('Development','EMA only'),('Test','EMA + ADX'),('Test','EMA only')]]
        table(['Metric','Dev: ADX','Dev: basic','Test: ADX','Test: basic'],
              [[label]+[fmt(x[key],kind) for x in columns] for key,label,kind in specs],[150,85,85,85,85])
    p('Dev = 2018-2022; Test = 2023-2025. Trade profits and losses include entry/exit fees and slippage. N/A denotes an absent group or undefined denominator.','SmallCustom')
    page()
    h('04 / Benchmarks and development results')
    p('Same-stock adjusted buy-and-hold isolates timing versus owning the equity and pays identical entry/exit costs. It invests all capital, so exposure exceeds the risk-sized strategy. Nifty 50 is a gross price-index reference: no fees or dividends. Both begin at the first session open and finish at the final close.')
    table(['Stock / period','ADX return','Buy & hold','Nifty price'],[
        [f'{s} / {per}',fmt(get(s,per,'EMA + ADX').cumulative_return,'pct'),
         fmt(get(s,per,'Buy & hold').cumulative_return,'pct'),fmt(get(s,per,'Nifty 50 price').cumulative_return,'pct')]
        for s in ['INFY','TCS'] for per in ['Development','Test']],[175,105,105,105])
    img('INFY_Development_performance.png')
    p('EMA20/50, ADX14 >= 25 and 3 ATR are interpretable starting choices fixed before evaluation, not winners selected from the grid. Development sensitivity does not change the frozen specification.','SmallCustom')
    page()
    h('05 / Test equity and drawdown')
    img('INFY_Test_performance.png')
    p('Drawdown is decline from running equity high, including starting capital. Daily equity marks positions to close; final equity includes liquidation costs.')
    t=get('TCS','Test','EMA + ADX'); tb=get('TCS','Test','EMA only'); th=get('TCS','Test','Buy & hold')
    p(f'<b>Cross-stock check.</b> TCS returned {fmt(t.cumulative_return,"pct")} filtered, {fmt(tb.cumulative_return,"pct")} basic, and {fmt(th.cumulative_return,"pct")} buy-and-hold. '
      f'Filtered drawdown was {fmt(t.max_drawdown,"pct")}. Two IT stocks are not independent evidence across the Indian market.')
    years=pd.read_csv(OUT/'test_yearly_returns.csv')
    table(['Stock / year','ADX','Basic','Buy & hold','Nifty price'],[
        [f'{stock} / {year}']+[fmt(years[(years.stock==stock)&(years.year==year)&(years.strategy==label)].return_value.iloc[0],'pct')
        for label in ['EMA + ADX','EMA only','Buy & hold','Nifty 50 price']]
        for stock in ['INFY','TCS'] for year in [2023,2024,2025]],[130,90,90,90,90])
    p('Yearly results compound segments of the continuing test account; they are not restarted annual backtests.','SmallCustom')
    page()
    h('06 / Entries, exits and whipsaws')
    img('INFY_test_trades.png')
    table(['Test diagnostics','INFY ADX','INFY basic','TCS ADX','TCS basic'],[
        [label]+[fmt(diag[(diag.stock==s)&(diag.period=='Test')&(diag.strategy==st)].iloc[0][key],kind)
        for s,st in [('INFY','EMA + ADX'),('INFY','EMA only'),('TCS','EMA + ADX'),('TCS','EMA only')]]
        for key,label,kind in [('exposure','Sessions with exposure','pct'),('avg_holding_sessions','Mean holding sessions','number'),
            ('avg_entry_lag','Mean entry lag (sessions)','number'),('max_consecutive_losses','Longest loss streak','int'),
            ('top3_share_gross_profit','Top 3 / gross winning P&L','pct'),('mean_close_peak_giveback','Mean peak-close giveback','pct')]], [170,80,80,80,80])
    p('Entry lag counts sessions since the current bullish EMA regime began, including delayed re-entries. It is not lag from a true turning point. Giveback = max(0, 1 - exit fill / highest close on holding dates), a descriptive proxy that may include the exit-day close after an open exit. Top-three concentration uses gross winning P&amp;L.','SmallCustom')
    p('Loss streaks quantify repeated failed entries. ADX can delay entries and cannot prevent sudden reversals. High concentration of profit in a few trades limits confidence despite a long daily dataset.')
    page()
    h('07 / Sensitivity and market conditions')
    p('Development-only checks: EMA 15/40, 20/50, 25/60 crossed with ADX 20, 25, 30. Cells are net 2018-2022 cumulative returns. This grid is not used to select a test-period winner.')
    table(['Stock / EMA','ADX 20','ADX 25','ADX 30'],[
        [f'{s} / {f}-{sl}']+[fmt(sensitivity[(sensitivity.stock==s)&(sensitivity.fast==f)&(sensitivity.slow==sl)&(sensitivity.adx==ad)].cumulative_return.iloc[0],'pct') for ad in [20,25,30]]
        for s in ['INFY','TCS'] for f,sl in [(15,40),(20,50),(25,60)]],[190,100,100,100])
    p('Variation across nearby settings measures specification sensitivity. Stop distances and risk budgets were not searched.')
    table(['Test costs per side','INFY return','TCS return'],[
        [label]+[fmt(costs[(costs.stock==s)&(costs.fee_bps==fee)].cumulative_return.iloc[0],'pct') for s in ['INFY','TCS']]
        for fee,label in [(0,'No fees / no slippage'),(15,'15 bp fees + 5 bp slip'),(30,'30 bp fees + 10 bp slip')]],[250,120,120])
    p('Cost stress diagnoses the frozen test strategy, not model selection; costs also alter subsequent cash and position sizes.')
    reg=pd.read_csv(OUT/'test_regime_attribution.csv')
    table(['Stock / prior-close regime','Sessions','Net P&L (INR)'],[
        [f'{r.stock} / {r.regime}',r.sessions,fmt(r.pnl_inr,'money')] for r in reg.itertuples()],[280,80,130])
    p('Prior ADX below 25 = weak/sideways; otherwise EMA direction defines strong up/down. Additive daily equity changes sum to test profit. These are indicator-defined labels, not independently verified market states.','SmallCustom')
    page()
    h('08 / Definitions and limitations')
    p('<b>Returns.</b> Daily simple returns; first return = first close equity / initial capital - 1. Annualized return = (ending / initial capital)^(252 / sessions) - 1. Sharpe = sqrt(252) x daily mean / sample standard deviation. Risk-free rate = 0%. Sortino denominator = sqrt(mean(min(return,0)^2)) across all sessions, with zero target return. Cash earns zero.')
    p('<b>Trades.</b> Win rate = positive-net-P&amp;L trades / completed trades. Profit factor = positive P&amp;L sum / absolute negative P&amp;L sum. Average and maximum profit/loss use winners/losers separately. Drawdown is negative. Zero volatility, absent downside, no losing trades or an absent trade group yield N/A where undefined. Final liquidation counts as a trade.')
    p('<b>What this establishes.</b> Reproducible historical behavior with delayed execution, explicit costs and a chronological holdout. It does not establish future profitability or statistically significant alpha.')
    p('<b>Material limitations.</b> Retrospective selection of surviving large caps introduces selection/survivorship bias; both stocks share a sector. Vendor adjustments are not point-in-time corporate-action records. Fractional adjusted units approximate total returns and omit dividend timing, settlement, integer shares and tax lots. Data can be revised. Flat costs simplify Indian delivery charges. Stops may fail at circuit limits or poor liquidity. Daily bars cannot reconstruct order books. No volume-based capacity model is used. A small trade sample and one holdout weaken statistical conclusions.')
    p('<b>Interpretation.</b> Read returns alongside drawdown, exposure and profit concentration. Filters may eliminate large winners as well as losses. Cash-heavy strategies cannot be credited with superior stock selection simply because drawdown is below fully invested buy-and-hold. Basic EMA and same-stock passive controls are essential.')
    p('<b>Improvements.</b> Forward paper trading; a point-in-time multi-sector universe; exchange-calendar and corporate-action audits; explicit Indian delivery costs and integer shares; capacity constraints; rolling walk-forward windows and block-bootstrap uncertainty. Treat these as new studies rather than repeatedly tuning this holdout.')
    p('<b>Verification.</b> Deterministic tests cover indicator causality, Wilder seeds, next-open signals, gap stops, entry-day stops, trailing-stop timing, trade P&amp;L reconciliation, first-day returns and undefined metrics. Each real backtest asserts nonnegative cash and reconciles P&amp;L to equity.')
    page()
    h('09 / Reproduction and resources')
    p('<b>Reproduce.</b> Open the folder in VS Code. Install requirements.txt into a virtual environment. Run python -m unittest discover -s tests -v and python run_project.py. Default runs use the saved snapshot and rebuild CSVs, charts and this PDF. Use --download only for an intentional refresh; revisions can change results. README.md has exact commands; WALKTHROUGH.md explains the code.')
    p('<b>Audit trail.</b> data/manifest.json records source URLs, timestamps, checksums and corporate actions. results/data_quality.json documents cleaning. configuration.json records parameters and versions. Account CSVs include cash, units, equity and stops. Trade logs include signal, entry and exit dates, prices, fees, P&amp;L and reasons.')
    manifest=json.loads((ROOT/'data/manifest.json').read_text(encoding='utf-8'))
    p('Snapshot retrieval (UTC): '+escape(manifest['retrieved_utc']),'SmallCustom')
    refs=[('Assignment','CFA_InductionTask2026 (1).pdf supplied by the user; Track 2 and general deliverables, supplied PDF pages 1-4.'),
        ('Infosys data','https://finance.yahoo.com/quote/INFY.NS/history/'),
        ('TCS data','https://finance.yahoo.com/quote/TCS.NS/history/'),
        ('Nifty data','https://finance.yahoo.com/quote/%5ENSEI/history/'),
        ('Download route','Yahoo Finance v8 chart API. Exact URLs and raw responses are retained in data/.'),
        ('ADX and smoothing','https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/average-directional-index-adx'),
        ('Libraries','https://pandas.pydata.org/docs/ ; https://numpy.org/doc/ ; https://matplotlib.org/stable/ ; https://docs.reportlab.com/'),
        ('Assistance','OpenAI Codex assisted in implementation, validation, analysis and report drafting. No external strategy repository or tutorial code was copied.')]
    for title,text in refs: p('<b>'+escape(title)+'.</b> '+escape(text),'SmallCustom')
    p('The ADX reference explains strength, threshold and smoothing. EMA20/50, 3 ATR, 1% risk and costs are design assumptions, not claims of optimality. Sources consulted on 27 October 2026.','SmallCustom')
    def footer(canvas,doc):
        canvas.setStrokeColor(colors.HexColor('#d7e2e9')); canvas.line(42,40,553,40)
        canvas.setFont('Helvetica',8); canvas.setFillColor(colors.HexColor('#667486'))
        canvas.drawString(42,27,'CFA | Trend-following research | Daily Indian equities')
        canvas.drawRightString(553,27,str(doc.page))
    doc=SimpleDocTemplate(str(OUT/'Technical_Report.pdf'),pagesize=(595.28,841.89),
        rightMargin=47,leftMargin=47,topMargin=38,bottomMargin=54,
        title='Trend Following in Indian Equities',author='CFA Intermediate Project - AI-assisted')
    doc.build(flow,onFirstPage=footer,onLaterPages=footer)
