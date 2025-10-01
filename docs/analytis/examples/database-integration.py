#!/usr/bin/env python3
"""
Database Integration Example

Ví dụ tích hợp với database cho phân tích
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime, timedelta
import asyncio
import json

def test_database_connection():
    """Kiểm tra kết nối database"""
    
    print("=== Kiểm tra kết nối database ===")
    
    try:
        from analytis.analysis_engine_db import DatabaseIntegratedAnalysisEngine
        
        async def check_connection():
            engine = DatabaseIntegratedAnalysisEngine()
            
            # Kiểm tra kết nối
            stats = await engine.get_database_stats()
            print("✅ Kết nối database thành công")
            
            # Hiển thị thống kê
            print(f"\nThống kê database:")
            print(f"- Configurations: {stats.get('configurations', {})}")
            print(f"- Indicator Calculations: {stats.get('indicator_calculations', {}).get('total_calculations', 0)}")
            print(f"- Analysis Results: {stats.get('analysis_results', {}).get('total_analyses', 0)}")
            print(f"- Signals: {stats.get('signals', {}).get('total_signals', 0)}")
            
            return True
        
        return asyncio.run(check_connection())
        
    except ImportError:
        print("❌ Database engine không khả dụng")
        return False
    except Exception as e:
        print(f"❌ Lỗi kết nối database: {e}")
        return False

def analyze_with_database():
    """Phân tích với lưu trữ database"""
    
    print("\n=== Phân tích với database ===")
    
    try:
        from analytis.analysis_engine_db import DatabaseIntegratedAnalysisEngine
        
        async def run_analysis():
            engine = DatabaseIntegratedAnalysisEngine()
            
            # Phân tích
            symbol = "PDR"
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=90)
            
            print(f"Mã: {symbol}")
            print(f"Thời gian: {start_date} đến {end_date}")
            
            result = await engine.analyze_symbol(
                symbol=symbol,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat()
            )
            
            # Hiển thị kết quả
            print(f"\nKết quả phân tích:")
            print(f"- Analysis Result ID: {result.analysis_result_id}")
            print(f"- Indicator Config ID: {result.indicator_config_id}")
            print(f"- Scoring Config ID: {result.scoring_config_id}")
            print(f"- Analysis Config ID: {result.analysis_config_id}")
            print(f"- Số tín hiệu: {len(result.signals)}")
            
            if result.signals:
                summary = result.signal_summary
                print(f"- Tín hiệu mua: {summary['buy_signals']}")
                print(f"- Tín hiệu bán: {summary['sell_signals']}")
                print(f"- Tín hiệu mạnh: {summary['strong_signals']}")
                print(f"- Điểm trung bình: {summary['avg_score']:.2f}")
                
                # Tín hiệu gần nhất
                latest = result.signals[-1]
                print(f"- Tín hiệu gần nhất: {latest.timestamp.date()} - {latest.action.value} {latest.strength.value}")
            
            return result
        
        return asyncio.run(run_analysis())
        
    except ImportError:
        print("Database engine không khả dụng")
        return None
    except Exception as e:
        print(f"Lỗi: {e}")
        return None

def query_analysis_history():
    """Truy vấn lịch sử phân tích"""
    
    print("\n=== Truy vấn lịch sử phân tích ===")
    
    try:
        from analytis.analysis_engine_db import DatabaseIntegratedAnalysisEngine
        
        async def run_query():
            engine = DatabaseIntegratedAnalysisEngine()
            
            # Lấy lịch sử phân tích
            symbol = "PDR"
            history = await engine.get_analysis_history(symbol, limit=10)
            
            print(f"Lịch sử phân tích {symbol}:")
            print(f"{'Ngày':<12} {'Tín hiệu':<10} {'Mua':<5} {'Bán':<5} {'Điểm TB':<10}")
            print("-" * 50)
            
            for h in history:
                print(f"{h['analysis_date']:<12} {h['total_signals']:<10} {h['buy_signals']:<5} {h['sell_signals']:<5} {h['avg_score']:<10.2f}")
            
            # Lấy lịch sử tín hiệu
            signal_history = await engine.get_signal_history(symbol, limit=15)
            
            print(f"\nLịch sử tín hiệu {symbol}:")
            print(f"{'Ngày':<12} {'Hành động':<10} {'Sức mạnh':<12} {'Điểm':<10} {'Mô tả':<30}")
            print("-" * 80)
            
            for s in signal_history:
                description = s['description'][:27] + "..." if len(s['description']) > 30 else s['description']
                print(f"{s['signal_date']:<12} {s['action']:<10} {s['strength']:<12} {s['score']:<10.2f} {description:<30}")
            
            return history, signal_history
        
        return asyncio.run(run_query())
        
    except ImportError:
        print("Database engine không khả dụng")
        return None, None
    except Exception as e:
        print(f"Lỗi: {e}")
        return None, None

def query_by_configuration():
    """Truy vấn theo cấu hình"""
    
    print("\n=== Truy vấn theo cấu hình ===")
    
    try:
        from analytis.analysis_engine_db import DatabaseIntegratedAnalysisEngine
        
        async def run_query():
            engine = DatabaseIntegratedAnalysisEngine()
            
            # Lấy danh sách cấu hình
            configs = await engine.get_configurations()
            
            print(f"Cấu hình có sẵn:")
            for config in configs:
                print(f"- ID: {config['id']}, Tên: {config['name']}, Loại: {config['config_type']}")
            
            if configs:
                # Lấy cấu hình đầu tiên
                config_id = configs[0]['id']
                print(f"\nSử dụng cấu hình ID: {config_id}")
                
                # Lấy kết quả phân tích với cấu hình này
                results = await engine.get_analysis_by_config(config_id, limit=10)
                
                print(f"\nKết quả phân tích với cấu hình {config_id}:")
                print(f"{'Mã':<8} {'Ngày':<12} {'Tín hiệu':<10} {'Mua':<5} {'Bán':<5}")
                print("-" * 50)
                
                for result in results:
                    print(f"{result['symbol']:<8} {result['analysis_date']:<12} {result['total_signals']:<10} {result['buy_signals']:<5} {result['sell_signals']:<5}")
            
            return configs, results if 'results' in locals() else []
        
        return asyncio.run(run_query())
        
    except ImportError:
        print("Database engine không khả dụng")
        return [], []
    except Exception as e:
        print(f"Lỗi: {e}")
        return [], []

def query_signals_by_action():
    """Truy vấn tín hiệu theo hành động"""
    
    print("\n=== Truy vấn tín hiệu theo hành động ===")
    
    try:
        from analytis.analysis_engine_db import DatabaseIntegratedAnalysisEngine
        
        async def run_query():
            engine = DatabaseIntegratedAnalysisEngine()
            
            # Tín hiệu mua mạnh
            buy_signals = await engine.get_signals_by_action("MUA", strength="RẤT MẠNH", limit=10)
            
            print(f"Tín hiệu mua mạnh (10 gần nhất):")
            print(f"{'Mã':<8} {'Ngày':<12} {'Điểm':<10} {'Mô tả':<40}")
            print("-" * 70)
            
            for signal in buy_signals:
                description = signal['description'][:37] + "..." if len(signal['description']) > 40 else signal['description']
                print(f"{signal['symbol']:<8} {signal['signal_date']:<12} {signal['score']:<10.2f} {description:<40}")
            
            # Tín hiệu bán mạnh
            sell_signals = await engine.get_signals_by_action("BÁN", strength="RẤT MẠNH", limit=10)
            
            print(f"\nTín hiệu bán mạnh (10 gần nhất):")
            print(f"{'Mã':<8} {'Ngày':<12} {'Điểm':<10} {'Mô tả':<40}")
            print("-" * 70)
            
            for signal in sell_signals:
                description = signal['description'][:37] + "..." if len(signal['description']) > 40 else signal['description']
                print(f"{signal['symbol']:<8} {signal['signal_date']:<12} {signal['score']:<10.2f} {description:<40}")
            
            return buy_signals, sell_signals
        
        return asyncio.run(run_query())
        
    except ImportError:
        print("Database engine không khả dụng")
        return [], []
    except Exception as e:
        print(f"Lỗi: {e}")
        return [], []

def query_performance_stats():
    """Truy vấn thống kê hiệu suất"""
    
    print("\n=== Thống kê hiệu suất ===")
    
    try:
        from analytis.analysis_engine_db import DatabaseIntegratedAnalysisEngine
        
        async def run_query():
            engine = DatabaseIntegratedAnalysisEngine()
            
            # Thống kê tổng quan
            stats = await engine.get_database_stats()
            
            print(f"Thống kê tổng quan:")
            print(f"- Configurations: {stats.get('configurations', {})}")
            print(f"- Indicator Calculations: {stats.get('indicator_calculations', {})}")
            print(f"- Analysis Results: {stats.get('analysis_results', {})}")
            print(f"- Signals: {stats.get('signals', {})}")
            
            # Thống kê theo thời gian
            time_stats = await engine.get_performance_stats()
            
            print(f"\nThống kê theo thời gian:")
            print(f"- Phân tích hôm nay: {time_stats.get('today_analyses', 0)}")
            print(f"- Phân tích tuần này: {time_stats.get('week_analyses', 0)}")
            print(f"- Phân tích tháng này: {time_stats.get('month_analyses', 0)}")
            print(f"- Tín hiệu hôm nay: {time_stats.get('today_signals', 0)}")
            print(f"- Tín hiệu tuần này: {time_stats.get('week_signals', 0)}")
            print(f"- Tín hiệu tháng này: {time_stats.get('month_signals', 0)}")
            
            # Top mã có nhiều tín hiệu nhất
            top_symbols = await engine.get_top_symbols_by_signals(limit=10)
            
            print(f"\nTop 10 mã có nhiều tín hiệu nhất:")
            print(f"{'Mã':<8} {'Tín hiệu':<10} {'Mua':<5} {'Bán':<5} {'Điểm TB':<10}")
            print("-" * 50)
            
            for symbol in top_symbols:
                print(f"{symbol['symbol']:<8} {symbol['total_signals']:<10} {symbol['buy_signals']:<5} {symbol['sell_signals']:<5} {symbol['avg_score']:<10.2f}")
            
            return stats, time_stats, top_symbols
        
        return asyncio.run(run_query())
        
    except ImportError:
        print("Database engine không khả dụng")
        return {}, {}, []
    except Exception as e:
        print(f"Lỗi: {e}")
        return {}, {}, []

def export_database_data():
    """Xuất dữ liệu database"""
    
    print("\n=== Xuất dữ liệu database ===")
    
    try:
        from analytis.analysis_engine_db import DatabaseIntegratedAnalysisEngine
        
        async def run_export():
            engine = DatabaseIntegratedAnalysisEngine()
            
            # Xuất tín hiệu gần đây
            recent_signals = await engine.get_recent_signals(days=30, limit=100)
            
            # Xuất kết quả phân tích gần đây
            recent_analyses = await engine.get_recent_analyses(days=30, limit=50)
            
            # Tạo dữ liệu xuất
            export_data = {
                'export_info': {
                    'export_date': datetime.now().isoformat(),
                    'signals_count': len(recent_signals),
                    'analyses_count': len(recent_analyses)
                },
                'recent_signals': recent_signals,
                'recent_analyses': recent_analyses
            }
            
            # Lưu file
            output_path = os.path.join(os.path.dirname(__file__), "database_export.json")
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
            
            print(f"Đã xuất dữ liệu:")
            print(f"- Tín hiệu: {len(recent_signals)}")
            print(f"- Kết quả phân tích: {len(recent_analyses)}")
            print(f"- File: {output_path}")
            
            return export_data
        
        return asyncio.run(run_export())
        
    except ImportError:
        print("Database engine không khả dụng")
        return None
    except Exception as e:
        print(f"Lỗi: {e}")
        return None

def cleanup_old_data():
    """Dọn dẹp dữ liệu cũ"""
    
    print("\n=== Dọn dẹp dữ liệu cũ ===")
    
    try:
        from analytis.analysis_engine_db import DatabaseIntegratedAnalysisEngine
        
        async def run_cleanup():
            engine = DatabaseIntegratedAnalysisEngine()
            
            # Dọn dẹp dữ liệu cũ hơn 6 tháng
            cutoff_date = (datetime.now() - timedelta(days=180)).date()
            
            print(f"Dọn dẹp dữ liệu cũ hơn {cutoff_date}")
            
            # Đếm dữ liệu sẽ bị xóa
            old_analyses = await engine.count_old_analyses(cutoff_date)
            old_signals = await engine.count_old_signals(cutoff_date)
            old_indicators = await engine.count_old_indicators(cutoff_date)
            
            print(f"Dữ liệu sẽ bị xóa:")
            print(f"- Kết quả phân tích: {old_analyses}")
            print(f"- Tín hiệu: {old_signals}")
            print(f"- Chỉ số: {old_indicators}")
            
            if old_analyses > 0 or old_signals > 0 or old_indicators > 0:
                # Thực hiện dọn dẹp
                deleted = await engine.cleanup_old_data(cutoff_date)
                
                print(f"\nĐã xóa:")
                print(f"- Kết quả phân tích: {deleted.get('analyses', 0)}")
                print(f"- Tín hiệu: {deleted.get('signals', 0)}")
                print(f"- Chỉ số: {deleted.get('indicators', 0)}")
            else:
                print("Không có dữ liệu cũ cần dọn dẹp")
            
            return deleted if 'deleted' in locals() else {}
        
        return asyncio.run(run_cleanup())
        
    except ImportError:
        print("Database engine không khả dụng")
        return {}
    except Exception as e:
        print(f"Lỗi: {e}")
        return {}

def main():
    """Hàm chính"""
    
    print("=== Ví dụ tích hợp database ===")
    
    try:
        # 1. Kiểm tra kết nối
        connection_ok = test_database_connection()
        
        if not connection_ok:
            print("Không thể kết nối database, dừng chương trình")
            return
        
        # 2. Phân tích với database
        result = analyze_with_database()
        
        # 3. Truy vấn lịch sử
        history, signal_history = query_analysis_history()
        
        # 4. Truy vấn theo cấu hình
        configs, config_results = query_by_configuration()
        
        # 5. Truy vấn tín hiệu theo hành động
        buy_signals, sell_signals = query_signals_by_action()
        
        # 6. Thống kê hiệu suất
        stats, time_stats, top_symbols = query_performance_stats()
        
        # 7. Xuất dữ liệu
        export_data = export_database_data()
        
        # 8. Dọn dẹp dữ liệu cũ
        cleanup_result = cleanup_old_data()
        
        print("\n=== Hoàn thành ===")
        print("Tất cả ví dụ tích hợp database đã chạy thành công!")
        
    except Exception as e:
        print(f"Lỗi: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
