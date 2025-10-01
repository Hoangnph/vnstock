#!/usr/bin/env python3
"""
VN100 Analysis Pipeline

Pipeline tích hợp cập nhật dữ liệu VN100 và tính toán chỉ số phân tích tự động.
Pipeline này sẽ:
1. Cập nhật dữ liệu VN100 từ SSI API
2. Tự động tính toán các chỉ số phân tích cho các mã đã cập nhật
3. Lưu kết quả phân tích vào database
4. Hỗ trợ cập nhật incremental và batch processing

Usage:
  python fastapi/pipeline/vn100_analysis_pipeline.py --batch 3 --analysis-days 30
"""

from __future__ import annotations

import argparse
import asyncio
import time
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Set

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi.func.vn100_database_loader import VN100DatabaseLoader
from fastapi.func.ssi_fetcher_with_tracking import SSIFetcherWithTracking
from database.api.database import get_database_manager, get_async_session
from database.api.repositories import RepositoryFactory
from database.schema.models import DataSource
from analytis.analysis_engine_db import DatabaseIntegratedAnalysisEngine
from analytis.config import AnalysisConfig


class VN100AnalysisPipeline:
    """Pipeline tích hợp cập nhật dữ liệu và phân tích VN100"""
    
    def __init__(self, batch_size: int = 3, analysis_days: int = 30):
        """
        Khởi tạo pipeline
        
        Args:
            batch_size: Kích thước batch cho cập nhật dữ liệu
            analysis_days: Số ngày phân tích cho các mã đã cập nhật
        """
        self.batch_size = batch_size
        self.analysis_days = analysis_days
        self.data_fetcher = SSIFetcherWithTracking()
        self.analysis_engine = DatabaseIntegratedAnalysisEngine()
        self.updated_symbols: Set[str] = set()
        self.analyzed_symbols: Set[str] = set()
        
    async def run_pipeline(self, target_end_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Chạy pipeline hoàn chỉnh
        
        Args:
            target_end_date: Ngày kết thúc cập nhật (None = hôm nay)
            
        Returns:
            Dict với kết quả pipeline
        """
        start_time = time.time()
        
        if target_end_date is None:
            target_end_date = date.today()
        
        print(f"🚀 Bắt đầu VN100 Analysis Pipeline")
        print(f"📊 Target end date: {target_end_date}")
        print(f"📦 Batch size: {self.batch_size}")
        print(f"📈 Analysis days: {self.analysis_days}")
        
        # Bước 1: Cập nhật dữ liệu VN100
        print(f"\n{'='*60}")
        print(f"BƯỚC 1: CẬP NHẬT DỮ LIỆU VN100")
        print(f"{'='*60}")
        
        data_update_result = await self._update_vn100_data(target_end_date)
        
        # Bước 2: Tính toán chỉ số phân tích
        print(f"\n{'='*60}")
        print(f"BƯỚC 2: TÍNH TOÁN CHỈ SỐ PHÂN TÍCH")
        print(f"{'='*60}")
        
        analysis_result = await self._run_analysis_for_updated_symbols()
        
        # Tổng kết
        end_time = time.time()
        duration = end_time - start_time
        
        summary = {
            'pipeline_duration_seconds': duration,
            'target_end_date': target_end_date.isoformat(),
            'data_update': data_update_result,
            'analysis': analysis_result,
            'total_updated_symbols': len(self.updated_symbols),
            'total_analyzed_symbols': len(self.analyzed_symbols),
            'success_rate': {
                'data_update': (data_update_result['success_count'] / data_update_result['total_symbols']) * 100 if data_update_result['total_symbols'] > 0 else 0,
                'analysis': (analysis_result['success_count'] / analysis_result['total_symbols']) * 100 if analysis_result['total_symbols'] > 0 else 0
            }
        }
        
        print(f"\n{'='*60}")
        print(f"TỔNG KẾT PIPELINE")
        print(f"{'='*60}")
        print(f"⏱️ Thời gian: {duration:.2f} giây")
        print(f"📊 Cập nhật dữ liệu: {data_update_result['success_count']}/{data_update_result['total_symbols']} mã")
        print(f"📈 Phân tích: {analysis_result['success_count']}/{analysis_result['total_symbols']} mã")
        print(f"📋 Tổng bản ghi cập nhật: {data_update_result['total_records']:,}")
        print(f"🎯 Tổng tín hiệu phân tích: {analysis_result['total_signals']:,}")
        
        if data_update_result['failed_symbols']:
            print(f"❌ Mã cập nhật thất bại: {', '.join(data_update_result['failed_symbols'])}")
        
        if analysis_result['failed_symbols']:
            print(f"❌ Mã phân tích thất bại: {', '.join(analysis_result['failed_symbols'])}")
        
        return summary
    
    async def _update_vn100_data(self, target_end_date: date) -> Dict[str, Any]:
        """Cập nhật dữ liệu VN100"""
        get_database_manager().initialize()
        loader = VN100DatabaseLoader()
        symbols = await loader.get_active_vn100_symbols()
        
        if not symbols:
            # Fallback từ CSV
            import pandas as pd
            df = pd.read_csv('assets/data/vn100_official_ssi.csv')
            symbols = df['symbol'].astype(str).str.upper().tolist()
        
        print(f"📊 Cập nhật {len(symbols)} mã VN100")
        
        async with get_async_session() as session:
            results: List[Dict[str, Any]] = []
            total_batches = (len(symbols) + self.batch_size - 1) // self.batch_size
            
            for i in range(0, len(symbols), self.batch_size):
                batch_num = i // self.batch_size + 1
                chunk = symbols[i:i+self.batch_size]
                
                print(f"🔄 Batch {batch_num}/{total_batches}: {chunk}")
                
                batch_results = []
                for j, symbol in enumerate(chunk):
                    try:
                        result = await self._update_symbol_data(session, symbol, target_end_date)
                        batch_results.append(result)
                        
                        if result.get("success"):
                            records = result.get('records', 0)
                            if records > 0:
                                self.updated_symbols.add(symbol)
                                last_date = result.get('last_updated_date', 'N/A')
                                duration = result.get('duration_seconds', 0)
                                print(f"  ✅ {symbol}: {records} records to {last_date} ({duration}s)")
                            else:
                                print(f"  ⏭️ {symbol}: No new data")
                        else:
                            error = result.get('error', 'unknown error')
                            print(f"  ❌ {symbol}: {error}")
                        
                        # Delay giữa các mã
                        if j < len(chunk) - 1:
                            await asyncio.sleep(2.0)
                            
                    except Exception as e:
                        print(f"  ❌ {symbol}: Exception - {e}")
                        batch_results.append({"symbol": symbol, "success": False, "error": str(e)})
                
                results.extend(batch_results)
                
                # Delay giữa các batch
                if i + self.batch_size < len(symbols):
                    print(f"⏳ Chờ 5 giây trước batch tiếp theo...")
                    await asyncio.sleep(5.0)
            
            # Tổng kết cập nhật dữ liệu
            success_count = sum(1 for r in results if r.get("success"))
            failed_symbols = [r["symbol"] for r in results if not r.get("success")]
            total_records = sum(r.get('records', 0) for r in results if r.get("success"))
            
            return {
                "total_symbols": len(symbols),
                "success_count": success_count,
                "failed_count": len(failed_symbols),
                "failed_symbols": failed_symbols,
                "total_records": total_records,
                "target_end_date": target_end_date.isoformat()
            }
    
    async def _update_symbol_data(self, session, symbol: str, target_end_date: date) -> Dict[str, Any]:
        """Cập nhật dữ liệu một mã"""
        start_time = time.time()
        
        try:
            # Fetch dữ liệu với tracking
            success, df, last_updated_date = await self.data_fetcher.fetch_daily_with_tracking(symbol, target_end_date)
            
            if not success:
                await self.data_fetcher.update_tracking_error(symbol, "Failed to fetch data")
                return {"symbol": symbol, "success": False, "error": "fetch_failed"}
            
            if df is None or df.empty:
                # Không có dữ liệu mới
                await self.data_fetcher.update_tracking_success(symbol, target_end_date, 0, int(time.time() - start_time))
                return {"symbol": symbol, "success": True, "records": 0, "message": "no_new_data"}
            
            # Đảm bảo stock tồn tại
            stock_repo = RepositoryFactory.create_stock_repository(session)
            existing = await stock_repo.get_by_symbol(symbol)
            if not existing:
                await stock_repo.create({
                    "symbol": symbol.upper(),
                    "name": f"Stock {symbol.upper()}",
                    "exchange": "HOSE",
                    "sector": "Other",
                    "industry": "Other",
                    "market_cap_tier": "Tier 3",
                    "is_active": True,
                })
                existing = await stock_repo.get_by_symbol(symbol)
            
            # Chuẩn bị dữ liệu cho upsert
            price_repo = RepositoryFactory.create_stock_price_repository(session)
            foreign_repo = RepositoryFactory.create_foreign_trade_repository(session)
            
            prices: List[Dict[str, Any]] = []
            trades: List[Dict[str, Any]] = []
            
            for _, row in df.iterrows():
                close_price = float(row.get("close", 0.0))
                volume = int(row.get("volume", 0))
                
                prices.append({
                    "stock_id": existing.id,
                    "symbol": symbol.upper(),
                    "time": row["time"],
                    "open": float(row.get("open", 0)),
                    "high": float(row.get("high", 0)),
                    "low": float(row.get("low", 0)),
                    "close": close_price,
                    "volume": volume,
                    "value": close_price * volume,
                    "source": DataSource.SSI,
                })
                
                fb = int(row.get("foreign_buy_shares", 0))
                fs = int(row.get("foreign_sell_shares", 0))
                
                if fb > 0 or fs > 0:
                    trades.append({
                        "stock_id": existing.id,
                        "symbol": symbol.upper(),
                        "time": row["time"],
                        "buy_volume": fb,
                        "sell_volume": fs,
                        "net_volume": fb - fs,
                        "buy_value": close_price * fb,
                        "sell_value": close_price * fs,
                        "net_value": close_price * (fb - fs),
                        "source": DataSource.SSI,
                    })
            
            # Upsert dữ liệu
            if prices:
                await price_repo.create_batch(prices)
            if trades:
                await foreign_repo.create_batch(trades)
            
            # Cập nhật tracking
            duration_seconds = int(time.time() - start_time)
            await self.data_fetcher.update_tracking_success(symbol, last_updated_date, len(df), duration_seconds)
            
            return {
                "symbol": symbol, 
                "success": True, 
                "records": len(df),
                "last_updated_date": last_updated_date.isoformat(),
                "duration_seconds": duration_seconds
            }
            
        except Exception as e:
            error_msg = str(e)
            await self.data_fetcher.update_tracking_error(symbol, error_msg)
            return {"symbol": symbol, "success": False, "error": error_msg}
    
    async def _run_analysis_for_updated_symbols(self) -> Dict[str, Any]:
        """Chạy phân tích cho các mã đã cập nhật"""
        if not self.updated_symbols:
            print("⏭️ Không có mã nào được cập nhật, bỏ qua phân tích")
            return {
                "total_symbols": 0,
                "success_count": 0,
                "failed_count": 0,
                "failed_symbols": [],
                "total_signals": 0
            }
        
        print(f"📈 Phân tích {len(self.updated_symbols)} mã đã cập nhật")
        
        # Tính toán thời gian phân tích
        end_date = date.today()
        start_date = end_date - timedelta(days=self.analysis_days)
        
        print(f"📅 Thời gian phân tích: {start_date} đến {end_date}")
        
        results: List[Dict[str, Any]] = []
        total_signals = 0
        
        for symbol in self.updated_symbols:
            try:
                print(f"🔍 Phân tích {symbol}...")
                
                # Chạy phân tích
                result = await self.analysis_engine.analyze_symbol(
                    symbol=symbol,
                    start_date=start_date.isoformat(),
                    end_date=end_date.isoformat()
                )
                
                signals_count = len(result.signals)
                total_signals += signals_count
                self.analyzed_symbols.add(symbol)
                
                results.append({
                    "symbol": symbol,
                    "success": True,
                    "signals_count": signals_count,
                    "analysis_result_id": result.analysis_result_id
                })
                
                print(f"  ✅ {symbol}: {signals_count} tín hiệu")
                
                # Delay nhỏ giữa các phân tích
                await asyncio.sleep(1.0)
                
            except Exception as e:
                print(f"  ❌ {symbol}: {e}")
                results.append({
                    "symbol": symbol,
                    "success": False,
                    "error": str(e)
                })
        
        # Tổng kết phân tích
        success_count = sum(1 for r in results if r.get("success"))
        failed_symbols = [r["symbol"] for r in results if not r.get("success")]
        
        return {
            "total_symbols": len(self.updated_symbols),
            "success_count": success_count,
            "failed_count": len(failed_symbols),
            "failed_symbols": failed_symbols,
            "total_signals": total_signals,
            "analysis_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": self.analysis_days
            }
        }


async def main(batch_size: int = 3, analysis_days: int = 30) -> None:
    """Hàm chính"""
    pipeline = VN100AnalysisPipeline(batch_size=batch_size, analysis_days=analysis_days)
    
    try:
        result = await pipeline.run_pipeline()
        
        # Lưu kết quả
        import json
        from datetime import datetime
        
        output_file = f"output/pipeline_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n💾 Kết quả đã được lưu vào: {output_file}")
        
    except Exception as e:
        print(f"❌ Pipeline thất bại: {e}")
        import traceback
        traceback.print_exc()
        raise


def cli_main() -> int:
    """CLI entry point"""
    parser = argparse.ArgumentParser(description="VN100 Analysis Pipeline")
    parser.add_argument("--batch", dest="batch", type=int, default=3, 
                       help="Batch size for data update (default: 3)")
    parser.add_argument("--analysis-days", dest="analysis_days", type=int, default=30,
                       help="Number of days for analysis (default: 30)")
    
    args = parser.parse_args()
    
    asyncio.run(main(args.batch, args.analysis_days))
    return 0


if __name__ == "__main__":
    raise SystemExit(cli_main())
