## Vnstock API Reference (VCI, TCBS, MSN)

This document summarizes all public APIs exposed via the unified imports and provider implementations, with parameters and usage examples. Prefer the unified interface (`from vnstock import ...`) unless you need provider-specific behaviors.

### Importing

```python
from vnstock import Vnstock, Listing, Quote, Company, Finance, Trading, Screener
# Advanced (fixed provider)
# from vnstock.explorer.vci import Listing, Quote, Company, Finance, Trading
# from vnstock.explorer.tcbs import Quote, Company, Finance, Trading, Screener
```

### Unified Orchestration

```python
from vnstock import Vnstock
stock = Vnstock().stock(symbol='ACB', source='VCI')
df = stock.quote.history(start='2024-01-01', end='2025-03-19', interval='1D')
info = stock.company.overview()
bs = stock.finance.balance_sheet(period='year', lang='vi', dropna=True)
```

---

## Listing (sources: VCI, MSN)

Unified class: `Listing(source='vci'|'msn')`

- VCI
  - all_symbols(show_log=False, to_df=True)
  - symbols_by_exchange(lang='vi'|'en', show_log=False, to_df=True)
  - symbols_by_industries(lang='vi'|'en', show_log=False, to_df=True)
  - industries_icb(show_log=False, to_df=True)
  - symbols_by_group(group, show_log=False, to_df=True)
  - Shortcuts: all_future_indices(), all_government_bonds(), all_covered_warrant(), all_bonds()

- MSN
  - search_symbol_id(query, locale=None, limit=10, show_log=False, to_df=True)

Examples

```python
from vnstock import Listing
Listing(source='vci').all_symbols()
Listing(source='vci').symbols_by_group('VN30')

from vnstock.explorer.msn import Listing as MSNListing
MSNListing().search_symbol_id('USDEUR', locale='en-us', limit=10)
```

Notes
- When using `Vnstock().stock(..., source='TCBS')`, listing data is auto-fallback to VCI because TCBS does not provide listing.

---

## Quote (sources: VCI, TCBS, MSN)

Unified class: `Quote(symbol, source='vci'|'tcbs'|'msn')`

Common methods
- history(...): historical OHLC
- intraday(...): tick-level trades (VCI, TCBS)
- price_depth(...): orderbook depth (VCI)

Parameter reference by provider

- VCI
  - history(start, end=None, interval='1D', to_df=True, show_log=False, count_back=None, floating=2)
  - intraday(page_size=100, last_time=None, to_df=True, show_log=False)
  - price_depth(to_df=True, show_log=False)

- TCBS
  - history(start, end=None, interval='1D', to_df=True, show_log=False, count_back=365, asset_type=None, _skip_long_check=False)
  - intraday(page_size=100, page=0, to_df=True, show_log=False)

- MSN
  - history(start, end, interval in {'1D','1W','1M'}, to_df=True, show_log=False, count_back=365)

Examples

```python
# VCI
from vnstock import Quote
Quote(symbol='ACB', source='vci').history(start='2024-01-01', end='2025-03-19', interval='1D')
Quote(symbol='ACB', source='vci').intraday(page_size=10_000)
Quote(symbol='ACB', source='vci').price_depth()

# VCI - other asset types
Quote(symbol='VN30F1M', source='vci').history(start='2024-01-02', end='2025-03-19', interval='1D')  # derivatives
Quote(symbol='VNINDEX', source='vci').history(start='2024-01-02', end='2025-03-19', interval='1D')  # index
Quote(symbol='CFPT2314', source='vci').history(start='2024-01-02', end='2025-03-19', interval='1D')  # CW
Quote(symbol='CII424002', source='vci').history(start='2024-01-02', end='2025-03-19', interval='1D')  # listed bond

# TCBS
Quote(symbol='VNINDEX', source='tcbs').history(start='2024-01-02', end='2024-11-01', interval='1D')

# MSN (via unified)
from vnstock import Vnstock
fx = Vnstock().fx(symbol='JPYVND', source='MSN')
fx.quote.history(start='2025-01-02', end='2025-03-20', interval='1D')
```

Notes
- VCI supports multiple asset types (stock, index, derivatives, covered warrants, listed bonds) using the same method signature.
- TCBS history auto-chunks long ranges (>365 days) per year.
- MSN requires `symbol_id` if called directly by provider; unified helpers map known symbols.

---

## Company (sources: VCI, TCBS)

Unified class: `Company(symbol, source='vci'|'tcbs')`

- VCI methods
  - overview()
  - shareholders()
  - officers(filter_by='working'|'resigned'|'all')
  - subsidiaries(filter_by='all'|'subsidiary')
  - affiliate()
  - news()
  - events()
  - reports()
  - ratio_summary()
  - trading_stats()

- TCBS methods (as shown in docs)
  - overview(), profile(), shareholders(), officers(), subsidiaries(), events(), news(), dividends(), insider_deals()

Examples

```python
from vnstock import Company
Company(symbol='ACB', source='vci').officers(filter_by='all')

from vnstock import Vnstock
Vnstock().stock(symbol='VCB', source='TCBS').company.dividends()

# TCBS notebook examples
tcbs_company = Vnstock().stock(symbol='VCB', source='TCBS').company
tcbs_company.overview()
tcbs_company.profile()
tcbs_company.shareholders()
tcbs_company.insider_deals()
tcbs_company.subsidiaries()
tcbs_company.officers()
tcbs_company.events()
tcbs_company.news()
```

