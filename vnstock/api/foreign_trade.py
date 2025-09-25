"""
vnstock/api/foreign_trade.py

Unified ForeignTrade adapter for daily foreign buy/sell data.
"""

from typing import Any
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential
from vnstock.config import Config
from vnstock.base import BaseAdapter, dynamic_method


class ForeignTrade(BaseAdapter):
    _module_name = "foreign_trade"
    """
    Adapter for daily foreign trading data (buy/sell volume & value).

    Usage:
        ft = ForeignTrade(source="vci")
        df = ft.daily(symbol="PDR", start="2025-01-01", end="2025-09-25")
    """

    def __init__(
        self,
        source: str = "vci",
        symbol: str | None = None,
        random_agent: bool = False,
        show_log: bool = False
    ):
        self.source = source
        self.symbol = symbol if symbol else ""
        self.random_agent = random_agent
        self.show_log = show_log

        if source.lower() not in ["vci", "tcbs"]:
            raise ValueError("Lớp ForeignTrade chỉ nhận giá trị tham số source là 'VCI' hoặc 'TCBS'.")

        super().__init__(
            source=source,
            symbol=symbol,
            random_agent=random_agent,
            show_log=show_log
        )

    @dynamic_method
    def daily(self, *args: Any, **kwargs: Any) -> pd.DataFrame:
        """
        Retrieve daily foreign trading data for a symbol in [start, end].
        Expected columns: ['date','buy_vol','sell_vol','buy_val','sell_val','net_vol','net_val']
        """
        # Implemented by provider modules; here for signature and retries
        raise NotImplementedError


