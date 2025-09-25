"""
VCI provider implementation for ForeignTrade.

Uses IQ Insight public endpoints observed from the VCI site:
- price-history (ONE_DAY) with pagination
- price-history-summary (optional for totals)
"""

from typing import Optional, List, Dict
import datetime as dt
import pandas as pd

from vnstock.core.utils.client import send_request
from vnstock.core.utils.user_agent import get_headers


def _to_yyyymmdd(date_str: str) -> str:
    # Accept 'YYYY-MM-DD' and return 'YYYYMMDD'
    try:
        return dt.datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y%m%d")
    except Exception:
        return date_str.replace("-", "")


class ForeignTrade:
    BASE = "https://iq.vietcap.com.vn/api/iq-insight-service/v1/company/{ticker}"

    def __init__(self, symbol: Optional[str] = None, random_agent: bool = False, show_log: bool = False):
        self.symbol = symbol
        self.random_agent = random_agent
        self.show_log = show_log
        self.headers = get_headers(data_source='VCI', random_agent=random_agent)

    def _fetch_page(self, ticker: str, from_date: str, to_date: str, page: int, size: int = 50) -> List[Dict]:
        url = f"{self.BASE.format(ticker=ticker)}/price-history"
        params = {
            "timeFrame": "ONE_DAY",
            "fromDate": from_date,
            "toDate": to_date,
            "page": page,
            "size": size,
        }
        resp = send_request(url=url, headers=self.headers, method="GET", params=params, show_log=self.show_log)
        data = (resp or {}).get("data", {})
        return data.get("content", [])

    def daily(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        if not symbol:
            raise ValueError("symbol is required")
        ticker = symbol.upper()
        from_date = _to_yyyymmdd(start)
        to_date = _to_yyyymmdd(end)

        # paginate until empty
        page = 0
        rows: List[Dict] = []
        while True:
            content = self._fetch_page(ticker, from_date, to_date, page=page, size=50)
            if not content:
                break
            rows.extend(content)
            # stop if returned less than page size
            if len(content) < 50:
                break
            page += 1

        if not rows:
            return pd.DataFrame(columns=[
                "date", "buy_vol", "sell_vol", "buy_val", "sell_val", "net_vol", "net_val"
            ])

        # Map fields defensively (names may vary). Prefer *Matched fields if present
        def map_row(r: Dict) -> Dict:
            # date
            trading_date = r.get("tradingDate") or r.get("date")
            # values
            buy_vol = (
                r.get("foreignBuyVolumeMatched")
                or r.get("foreignBuyVolume")
                or r.get("totalMatchForeignBuyVolume")
            )
            sell_vol = (
                r.get("foreignSellVolumeMatched")
                or r.get("foreignSellVolume")
                or r.get("totalMatchForeignSellVolume")
            )
            buy_val = (
                r.get("foreignBuyValueMatched")
                or r.get("foreignBuyValue")
                or r.get("totalMatchForeignBuyValue")
            )
            sell_val = (
                r.get("foreignSellValueMatched")
                or r.get("foreignSellValue")
                or r.get("totalMatchForeignSellValue")
            )
            net_vol = (
                r.get("foreignNetVolumeMatched")
                or r.get("foreignNetVolume")
                or (None if (buy_vol is None or sell_vol is None) else (buy_vol - sell_vol))
            )
            net_val = (
                r.get("foreignNetValueMatched")
                or r.get("foreignNetValue")
                or (None if (buy_val is None or sell_val is None) else (buy_val - sell_val))
            )
            return {
                "date": trading_date,
                "buy_vol": buy_vol,
                "sell_vol": sell_vol,
                "buy_val": buy_val,
                "sell_val": sell_val,
                "net_vol": net_vol,
                "net_val": net_val,
            }

        mapped = [map_row(r) for r in rows]
        df = pd.DataFrame(mapped)
        # Normalize date
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"]).dt.date.astype("datetime64[ns]")
            df = df.sort_values("date").reset_index(drop=True)
        return df