Notes
- `affiliate()` is VCI-specific; TCBS has `dividends()` and `insider_deals()` in notebooks.

---

## Finance (sources: VCI, TCBS)

Unified class: `Finance(source='vci'|'tcbs', symbol, period='quarter', get_all=True, show_log=False)`

Methods
- balance_sheet(period={'year','quarter'}, lang={'vi','en'}, dropna=True, show_log=False)
- income_statement(period, lang, dropna, show_log)
- cash_flow(period, lang, dropna, show_log)
- ratio(period, lang, dropna=True, show_log=False, flatten_columns=False, separator='_', drop_levels=None)

Examples

```python
from vnstock import Finance
Finance(source='vci', symbol='VCI').balance_sheet(period='year', lang='vi', dropna=True)
Finance(source='vci', symbol='VCI').ratio(period='quarter', lang='en', flatten_columns=True, drop_levels=[0])

from vnstock import Vnstock
Vnstock().stock(symbol='VCI', source='TCBS').finance.balance_sheet(period='year')
Vnstock().stock(symbol='VCI', source='TCBS').finance.income_statement(period='quarter')
Vnstock().stock(symbol='VCI', source='TCBS').finance.cash_flow(period='year')
Vnstock().stock(symbol='VCI', source='TCBS').finance.ratio(period='quarter')
```

Notes
- TCBS may not support `dropna` (a warning is shown in notebooks).
- VCI provides multi-index ratios with optional flattening.

---

## Trading (sources: VCI, TCBS)

Unified class: `Trading(source='vci'|'tcbs', symbol=None)`

- VCI
  - price_board(symbols_list: list[str], to_df=True, show_log=False, flatten_columns=False, separator='_', drop_levels=None)

- TCBS
  - price_board(symbol_ls: list[str], std_columns=True, to_df=True, show_log=False)

Examples

```python
from vnstock import Trading
Trading(source='vci').price_board(['VCB','ACB','TCB','BID'])
Trading(source='tcbs').price_board(['VCB','ACB'], std_columns=False)

# VCI: display matrix with flattening options
Trading(source='vci').price_board(
    ['VCB','ACB','TCB','BID'],
    flatten_columns=True,
    drop_levels=[0]
).T  # remove .T to see original board orientation
```

---

## Screener (source: TCBS)

Class: `Screener(source='tcbs')`

- stock(params=None, limit=50, id=None, lang='vi')

Example

```python
from vnstock import Screener
Screener(source='tcbs').stock(params={"exchangeName":"HOSE,HNX,UPCOM"}, limit=1700)
```

---

## International Markets via MSN

Using unified helpers that map friendly symbols to MSN `symbol_id`:

```python
from vnstock import Vnstock
fx = Vnstock().fx(symbol='JPYVND', source='MSN')
fx.quote.history(start='2025-01-02', end='2025-03-20', interval='1D')

crypto = Vnstock().crypto(symbol='BTC', source='MSN')
crypto.quote.history(start='2023-01-01', end='2024-12-31', interval='1D')

index = Vnstock().world_index(symbol='DJI', source='MSN')
index.quote.history(start='2023-01-01', end='2024-12-31', interval='1D')
```

If you need direct `symbol_id`:

```python
from vnstock.explorer.msn import Listing
from vnstock.explorer.msn.quote import Quote as MSNQuote

sid = Listing().search_symbol_id('USDEUR', locale='en-us').iloc[0]['symbol_id']
MSNQuote(symbol_id=sid).history(start='2024-01-01', end='2024-12-31', interval='1D')
```

---

## ForeignTrade (sources: VCI, TCBS)

Unified class: `ForeignTrade(source='vci'|'tcbs', symbol=None)`

- daily(symbol, start, end) -> DataFrame
  - Expected columns: `date, buy_vol, sell_vol, buy_val, sell_val, net_vol, net_val`

Status
- In this repository, provider implementations are placeholders and raise clear `NotImplementedError` messages because historical endpoints are not wired yet.
- Once provider endpoints are available, this API will return daily foreign buy/sell metrics.

Example (current behavior)

```python
from vnstock import ForeignTrade
ft = ForeignTrade(source='vci')
try:
    ft.daily(symbol='PDR', start='2025-01-01', end='2025-09-25')
except NotImplementedError as e:
    print(e)
```

## Error Handling & Export Tips
- Market-session constraints: Intraday endpoints (VCI/TCBS) may be unavailable during pre-open preparation windows.
- Parameter support varies by provider. For example, TCBS `finance.ratio` may ignore `dropna` (warning in notebook); prefer provider defaults.
- Date formats: Use `YYYY-MM-DD`. VCI also accepts `YYYY-MM-DD HH:MM:SS` windows for higher precision.
- Large ranges: TCBS automatically chunks long daily history (>365 days). VCI supports `count_back` to limit rows.
- Export: Any DataFrame can be exported via `df.to_csv(...)` or `df.to_excel(...)`.

## Tips & Notes
- Prefer unified classes for stability; you can change `source` without changing call sites.
- Date strings should be `YYYY-MM-DD`; VCI also accepts `YYYY-MM-DD HH:MM:SS` for higher precision windows.
- Intraday endpoints depend on market session; providers may block during pre-open preparation.
- All returns are Pandas DataFrame/Series; use `.to_csv()`/`.to_excel()` to export.


