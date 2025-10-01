#!/usr/bin/env python3
"""
Configuration Management Example

Ví dụ quản lý cấu hình phân tích
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from analytis.analysis_engine import AnalysisEngine, AnalysisConfig
from analytis.engines.indicator_engine import IndicatorConfig
from analytis.engines.scoring_engine import ScoringConfig
from datetime import datetime, timedelta
import json

def create_custom_configs():
    """Tạo các cấu hình tùy chỉnh"""
    
    print("=== Tạo cấu hình tùy chỉnh ===")
    
    # Cấu hình 1: Scalping (lướt sóng ngắn hạn)
    scalping_config = AnalysisConfig(
        name="Scalping Strategy",
        description="Chiến lược lướt sóng ngắn hạn, nhạy cảm với biến động",
        indicator_config=IndicatorConfig(
            ma_short=3,          # MA ngắn
            ma_long=15,          # MA dài
            rsi_period=7,        # RSI nhạy cảm
            bb_std=1.0,          # Bollinger Bands hẹp
            macd_fast=5,         # MACD nhanh
            macd_slow=13,        # MACD chậm
            macd_signal=5,       # MACD signal
            obv_enabled=True,    # Bật OBV
            ichimoku_enabled=False  # Tắt Ichimoku (quá chậm)
        ),
        scoring_config=ScoringConfig(
            strong_threshold=40.0,      # Ngưỡng thấp
            medium_threshold=15.0,
            buy_strong_threshold=-40.0,
            sell_strong_threshold=40.0,
            context_multipliers={
                "uptrend_buy": 1.5,
                "uptrend_sell": 0.5,
                "downtrend_sell": 1.5,
                "downtrend_buy": 0.5,
                "sideways": 0.8
            }
        ),
        min_score_threshold=5.0,    # Ngưỡng thấp
        lookback_days=30            # Thời gian ngắn
    )
    
    # Cấu hình 2: Swing Trading (giao dịch theo sóng)
    swing_config = AnalysisConfig(
        name="Swing Trading Strategy",
        description="Chiến lược giao dịch theo sóng trung hạn",
        indicator_config=IndicatorConfig(
            ma_short=10,         # MA trung bình
            ma_long=50,          # MA dài
            rsi_period=14,       # RSI chuẩn
            bb_std=2.0,          # Bollinger Bands chuẩn
            macd_fast=12,        # MACD chuẩn
            macd_slow=26,        # MACD chuẩn
            macd_signal=9,       # MACD signal chuẩn
            obv_enabled=True,    # Bật OBV
            ichimoku_enabled=True  # Bật Ichimoku
        ),
        scoring_config=ScoringConfig(
            strong_threshold=70.0,      # Ngưỡng trung bình
            medium_threshold=25.0,
            buy_strong_threshold=-70.0,
            sell_strong_threshold=70.0,
            context_multipliers={
                "uptrend_buy": 2.0,
                "uptrend_sell": 0.3,
                "downtrend_sell": 2.0,
                "downtrend_buy": 0.3,
                "sideways": 0.6
            }
        ),
        min_score_threshold=15.0,   # Ngưỡng trung bình
        lookback_days=90            # Thời gian trung bình
    )
    
    # Cấu hình 3: Position Trading (giao dịch dài hạn)
    position_config = AnalysisConfig(
        name="Position Trading Strategy",
        description="Chiến lược giao dịch dài hạn, ít tín hiệu nhưng chất lượng cao",
        indicator_config=IndicatorConfig(
            ma_short=20,         # MA dài
            ma_long=100,         # MA rất dài
            rsi_period=21,       # RSI chậm
            bb_std=2.5,          # Bollinger Bands rộng
            macd_fast=12,        # MACD chuẩn
            macd_slow=26,        # MACD chuẩn
            macd_signal=9,       # MACD signal chuẩn
            obv_enabled=True,    # Bật OBV
            ichimoku_enabled=True  # Bật Ichimoku
        ),
        scoring_config=ScoringConfig(
            strong_threshold=90.0,      # Ngưỡng cao
            medium_threshold=40.0,
            buy_strong_threshold=-90.0,
            sell_strong_threshold=90.0,
            context_multipliers={
                "uptrend_buy": 3.0,
                "uptrend_sell": 0.2,
                "downtrend_sell": 3.0,
                "downtrend_buy": 0.2,
                "sideways": 0.4
            }
        ),
        min_score_threshold=30.0,   # Ngưỡng cao
        lookback_days=180           # Thời gian dài
    )
    
    # Cấu hình 4: Momentum Trading (giao dịch theo động lượng)
    momentum_config = AnalysisConfig(
        name="Momentum Trading Strategy",
        description="Chiến lược giao dịch theo động lượng, tập trung vào RSI và MACD",
        indicator_config=IndicatorConfig(
            ma_short=8,          # MA ngắn
            ma_long=25,          # MA dài
            rsi_period=10,       # RSI nhạy cảm
            bb_std=1.5,          # Bollinger Bands trung bình
            macd_fast=8,         # MACD nhanh
            macd_slow=21,        # MACD chậm
            macd_signal=7,       # MACD signal
            obv_enabled=True,    # Bật OBV
            ichimoku_enabled=False  # Tắt Ichimoku
        ),
        scoring_config=ScoringConfig(
            strong_threshold=60.0,      # Ngưỡng trung bình
            medium_threshold=20.0,
            buy_strong_threshold=-60.0,
            sell_strong_threshold=60.0,
            context_multipliers={
                "uptrend_buy": 2.5,
                "uptrend_sell": 0.4,
                "downtrend_sell": 2.5,
                "downtrend_buy": 0.4,
                "sideways": 0.7
            }
        ),
        min_score_threshold=12.0,   # Ngưỡng trung bình
        lookback_days=60            # Thời gian trung bình
    )
    
    configs = {
        "scalping": scalping_config,
        "swing": swing_config,
        "position": position_config,
        "momentum": momentum_config
    }
    
    print(f"Đã tạo {len(configs)} cấu hình:")
    for name, config in configs.items():
        print(f"- {name}: {config.name}")
        print(f"  {config.description}")
        print(f"  Ngưỡng: {config.min_score_threshold}, Thời gian: {config.lookback_days} ngày")
    
    return configs

def test_configurations():
    """Kiểm thử các cấu hình"""
    
    configs = create_custom_configs()
    symbol = "PDR"
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=120)
    
    print(f"\n=== Kiểm thử cấu hình ===")
    print(f"Mã: {symbol}")
    print(f"Thời gian: {start_date} đến {end_date}")
    
    results = {}
    
    for name, config in configs.items():
        print(f"\n--- {name.upper()} ---")
        print(f"Tên: {config.name}")
        print(f"Mô tả: {config.description}")
        
        try:
            engine = AnalysisEngine(config)
            result = engine.analyze_symbol(
                symbol=symbol,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat()
            )
            
            results[name] = {
                'success': True,
                'signals_count': len(result.signals),
                'data_points': result.data_info['total_rows'],
                'summary': result.signal_summary
            }
            
            print(f"✅ Thành công: {len(result.signals)} tín hiệu")
            
            if result.signals:
                summary = result.signal_summary
                print(f"  - Mua: {summary['buy_signals']}, Bán: {summary['sell_signals']}")
                print(f"  - Mạnh: {summary['strong_signals']}, Trung bình: {summary['medium_signals']}")
                print(f"  - Điểm TB: {summary['avg_score']:.2f}")
                
                # Tín hiệu gần nhất
                latest = result.signals[-1]
                print(f"  - Gần nhất: {latest.timestamp.date()} - {latest.action.value} {latest.strength.value}")
            
        except Exception as e:
            results[name] = {
                'success': False,
                'error': str(e)
            }
            print(f"❌ Lỗi: {e}")
    
    return results

def compare_configurations():
    """So sánh các cấu hình"""
    
    results = test_configurations()
    
    print(f"\n=== So sánh cấu hình ===")
    
    # Tạo bảng so sánh
    print(f"{'Cấu hình':<15} {'Tín hiệu':<10} {'Mua':<5} {'Bán':<5} {'Mạnh':<5} {'Điểm TB':<10}")
    print("-" * 70)
    
    for name, result in results.items():
        if result['success']:
            summary = result['summary']
            print(f"{name:<15} {result['signals_count']:<10} {summary['buy_signals']:<5} {summary['sell_signals']:<5} {summary['strong_signals']:<5} {summary['avg_score']:<10.2f}")
        else:
            print(f"{name:<15} {'LỖI':<10} {'-':<5} {'-':<5} {'-':<5} {'-':<10}")
    
    # Phân tích
    print(f"\n=== Phân tích ===")
    
    successful_results = {k: v for k, v in results.items() if v['success']}
    
    if successful_results:
        # Cấu hình có nhiều tín hiệu nhất
        most_signals = max(successful_results.items(), key=lambda x: x[1]['signals_count'])
        print(f"Nhiều tín hiệu nhất: {most_signals[0]} ({most_signals[1]['signals_count']} tín hiệu)")
        
        # Cấu hình có ít tín hiệu nhất
        least_signals = min(successful_results.items(), key=lambda x: x[1]['signals_count'])
        print(f"Ít tín hiệu nhất: {least_signals[0]} ({least_signals[1]['signals_count']} tín hiệu)")
        
        # Cấu hình có điểm trung bình cao nhất
        highest_score = max(successful_results.items(), key=lambda x: x[1]['summary']['avg_score'])
        print(f"Điểm cao nhất: {highest_score[0]} ({highest_score[1]['summary']['avg_score']:.2f})")
        
        # Cấu hình có nhiều tín hiệu mạnh nhất
        most_strong = max(successful_results.items(), key=lambda x: x[1]['summary']['strong_signals'])
        print(f"Nhiều tín hiệu mạnh nhất: {most_strong[0]} ({most_strong[1]['summary']['strong_signals']} tín hiệu)")
    
    return results

def save_configurations():
    """Lưu cấu hình ra file"""
    
    configs = create_custom_configs()
    
    print(f"\n=== Lưu cấu hình ===")
    
    # Lưu từng cấu hình
    for name, config in configs.items():
        filename = f"config_{name}.json"
        filepath = os.path.join(os.path.dirname(__file__), filename)
        
        # Chuyển đổi cấu hình thành dict
        config_dict = {
            'name': config.name,
            'description': config.description,
            'indicator_config': config.indicator_config.to_dict(),
            'scoring_config': config.scoring_config.to_dict(),
            'min_score_threshold': config.min_score_threshold,
            'lookback_days': config.lookback_days
        }
        
        # Lưu file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, ensure_ascii=False, indent=2)
        
        print(f"Đã lưu: {filename}")
    
    # Lưu tất cả cấu hình
    all_configs = {}
    for name, config in configs.items():
        all_configs[name] = {
            'name': config.name,
            'description': config.description,
            'indicator_config': config.indicator_config.to_dict(),
            'scoring_config': config.scoring_config.to_dict(),
            'min_score_threshold': config.min_score_threshold,
            'lookback_days': config.lookback_days
        }
    
    all_configs_path = os.path.join(os.path.dirname(__file__), "all_configs.json")
    with open(all_configs_path, 'w', encoding='utf-8') as f:
        json.dump(all_configs, f, ensure_ascii=False, indent=2)
    
    print(f"Đã lưu tất cả: all_configs.json")
    
    return list(configs.keys())

def load_configurations():
    """Tải cấu hình từ file"""
    
    print(f"\n=== Tải cấu hình ===")
    
    all_configs_path = os.path.join(os.path.dirname(__file__), "all_configs.json")
    
    if not os.path.exists(all_configs_path):
        print("Không tìm thấy file cấu hình")
        return {}
    
    try:
        with open(all_configs_path, 'r', encoding='utf-8') as f:
            configs_dict = json.load(f)
        
        print(f"Đã tải {len(configs_dict)} cấu hình:")
        
        loaded_configs = {}
        for name, config_dict in configs_dict.items():
            # Tạo lại cấu hình
            config = AnalysisConfig(
                name=config_dict['name'],
                description=config_dict['description'],
                indicator_config=IndicatorConfig(**config_dict['indicator_config']),
                scoring_config=ScoringConfig(**config_dict['scoring_config']),
                min_score_threshold=config_dict['min_score_threshold'],
                lookback_days=config_dict['lookback_days']
            )
            
            loaded_configs[name] = config
            print(f"- {name}: {config.name}")
        
        return loaded_configs
        
    except Exception as e:
        print(f"Lỗi tải cấu hình: {e}")
        return {}

def optimize_configuration():
    """Tối ưu cấu hình"""
    
    print(f"\n=== Tối ưu cấu hình ===")
    
    # Cấu hình cơ sở
    base_config = AnalysisConfig()
    
    # Thử nghiệm các tham số khác nhau
    test_params = {
        'ma_short': [5, 10, 15, 20],
        'ma_long': [30, 50, 100, 200],
        'rsi_period': [7, 14, 21, 28],
        'min_score_threshold': [5.0, 10.0, 15.0, 20.0, 25.0]
    }
    
    symbol = "PDR"
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=90)
    
    print(f"Mã: {symbol}")
    print(f"Thời gian: {start_date} đến {end_date}")
    
    best_config = None
    best_score = 0
    best_params = {}
    
    # Thử nghiệm từng tham số
    for param_name, param_values in test_params.items():
        print(f"\n--- Thử nghiệm {param_name} ---")
        
        param_best_score = 0
        param_best_value = None
        
        for value in param_values:
            try:
                # Tạo cấu hình thử nghiệm
                if param_name == 'ma_short':
                    test_config = AnalysisConfig(
                        indicator_config=IndicatorConfig(ma_short=value, ma_long=base_config.indicator_config.ma_long),
                        scoring_config=base_config.scoring_config,
                        min_score_threshold=base_config.min_score_threshold,
                        lookback_days=base_config.lookback_days
                    )
                elif param_name == 'ma_long':
                    test_config = AnalysisConfig(
                        indicator_config=IndicatorConfig(ma_short=base_config.indicator_config.ma_short, ma_long=value),
                        scoring_config=base_config.scoring_config,
                        min_score_threshold=base_config.min_score_threshold,
                        lookback_days=base_config.lookback_days
                    )
                elif param_name == 'rsi_period':
                    test_config = AnalysisConfig(
                        indicator_config=IndicatorConfig(rsi_period=value),
                        scoring_config=base_config.scoring_config,
                        min_score_threshold=base_config.min_score_threshold,
                        lookback_days=base_config.lookback_days
                    )
                elif param_name == 'min_score_threshold':
                    test_config = AnalysisConfig(
                        indicator_config=base_config.indicator_config,
                        scoring_config=base_config.scoring_config,
                        min_score_threshold=value,
                        lookback_days=base_config.lookback_days
                    )
                
                # Chạy phân tích
                engine = AnalysisEngine(test_config)
                result = engine.analyze_symbol(
                    symbol=symbol,
                    start_date=start_date.isoformat(),
                    end_date=end_date.isoformat()
                )
                
                # Tính điểm (số tín hiệu * điểm trung bình)
                if result.signals:
                    score = len(result.signals) * result.signal_summary['avg_score']
                else:
                    score = 0
                
                print(f"  {value}: {len(result.signals)} tín hiệu, điểm: {score:.2f}")
                
                if score > param_best_score:
                    param_best_score = score
                    param_best_value = value
                
                if score > best_score:
                    best_score = score
                    best_config = test_config
                    best_params = {param_name: value}
                
            except Exception as e:
                print(f"  {value}: Lỗi - {e}")
        
        print(f"  Tốt nhất: {param_best_value} (điểm: {param_best_score:.2f})")
    
    print(f"\n=== Kết quả tối ưu ===")
    if best_config:
        print(f"Điểm tốt nhất: {best_score:.2f}")
        print(f"Tham số: {best_params}")
        print(f"Cấu hình: {best_config.name}")
    else:
        print("Không tìm thấy cấu hình tối ưu")
    
    return best_config, best_params

def main():
    """Hàm chính"""
    
    print("=== Ví dụ quản lý cấu hình ===")
    
    try:
        # 1. Tạo cấu hình tùy chỉnh
        configs = create_custom_configs()
        
        # 2. Kiểm thử cấu hình
        results = test_configurations()
        
        # 3. So sánh cấu hình
        comparison = compare_configurations()
        
        # 4. Lưu cấu hình
        saved_configs = save_configurations()
        
        # 5. Tải cấu hình
        loaded_configs = load_configurations()
        
        # 6. Tối ưu cấu hình
        best_config, best_params = optimize_configuration()
        
        print("\n=== Hoàn thành ===")
        print("Tất cả ví dụ quản lý cấu hình đã chạy thành công!")
        
    except Exception as e:
        print(f"Lỗi: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
