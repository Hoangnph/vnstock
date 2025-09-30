"""
StockAI Data Functions Package

Thư viện các hàm tiện ích để lấy và xử lý dữ liệu chứng khoán Việt Nam.

Main functions:
- fetch_stock_data: Lấy dữ liệu chứng khoán tổng quát
- StockDataFetcher: Class lấy dữ liệu với nhiều tùy chọn
- normalize_foreign_data: Chuẩn hóa dữ liệu foreign trading

Author: StockAI Team
Version: 1.0.0
"""

from .stock_data_fetcher import fetch_stock_data, StockDataFetcher
from .normalize_foreign_data import normalize_foreign_data
from .vn100_fetcher import (
    get_vn100_symbols, 
    get_vn100_dataframe, 
    save_vn100_csv, 
    get_vn100_by_sector, 
    get_vn100_top_n,
    VN100Fetcher
)

__version__ = "1.0.0"
__author__ = "StockAI Team"
__all__ = [
    "fetch_stock_data",
    "StockDataFetcher", 
    "normalize_foreign_data",
    "get_vn100_symbols",
    "get_vn100_dataframe",
    "save_vn100_csv",
    "get_vn100_by_sector",
    "get_vn100_top_n",
    "VN100Fetcher"
]
