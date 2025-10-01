#!/usr/bin/env python3
"""
VN100 Indicators Pipeline

Pipeline chỉ tính toán các chỉ số phân tích cho VN100 từ đầu tới giờ.
Pipeline này sẽ:
1. Lấy danh sách VN100
2. Tính toán các chỉ số phân tích cho từng mã
3. Lưu kết quả vào database với deduplication
4. Bỏ qua phần chấm điểm và đánh giá

Usage:
  python fastapi/pipeline/vn100_indicators_pipeline.py --batch 5 --start-date 2010-01-01
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
from database.api.database import get_database_manager, get_async_session
from database.api.repositories import RepositoryFactory
from analytis.engines.indicator_engine import IndicatorEngine
from analytis.config import AnalysisConfig
from analytis.repositories.indicator_repository import IndicatorRepository
from analytis.repositories.config_repository import ConfigRepository


class VN100IndicatorsPipeline:
    """Pipeline chỉ tính toán chỉ số phân tích cho VN100"""
    
    def __init__(self, batch_size: int = 5, start_date: str = "2010-01-01"):
        """
        Khởi tạo pipeline
        
        Args:
            batch_size: Kích thước batch cho xử lý
            start_date: Ngày bắt đầu tính toán
        """
        self.batch_size = batch_size
        self.start_date = start_date
        self.end_date = date.today()
        self.indicator_engine = IndicatorEngine()
        self.processed_symbols: Set[str] = set()
        self.skipped_symbols: Set[str] = set()
        
    async def run_pipeline(self) -> Dict[str, Any]:
        """
        Chạy pipeline tính toán chỉ số
        
        Returns:
            Dict với kết quả pipeline
        """
        start_time = time.time()
        
        print(f"🚀 Bắt đầu VN100 Indicators Pipeline")
        print(f"📊 Thời gian: {self.start_date} đến {self.end_date}")
        print(f"📦 Batch size: {self.batch_size}")
        
        # Bước 1: Lấy danh sách VN100
        print(f"\n{'='*60}")
        print(f"BƯỚC 1: LẤY DANH SÁCH VN100")
        print(f"{'='*60}")
        
        symbols = await self._get_vn100_symbols()
        print(f"📊 Tìm thấy {len(symbols)} mã VN100")
        
        # Bước 2: Tính toán chỉ số phân tích
        print(f"\n{'='*60}")
        print(f"BƯỚC 2: TÍNH TOÁN CHỈ SỐ PHÂN TÍCH")
        print(f"{'='*60}")
        
        result = await self._calculate_indicators_for_symbols(symbols)
        
        # Tổng kết
        end_time = time.time()
        duration = end_time - start_time
        
        summary = {
            'pipeline_duration_seconds': duration,
            'start_date': self.start_date,
            'end_date': self.end_date.isoformat(),
            'total_symbols': len(symbols),
            'processed_symbols': len(self.processed_symbols),
            'skipped_symbols': len(self.skipped_symbols),
            'success_rate': (len(self.processed_symbols) / len(symbols)) * 100 if symbols else 0,
            'result': result
        }
        
        print(f"\n{'='*60}")
        print(f"TỔNG KẾT PIPELINE")
        print(f"{'='*60}")
        print(f"⏱️ Thời gian: {duration:.2f} giây")
        print(f"📊 Tổng mã: {len(symbols)}")
        print(f"✅ Đã xử lý: {len(self.processed_symbols)}")
        print(f"⏭️ Bỏ qua: {len(self.skipped_symbols)}")
        print(f"📈 Tỷ lệ thành công: {summary['success_rate']:.1f}%")
        
        if self.skipped_symbols:
            print(f"⏭️ Mã bỏ qua: {', '.join(list(self.skipped_symbols)[:10])}{'...' if len(self.skipped_symbols) > 10 else ''}")
        
        return summary
    
    async def _get_vn100_symbols(self) -> List[str]:
        """Lấy danh sách mã VN100"""
        get_database_manager().initialize()
        loader = VN100DatabaseLoader()
        
        try:
            symbols = await loader.get_active_vn100_symbols()
            if symbols:
                return symbols
        except Exception as e:
            print(f"⚠️ Không thể lấy từ database: {e}")
        
        # Fallback từ CSV
        try:
            import pandas as pd
            df = pd.read_csv('assets/data/vn100_official_ssi.csv')
            symbols = df['symbol'].astype(str).str.upper().tolist()
            print(f"📋 Sử dụng danh sách từ CSV: {len(symbols)} mã")
            return symbols
        except Exception as e:
            print(f"❌ Không thể đọc CSV: {e}")
            return []
    
    async def _calculate_indicators_for_symbols(self, symbols: List[str]) -> Dict[str, Any]:
        """Tính toán chỉ số cho danh sách mã"""
        print(f"📈 Bắt đầu tính toán chỉ số cho {len(symbols)} mã")
        
        # Lấy hoặc tạo indicator config
        config_id = await self._get_or_create_indicator_config()
        
        async with get_async_session() as session:
            indicator_repo = IndicatorRepository(session)
            total_batches = (len(symbols) + self.batch_size - 1) // self.batch_size
            
            results = []
            total_calculations = 0
            total_skipped = 0
            
            for i in range(0, len(symbols), self.batch_size):
                batch_num = i // self.batch_size + 1
                chunk = symbols[i:i+self.batch_size]
                
                print(f"🔄 Batch {batch_num}/{total_batches}: {chunk}")
                
                batch_results = []
                for j, symbol in enumerate(chunk):
                    try:
                        result = await self._calculate_indicators_for_symbol(
                            session, indicator_repo, symbol, config_id
                        )
                        batch_results.append(result)
                        
                        if result['success']:
                            self.processed_symbols.add(symbol)
                            total_calculations += result['calculations_count']
                            print(f"  ✅ {symbol}: {result['calculations_count']} tính toán")
                        else:
                            if result.get('skipped', False):
                                self.skipped_symbols.add(symbol)
                                total_skipped += 1
                                print(f"  ⏭️ {symbol}: Bỏ qua (đã có)")
                            else:
                                print(f"  ❌ {symbol}: {result.get('error', 'Unknown error')}")
                        
                        # Delay nhỏ giữa các mã
                        if j < len(chunk) - 1:
                            await asyncio.sleep(0.5)
                            
                    except Exception as e:
                        print(f"  ❌ {symbol}: Exception - {e}")
                        batch_results.append({
                            "symbol": symbol, 
                            "success": False, 
                            "error": str(e)
                        })
                
                results.extend(batch_results)
                
                # Delay giữa các batch
                if i + self.batch_size < len(symbols):
                    print(f"⏳ Chờ 2 giây trước batch tiếp theo...")
                    await asyncio.sleep(2.0)
            
            return {
                "total_symbols": len(symbols),
                "processed_symbols": len(self.processed_symbols),
                "skipped_symbols": len(self.skipped_symbols),
                "total_calculations": total_calculations,
                "total_skipped": total_skipped,
                "results": results
            }
    
    async def _get_or_create_indicator_config(self) -> int:
        """Lấy hoặc tạo indicator config"""
        async with get_async_session() as session:
            config_repo = ConfigRepository(session)
            
            # Tìm config mặc định
            config = await config_repo.get_default_config("indicator")
            if config:
                print(f"📋 Sử dụng indicator config ID: {config['id']}")
                return config['id']
            
            # Tạo config mặc định nếu không có
            print("📋 Tạo indicator config mặc định...")
            config_id = await config_repo.create_config(
                name="Default Indicator Config",
                description="Cấu hình chỉ số mặc định cho VN100",
                config_type="indicator",
                config_data=AnalysisConfig().to_dict()
            )
            print(f"✅ Đã tạo indicator config ID: {config_id}")
            return config_id
    
    async def _calculate_indicators_for_symbol(
        self, 
        session, 
        indicator_repo: IndicatorRepository, 
        symbol: str, 
        config_id: int
    ) -> Dict[str, Any]:
        """Tính toán chỉ số cho một mã"""
        try:
            # Lấy dữ liệu OHLCV
            from analytis.data.loader import load_ohlcv_daily
            
            try:
                data = await load_ohlcv_daily(symbol, self.start_date, self.end_date.isoformat())
                if data is None or data.empty:
                    return {
                        "symbol": symbol,
                        "success": False,
                        "error": "No data available"
                    }
            except Exception as e:
                return {
                    "symbol": symbol,
                    "success": False,
                    "error": f"Failed to load data: {e}"
                }
            
            # Kiểm tra xem đã có dữ liệu chưa để tránh trùng lặp
            existing_calc = await indicator_repo.get_latest_calculation(symbol, config_id)
            if existing_calc:
                existing_date = existing_calc['calculation_date']
                if existing_date >= data.index.max().date():
                    return {
                        "symbol": symbol,
                        "success": True,
                        "skipped": True,
                        "calculations_count": 0,
                        "message": f"Already up to date (last: {existing_date})"
                    }
            
            # Tính toán chỉ số
            indicators_df = self.indicator_engine.calculate_all_indicators(data)
            
            # Lưu kết quả vào database (batch processing)
            calculations_count = 0
            import pandas as pd
            
            # Chuẩn bị dữ liệu batch
            batch_data = []
            for _, row in indicators_df.iterrows():
                try:
                    indicators_dict = {
                        "ma_short": float(row.get("MA9", 0)) if pd.notna(row.get("MA9")) else None,
                        "ma_long": float(row.get("MA50", 0)) if pd.notna(row.get("MA50")) else None,
                        "rsi": float(row.get("RSI", 0)) if pd.notna(row.get("RSI")) else None,
                        "macd": float(row.get("MACD", 0)) if pd.notna(row.get("MACD")) else None,
                        "macd_signal": float(row.get("Signal_Line", 0)) if pd.notna(row.get("Signal_Line")) else None,
                        "macd_histogram": float(row.get("MACD_Hist", 0)) if pd.notna(row.get("MACD_Hist")) else None,
                        "bb_upper": float(row.get("BB_Upper", 0)) if pd.notna(row.get("BB_Upper")) else None,
                        "bb_middle": float(row.get("MA20", 0)) if pd.notna(row.get("MA20")) else None,
                        "bb_lower": float(row.get("BB_Lower", 0)) if pd.notna(row.get("BB_Lower")) else None,
                        "obv": float(row.get("OBV", 0)) if pd.notna(row.get("OBV")) else None,
                        "ichimoku_conversion": float(row.get("Tenkan_sen", 0)) if pd.notna(row.get("Tenkan_sen")) else None,
                        "ichimoku_base": float(row.get("Kijun_sen", 0)) if pd.notna(row.get("Kijun_sen")) else None,
                        "ichimoku_span_a": float(row.get("Senkou_Span_A", 0)) if pd.notna(row.get("Senkou_Span_A")) else None,
                        "ichimoku_span_b": float(row.get("Senkou_Span_B", 0)) if pd.notna(row.get("Senkou_Span_B")) else None,
                    }
                    
                    batch_data.append({
                        "symbol": symbol,
                        "calculation_date": row.name.date(),
                        "config_id": config_id,
                        "indicators": indicators_dict,
                        "data_points": len(data),
                        "start_date": data.index.min().date(),
                        "end_date": data.index.max().date(),
                        "calculation_duration_ms": 0
                    })
                    
                except Exception as e:
                    print(f"    ⚠️ Lỗi chuẩn bị dữ liệu ngày {row.name.date()}: {e}")
                    continue
            
            # Lưu batch vào database
            if batch_data:
                try:
                    await indicator_repo.save_indicator_calculations_batch(batch_data)
                    calculations_count = len(batch_data)
                    print(f"    ✅ Đã lưu {calculations_count} tính toán chỉ số")
                except Exception as e:
                    print(f"    ❌ Lỗi lưu batch: {e}")
                    # Fallback: lưu từng record
                    for data in batch_data:
                        try:
                            await indicator_repo.save_indicator_calculation(
                                symbol=data["symbol"],
                                calculation_date=data["calculation_date"],
                                config_id=data["config_id"],
                                indicators=data["indicators"],
                                data_points=data["data_points"],
                                start_date=data["start_date"],
                                end_date=data["end_date"],
                                calculation_duration_ms=data["calculation_duration_ms"]
                            )
                            calculations_count += 1
                        except Exception as e2:
                            print(f"    ⚠️ Lỗi lưu ngày {data['calculation_date']}: {e2}")
                            continue
            
            return {
                "symbol": symbol,
                "success": True,
                "calculations_count": calculations_count,
                "data_points": len(data)
            }
            
        except Exception as e:
            return {
                "symbol": symbol,
                "success": False,
                "error": str(e)
            }


async def main(batch_size: int = 5, start_date: str = "2010-01-01") -> None:
    """Hàm chính"""
    pipeline = VN100IndicatorsPipeline(batch_size=batch_size, start_date=start_date)
    
    try:
        result = await pipeline.run_pipeline()
        
        # Lưu kết quả
        import json
        from datetime import datetime
        
        output_file = f"output/indicators_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
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
    parser = argparse.ArgumentParser(description="VN100 Indicators Pipeline")
    parser.add_argument("--batch", dest="batch", type=int, default=5, 
                       help="Batch size for processing (default: 5)")
    parser.add_argument("--start-date", dest="start_date", type=str, default="2010-01-01",
                       help="Start date for calculation (default: 2010-01-01)")
    
    args = parser.parse_args()
    
    asyncio.run(main(args.batch, args.start_date))
    return 0


if __name__ == "__main__":
    raise SystemExit(cli_main())
