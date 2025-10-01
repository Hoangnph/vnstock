#!/usr/bin/env python3
"""
Batch Analysis Example

Ví dụ phân tích hàng loạt nhiều mã cổ phiếu
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from analytis.analysis_engine import AnalysisEngine, AnalysisConfig
from analytis.engines.indicator_engine import IndicatorConfig
from analytis.engines.scoring_engine import ScoringConfig
from datetime import datetime, timedelta
import asyncio
import json

def get_vn100_symbols():
    """Lấy danh sách mã VN100"""
    # Danh sách mẫu VN100
    return [
        "ACB", "BCM", "BID", "BVH", "CTG", "FPT", "GAS", "GVR", "HDB", "HPG",
        "MBB", "MSN", "MWG", "PLX", "POW", "PDR", "PVD", "SAB", "SSI", "TCB",
        "TPB", "VCB", "VHM", "VIC", "VJC", "VNM", "VPB", "VRE", "VSH", "VTO"
    ]

def analyze_batch_basic():
    """Phân tích hàng loạt cơ bản"""
    
    symbols = get_vn100_symbols()[:10]  # 10 mã đầu tiên
    engine = AnalysisEngine()
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=90)
    
    print(f"=== Phân tích hàng loạt cơ bản ===")
    print(f"Thời gian: {start_date} đến {end_date}")
    print(f"Số mã: {len(symbols)}")
    
    results = []
    
    for i, symbol in enumerate(symbols, 1):
        print(f"\n[{i}/{len(symbols)}] Phân tích {symbol}...")
        
        try:
            result = engine.analyze_symbol(
                symbol=symbol,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat()
            )
            
            results.append({
                'symbol': symbol,
                'success': True,
                'signals_count': len(result.signals),
                'data_points': result.data_info['total_rows'],
                'latest_signal': result.signals[-1] if result.signals else None
            })
            
            print(f"  ✅ Thành công: {len(result.signals)} tín hiệu")
            
        except Exception as e:
            results.append({
                'symbol': symbol,
                'success': False,
                'error': str(e)
            })
            print(f"  ❌ Lỗi: {e}")
    
    # Tóm tắt kết quả
    print(f"\n=== Tóm tắt kết quả ===")
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    print(f"Thành công: {len(successful)}/{len(results)}")
    print(f"Thất bại: {len(failed)}")
    
    if successful:
        total_signals = sum(r['signals_count'] for r in successful)
        avg_signals = total_signals / len(successful)
        print(f"Tổng tín hiệu: {total_signals}")
        print(f"Trung bình tín hiệu/mã: {avg_signals:.1f}")
        
        # Top 5 mã có nhiều tín hiệu nhất
        top_signals = sorted(successful, key=lambda x: x['signals_count'], reverse=True)[:5]
        print(f"\nTop 5 mã có nhiều tín hiệu:")
        for r in top_signals:
            print(f"- {r['symbol']}: {r['signals_count']} tín hiệu")
    
    if failed:
        print(f"\nMã thất bại:")
        for r in failed:
            print(f"- {r['symbol']}: {r['error']}")
    
    return results

def analyze_batch_with_configs():
    """Phân tích hàng loạt với nhiều cấu hình"""
    
    symbols = get_vn100_symbols()[:5]  # 5 mã đầu tiên
    
    # Cấu hình 1: Nhạy cảm
    config1 = AnalysisConfig(
        min_score_threshold=5.0,
        lookback_days=60,
        indicator_config=IndicatorConfig(ma_short=3, ma_long=15, rsi_period=7),
        scoring_config=ScoringConfig(strong_threshold=50.0)
    )
    
    # Cấu hình 2: Bảo thủ
    config2 = AnalysisConfig(
        min_score_threshold=20.0,
        lookback_days=180,
        indicator_config=IndicatorConfig(ma_short=20, ma_long=100, rsi_period=21),
        scoring_config=ScoringConfig(strong_threshold=90.0)
    )
    
    configs = [
        ("Nhạy cảm", config1),
        ("Bảo thủ", config2)
    ]
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=120)
    
    print(f"\n=== Phân tích hàng loạt với nhiều cấu hình ===")
    print(f"Thời gian: {start_date} đến {end_date}")
    print(f"Số mã: {len(symbols)}")
    print(f"Số cấu hình: {len(configs)}")
    
    all_results = {}
    
    for config_name, config in configs:
        print(f"\n--- Cấu hình: {config_name} ---")
        engine = AnalysisEngine(config)
        config_results = []
        
        for i, symbol in enumerate(symbols, 1):
            print(f"[{i}/{len(symbols)}] {symbol}...")
            
            try:
                result = engine.analyze_symbol(
                    symbol=symbol,
                    start_date=start_date.isoformat(),
                    end_date=end_date.isoformat()
                )
                
                config_results.append({
                    'symbol': symbol,
                    'success': True,
                    'signals_count': len(result.signals),
                    'data_points': result.data_info['total_rows'],
                    'summary': result.signal_summary
                })
                
                print(f"  ✅ {len(result.signals)} tín hiệu")
                
            except Exception as e:
                config_results.append({
                    'symbol': symbol,
                    'success': False,
                    'error': str(e)
                })
                print(f"  ❌ {e}")
        
        all_results[config_name] = config_results
    
    # So sánh kết quả
    print(f"\n=== So sánh kết quả ===")
    
    for config_name, results in all_results.items():
        successful = [r for r in results if r['success']]
        if successful:
            total_signals = sum(r['signals_count'] for r in successful)
            avg_signals = total_signals / len(successful)
            print(f"\n{config_name}:")
            print(f"- Thành công: {len(successful)}/{len(results)}")
            print(f"- Tổng tín hiệu: {total_signals}")
            print(f"- Trung bình: {avg_signals:.1f}")
            
            # Top 3 mã
            top = sorted(successful, key=lambda x: x['signals_count'], reverse=True)[:3]
            print(f"- Top 3: {', '.join(f'{r['symbol']}({r['signals_count']})' for r in top)}")
    
    return all_results

def analyze_batch_async():
    """Phân tích hàng loạt bất đồng bộ"""
    
    symbols = get_vn100_symbols()[:10]
    engine = AnalysisEngine()
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=90)
    
    print(f"\n=== Phân tích hàng loạt bất đồng bộ ===")
    print(f"Thời gian: {start_date} đến {end_date}")
    print(f"Số mã: {len(symbols)}")
    
    async def analyze_symbol_async(symbol):
        """Phân tích một mã bất đồng bộ"""
        try:
            result = engine.analyze_symbol(
                symbol=symbol,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat()
            )
            return {
                'symbol': symbol,
                'success': True,
                'signals_count': len(result.signals),
                'data_points': result.data_info['total_rows']
            }
        except Exception as e:
            return {
                'symbol': symbol,
                'success': False,
                'error': str(e)
            }
    
    async def run_batch_async():
        """Chạy phân tích hàng loạt bất đồng bộ"""
        tasks = [analyze_symbol_async(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Xử lý kết quả
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    'symbol': symbols[i],
                    'success': False,
                    'error': str(result)
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    # Chạy phân tích
    results = asyncio.run(run_batch_async())
    
    # Hiển thị kết quả
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    print(f"\nKết quả:")
    print(f"Thành công: {len(successful)}/{len(results)}")
    print(f"Thất bại: {len(failed)}")
    
    if successful:
        total_signals = sum(r['signals_count'] for r in successful)
        avg_signals = total_signals / len(successful)
        print(f"Tổng tín hiệu: {total_signals}")
        print(f"Trung bình: {avg_signals:.1f}")
    
    return results

def analyze_batch_with_database():
    """Phân tích hàng loạt với lưu trữ database"""
    
    try:
        from analytis.analysis_engine_db import DatabaseIntegratedAnalysisEngine
        
        symbols = get_vn100_symbols()[:5]
        
        async def run_batch_db():
            engine = DatabaseIntegratedAnalysisEngine()
            
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=90)
            
            print(f"\n=== Phân tích hàng loạt với database ===")
            print(f"Thời gian: {start_date} đến {end_date}")
            print(f"Số mã: {len(symbols)}")
            
            results = []
            
            for i, symbol in enumerate(symbols, 1):
                print(f"[{i}/{len(symbols)}] {symbol}...")
                
                try:
                    result = await engine.analyze_symbol(
                        symbol=symbol,
                        start_date=start_date.isoformat(),
                        end_date=end_date.isoformat()
                    )
                    
                    results.append({
                        'symbol': symbol,
                        'success': True,
                        'signals_count': len(result.signals),
                        'analysis_result_id': result.analysis_result_id
                    })
                    
                    print(f"  ✅ {len(result.signals)} tín hiệu (ID: {result.analysis_result_id})")
                    
                except Exception as e:
                    results.append({
                        'symbol': symbol,
                        'success': False,
                        'error': str(e)
                    })
                    print(f"  ❌ {e}")
            
            # Thống kê database
            stats = await engine.get_database_stats()
            print(f"\nThống kê database sau phân tích:")
            print(f"- Analysis Results: {stats.get('analysis_results', {}).get('total_analyses', 0)}")
            print(f"- Signals: {stats.get('signals', {}).get('total_signals', 0)}")
            
            return results
        
        # Chạy phân tích
        results = asyncio.run(run_batch_db())
        return results
        
    except ImportError:
        print("Database engine không khả dụng, sử dụng engine thường")
        return analyze_batch_basic()

def export_results_to_json(results, filename="batch_analysis_results.json"):
    """Xuất kết quả ra file JSON"""
    
    # Chuyển đổi kết quả thành JSON serializable
    def serialize_result(result):
        if result['success']:
            return {
                'symbol': result['symbol'],
                'success': True,
                'signals_count': result['signals_count'],
                'data_points': result.get('data_points', 0)
            }
        else:
            return {
                'symbol': result['symbol'],
                'success': False,
                'error': result['error']
            }
    
    # Xử lý kết quả
    if isinstance(results, dict):
        # Nhiều cấu hình
        serialized = {}
        for config_name, config_results in results.items():
            serialized[config_name] = [serialize_result(r) for r in config_results]
    else:
        # Một cấu hình
        serialized = [serialize_result(r) for r in results]
    
    # Lưu file
    output_path = os.path.join(os.path.dirname(__file__), filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(serialized, f, ensure_ascii=False, indent=2)
    
    print(f"\nKết quả đã được lưu vào: {output_path}")
    return output_path

def main():
    """Hàm chính"""
    
    print("=== Ví dụ phân tích hàng loạt ===")
    
    try:
        # 1. Phân tích cơ bản
        results1 = analyze_batch_basic()
        
        # 2. Phân tích với nhiều cấu hình
        results2 = analyze_batch_with_configs()
        
        # 3. Phân tích bất đồng bộ
        results3 = analyze_batch_async()
        
        # 4. Phân tích với database (nếu có)
        results4 = analyze_batch_with_database()
        
        # 5. Xuất kết quả
        export_results_to_json(results1, "batch_basic_results.json")
        export_results_to_json(results2, "batch_configs_results.json")
        export_results_to_json(results3, "batch_async_results.json")
        
        print("\n=== Hoàn thành ===")
        print("Tất cả ví dụ phân tích hàng loạt đã chạy thành công!")
        
    except Exception as e:
        print(f"Lỗi: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
