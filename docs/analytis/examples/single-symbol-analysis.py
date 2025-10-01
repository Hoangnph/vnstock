#!/usr/bin/env python3
"""
Single Symbol Analysis Example

Ví dụ phân tích một mã cổ phiếu với các cấu hình khác nhau
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from analytis.analysis_engine import AnalysisEngine, AnalysisConfig
from analytis.engines.indicator_engine import IndicatorConfig
from analytis.engines.scoring_engine import ScoringConfig
from datetime import datetime, timedelta

def analyze_single_symbol():
    """Phân tích một mã cổ phiếu với cấu hình mặc định"""
    
    # Khởi tạo engine với cấu hình mặc định
    engine = AnalysisEngine()
    
    # Phân tích mã PDR
    symbol = "PDR"
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=180)  # 6 tháng gần đây
    
    print(f"=== Phân tích {symbol} ===")
    print(f"Thời gian: {start_date} đến {end_date}")
    
    # Chạy phân tích
    result = engine.analyze_symbol(
        symbol=symbol,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat()
    )
    
    # Hiển thị kết quả
    print(f"\nKết quả phân tích:")
    print(f"- Số điểm dữ liệu: {result.data_info['total_rows']}")
    print(f"- Số tín hiệu: {len(result.signals)}")
    
    if result.signals:
        # Tín hiệu gần nhất
        latest_signal = result.signals[-1]
        print(f"\nTín hiệu gần nhất:")
        print(f"- Thời gian: {latest_signal.timestamp.date()}")
        print(f"- Hành động: {latest_signal.action.value}")
        print(f"- Sức mạnh: {latest_signal.strength.value}")
        print(f"- Điểm số: {latest_signal.score:.2f}")
        print(f"- Mô tả: {latest_signal.description}")
        
        # Tóm tắt tín hiệu
        summary = result.signal_summary
        print(f"\nTóm tắt tín hiệu:")
        print(f"- Tổng tín hiệu: {summary['total_signals']}")
        print(f"- Tín hiệu mua: {summary['buy_signals']}")
        print(f"- Tín hiệu bán: {summary['sell_signals']}")
        print(f"- Tín hiệu mạnh: {summary['strong_signals']}")
        print(f"- Điểm trung bình: {summary['avg_score']:.2f}")
    
    return result

def analyze_with_custom_config():
    """Phân tích với cấu hình tùy chỉnh"""
    
    # Tạo cấu hình tùy chỉnh
    config = AnalysisConfig(
        indicator_config=IndicatorConfig(
            ma_short=5,      # MA ngắn hơn
            ma_long=30,      # MA dài hơn
            rsi_period=10,   # RSI nhạy cảm hơn
            bb_std=1.5       # Bollinger Bands hẹp hơn
        ),
        scoring_config=ScoringConfig(
            strong_threshold=60.0,      # Ngưỡng thấp hơn
            medium_threshold=20.0,
            buy_strong_threshold=-60.0,
            sell_strong_threshold=60.0,
            context_multipliers={
                "uptrend_buy": 2.0,     # Tăng mạnh trong xu hướng tăng
                "uptrend_sell": 0.3,
                "downtrend_sell": 2.0,
                "downtrend_buy": 0.3,
                "sideways": 0.6
            }
        ),
        min_score_threshold=8.0,    # Ngưỡng thấp hơn
        lookback_days=90            # Thời gian ngắn hơn
    )
    
    # Khởi tạo engine với cấu hình tùy chỉnh
    engine = AnalysisEngine(config)
    
    # Phân tích
    symbol = "PDR"
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=90)
    
    print(f"\n=== Phân tích {symbol} với cấu hình tùy chỉnh ===")
    print(f"Thời gian: {start_date} đến {end_date}")
    
    result = engine.analyze_symbol(
        symbol=symbol,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat()
    )
    
    # Hiển thị kết quả
    print(f"\nKết quả phân tích:")
    print(f"- Số điểm dữ liệu: {result.data_info['total_rows']}")
    print(f"- Số tín hiệu: {len(result.signals)}")
    
    if result.signals:
        # Tín hiệu mua mạnh
        strong_buy_signals = [
            s for s in result.signals 
            if s.action.value == "MUA" and s.strength.value == "RẤT MẠNH"
        ]
        
        print(f"\nTín hiệu mua mạnh: {len(strong_buy_signals)}")
        for signal in strong_buy_signals[-3:]:  # 3 tín hiệu gần nhất
            print(f"- {signal.timestamp.date()}: {signal.score:.2f} điểm")
            print(f"  {signal.description}")
        
        # Tín hiệu bán mạnh
        strong_sell_signals = [
            s for s in result.signals 
            if s.action.value == "BÁN" and s.strength.value == "RẤT MẠNH"
        ]
        
        print(f"\nTín hiệu bán mạnh: {len(strong_sell_signals)}")
        for signal in strong_sell_signals[-3:]:  # 3 tín hiệu gần nhất
            print(f"- {signal.timestamp.date()}: {signal.score:.2f} điểm")
            print(f"  {signal.description}")
    
    return result

def compare_configurations():
    """So sánh kết quả với các cấu hình khác nhau"""
    
    symbol = "PDR"
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=120)
    
    # Cấu hình 1: Nhạy cảm
    config1 = AnalysisConfig(
        min_score_threshold=5.0,
        lookback_days=60,
        indicator_config=IndicatorConfig(ma_short=3, ma_long=15, rsi_period=7),
        scoring_config=ScoringConfig(strong_threshold=50.0, buy_strong_threshold=-50.0, sell_strong_threshold=50.0)
    )
    
    # Cấu hình 2: Bảo thủ
    config2 = AnalysisConfig(
        min_score_threshold=20.0,
        lookback_days=180,
        indicator_config=IndicatorConfig(ma_short=20, ma_long=100, rsi_period=21),
        scoring_config=ScoringConfig(strong_threshold=90.0, buy_strong_threshold=-90.0, sell_strong_threshold=90.0)
    )
    
    # Cấu hình 3: Cân bằng
    config3 = AnalysisConfig()  # Mặc định
    
    print(f"\n=== So sánh cấu hình cho {symbol} ===")
    print(f"Thời gian: {start_date} đến {end_date}")
    
    results = []
    configs = [
        ("Nhạy cảm", config1),
        ("Bảo thủ", config2),
        ("Cân bằng", config3)
    ]
    
    for name, config in configs:
        engine = AnalysisEngine(config)
        result = engine.analyze_symbol(
            symbol=symbol,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat()
        )
        
        results.append((name, result))
        
        print(f"\n{name}:")
        print(f"- Tín hiệu: {len(result.signals)}")
        if result.signals:
            summary = result.signal_summary
            print(f"- Mua: {summary['buy_signals']}, Bán: {summary['sell_signals']}")
            print(f"- Mạnh: {summary['strong_signals']}, Trung bình: {summary['medium_signals']}")
            print(f"- Điểm TB: {summary['avg_score']:.2f}")
    
    # So sánh tín hiệu mua mạnh
    print(f"\n=== Tín hiệu mua mạnh ===")
    for name, result in results:
        strong_buy = [
            s for s in result.signals 
            if s.action.value == "MUA" and s.strength.value == "RẤT MẠNH"
        ]
        print(f"{name}: {len(strong_buy)} tín hiệu")
        
        if strong_buy:
            latest = strong_buy[-1]
            print(f"  Gần nhất: {latest.timestamp.date()} ({latest.score:.2f} điểm)")
    
    return results

def analyze_with_database():
    """Phân tích với lưu trữ database"""
    
    try:
        from analytis.analysis_engine_db import DatabaseIntegratedAnalysisEngine
        import asyncio
        
        async def run_analysis():
            # Khởi tạo engine tích hợp database
            engine = DatabaseIntegratedAnalysisEngine()
            
            # Phân tích
            symbol = "PDR"
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=90)
            
            print(f"\n=== Phân tích {symbol} với database ===")
            print(f"Thời gian: {start_date} đến {end_date}")
            
            result = await engine.analyze_symbol(
                symbol=symbol,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat()
            )
            
            # Hiển thị thông tin database
            print(f"\nThông tin database:")
            print(f"- Analysis Result ID: {result.analysis_result_id}")
            print(f"- Indicator Config ID: {result.indicator_config_id}")
            print(f"- Scoring Config ID: {result.scoring_config_id}")
            print(f"- Analysis Config ID: {result.analysis_config_id}")
            
            # Lấy lịch sử phân tích
            history = await engine.get_analysis_history(symbol, limit=5)
            print(f"\nLịch sử phân tích: {len(history)} bản ghi")
            for h in history:
                print(f"- {h['analysis_date']}: {h['total_signals']} tín hiệu")
            
            # Lấy lịch sử tín hiệu
            signal_history = await engine.get_signal_history(symbol, limit=10)
            print(f"\nLịch sử tín hiệu: {len(signal_history)} bản ghi")
            for s in signal_history[:5]:
                print(f"- {s['signal_date']}: {s['action']} {s['strength']} ({s['score']:.2f})")
            
            # Thống kê database
            stats = await engine.get_database_stats()
            print(f"\nThống kê database:")
            print(f"- Configurations: {stats.get('configurations', {})}")
            print(f"- Indicator Calculations: {stats.get('indicator_calculations', {}).get('total_calculations', 0)}")
            print(f"- Analysis Results: {stats.get('analysis_results', {}).get('total_analyses', 0)}")
            print(f"- Signals: {stats.get('signals', {}).get('total_signals', 0)}")
            
            return result
        
        # Chạy phân tích async
        result = asyncio.run(run_analysis())
        return result
        
    except ImportError:
        print("Database engine không khả dụng, sử dụng engine thường")
        return analyze_single_symbol()

def main():
    """Hàm chính"""
    
    print("=== Ví dụ phân tích một mã cổ phiếu ===")
    
    try:
        # 1. Phân tích cơ bản
        result1 = analyze_single_symbol()
        
        # 2. Phân tích với cấu hình tùy chỉnh
        result2 = analyze_with_custom_config()
        
        # 3. So sánh cấu hình
        results = compare_configurations()
        
        # 4. Phân tích với database (nếu có)
        result3 = analyze_with_database()
        
        print("\n=== Hoàn thành ===")
        print("Tất cả ví dụ đã chạy thành công!")
        
    except Exception as e:
        print(f"Lỗi: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
