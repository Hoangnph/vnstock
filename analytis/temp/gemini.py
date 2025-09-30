# -*- coding: utf-8 -*-
"""
File: trading_signals_analyzer.py
Tác giả: Gemini
Ngày tạo: 30-09-2025
Mô tả:
    Đây là module trung tâm, chứa toàn bộ logic để phân tích dữ liệu giá chứng khoán,
    tính toán các chỉ báo kỹ thuật, quét tín hiệu giao dịch, và đưa ra khuyến nghị
    cuối cùng dựa trên một hệ thống chấm điểm có thể cấu hình. Module được thiết kế
    để có thể dễ dàng tinh chỉnh (tuning) thông qua một dictionary config.
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Dict, Any

# ==============================================================================
# PHẦN 0: BỘ CẤU HÌNH MẶC ĐỊNH CHO THUẬT TOÁN
# ==============================================================================

DEFAULT_CONFIG: Dict[str, Any] = {
    # Các tham số cho đường trung bình động (Moving Average)
    "ma": {"short_period": 9, "long_period": 50},
    # Các tham số cho chỉ số sức mạnh tương đối (Relative Strength Index)
    "rsi": {"period": 14, "overbought": 70, "oversold": 30},
    # Các tham số cho chỉ báo MACD
    "macd": {"fast_period": 12, "slow_period": 26, "signal_period": 9},
    # Các tham số cho dải băng Bollinger (Bollinger Bands)
    "bb": {"period": 20, "std_dev": 2},
    # Các tham số cho mây Ichimoku (Ichimoku Cloud)
    "ichimoku": {"tenkan_period": 9, "kijun_period": 26, "senkou_b_period": 52},
    # Các tham số liên quan đến khối lượng giao dịch
    "volume": {"avg_period": 20, "spike_multiplier": 1.8},
    # Các tham số cho chỉ báo OBV (On-Balance Volume)
    "obv": {"divergence_lookback": 30},
    # Các tham số cho tín hiệu thắt cổ chai (Squeeze)
    "squeeze": {"lookback_period": 120},
    
    # (MỚI) CÔNG TẮC BẬT/TẮT CÁC NHÓM CHỈ BÁO PHÂN TÍCH
    # Thay đổi các giá trị này thành False để bỏ qua một nhóm tín hiệu trong phân tích
    "indicator_switches": {
        "use_ma_crossover": True,           # Tín hiệu Giao cắt Vàng/Chết (MA9/MA50)
        "use_macd_crossover": True,         # Tín hiệu MACD cắt đường Signal
        "use_rsi_engulfing_combo": True,    # Tín hiệu kết hợp Nến Engulfing và RSI
        "use_bb_squeeze": True,             # Tín hiệu thắt cổ chai Bollinger Squeeze
        "use_obv_divergence": True,         # Tín hiệu phân kỳ OBV (dòng tiền)
        "use_ichimoku_context": True,       # Sử dụng Ichimoku làm bộ lọc/xác nhận xu hướng
    },

    # Cấu hình cho hệ thống chấm điểm và đưa ra khuyến nghị
    # --- GIẢI THÍCH CHI TIẾT CÁCH TÍNH ĐIỂM ---
    # 1. Điểm cơ bản: Mỗi tín hiệu (MUA/BÁN) được tìm thấy sẽ được gán một điểm số
    #    cơ bản dựa vào 'weights'. Ví dụ: tín hiệu MUA MẠNH sẽ có 3 điểm MUA.
    # 2. Điều chỉnh theo bối cảnh: Nếu 'use_ichimoku_context' là True, tổng điểm
    #    MUA/BÁN sẽ được nhân với hệ số 'context_multipliers' dựa trên xu hướng
    #    chung do Ichimoku xác định. Nếu False, các hệ số này sẽ bị bỏ qua.
    # 3. Chuẩn hóa điểm cuối cùng: Điểm sau khi điều chỉnh được đưa về thang
    #    -100 (MUA CỰC MẠNH) đến 100 (BÁN CỰC MẠNH).
    # 4. Ra quyết định: Điểm cuối cùng được so sánh với các ngưỡng 'thresholds'
    #    để đưa ra hành động và mức độ khuyến nghị cuối cùng.
    "scoring": {
        "weights": {'STRONG': 3, 'MEDIUM': 2, 'WEAK': 1},
        "context_multipliers": {
            "uptrend_buy": 1.5,
            "uptrend_sell": 0.5,
            "downtrend_sell": 1.5,
            "downtrend_buy": 0.5,
            "sideways": 0.7
        },
        "thresholds": {
            "buy_strong": -75,
            "buy_medium": -25,
            "sell_medium": 25,
            "sell_strong": 75,
        }
    }
}

# ==============================================================================
# PHẦN 1: TÍNH TOÁN CÁC CHỈ BÁO KỸ THUẬT
# ==============================================================================

def add_technical_indicators(df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
    """Thêm tất cả các chỉ báo kỹ thuật cần thiết vào DataFrame.

    Hàm này nhận vào một DataFrame chứa dữ liệu OHLCV và một dictionary config,
    sau đó tính toán và thêm các cột chỉ báo kỹ thuật mới vào DataFrame đó.
    Các chỉ báo bao gồm: MA, RSI, MACD, Bollinger Bands, OBV, và Ichimoku Cloud.

    Args:
        df (pd.DataFrame): DataFrame đầu vào chứa các cột 'Open', 'High', 'Low',
                           'Close', 'Volume'.
        config (Dict[str, Any]): Dictionary chứa các tham số cấu hình cho
                                 từng chỉ báo.

    Returns:
        pd.DataFrame: DataFrame đã được thêm các cột chỉ báo kỹ thuật.
    """
    cfg_ma = config['ma']
    cfg_rsi = config['rsi']
    cfg_macd = config['macd']
    cfg_bb = config['bb']
    cfg_ichimoku = config['ichimoku']
    cfg_volume = config['volume']

    df['MA9'] = df['Close'].rolling(window=cfg_ma['short_period']).mean()
    df['MA50'] = df['Close'].rolling(window=cfg_ma['long_period']).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=cfg_rsi['period']).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=cfg_rsi['period']).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    exp1 = df['Close'].ewm(span=cfg_macd['fast_period'], adjust=False).mean()
    exp2 = df['Close'].ewm(span=cfg_macd['slow_period'], adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal_Line'] = df['MACD'].ewm(span=cfg_macd['signal_period'], adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['Signal_Line']
    
    df['Vol_Avg_20'] = df['Volume'].rolling(window=cfg_volume['avg_period']).mean()

    df['MA20'] = df['Close'].rolling(window=cfg_bb['period']).mean()
    df['BB_Std'] = df['Close'].rolling(window=cfg_bb['period']).std()
    df['BB_Upper'] = df['MA20'] + (df['BB_Std'] * cfg_bb['std_dev'])
    df['BB_Lower'] = df['MA20'] - (df['BB_Std'] * cfg_bb['std_dev'])
    df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / df['MA20']

    df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
    df['OBV_MA20'] = df['OBV'].rolling(window=cfg_volume['avg_period']).mean()

    high_9 = df['High'].rolling(cfg_ichimoku['tenkan_period']).max()
    low_9 = df['Low'].rolling(cfg_ichimoku['tenkan_period']).min()
    df['Tenkan_sen'] = (high_9 + low_9) / 2
    
    high_26 = df['High'].rolling(cfg_ichimoku['kijun_period']).max()
    low_26 = df['Low'].rolling(cfg_ichimoku['kijun_period']).min()
    df['Kijun_sen'] = (high_26 + low_26) / 2
    
    df['Senkou_Span_A'] = ((df['Tenkan_sen'] + df['Kijun_sen']) / 2).shift(cfg_ichimoku['kijun_period'])
    
    high_52 = df['High'].rolling(cfg_ichimoku['senkou_b_period']).max()
    low_52 = df['Low'].rolling(cfg_ichimoku['senkou_b_period']).min()
    df['Senkou_Span_B'] = ((high_52 + low_52) / 2).shift(cfg_ichimoku['kijun_period'])
    
    return df

# ==============================================================================
# PHẦN 2: NHẬN DIỆN CÁC MẪU HÌNH NẾN
# ==============================================================================

def is_bullish_engulfing(df: pd.DataFrame, i: int) -> bool:
    """Kiểm tra mẫu hình nến Bullish Engulfing (Nhấn chìm tăng).

    Lý thuyết: Mẫu hình này xảy ra trong một xu hướng giảm, bao gồm một nến giảm
    được theo sau bởi một nến tăng lớn hơn "nhấn chìm" hoàn toàn thân nến giảm
    trước đó. Nó báo hiệu sự đảo chiều tiềm năng từ giảm sang tăng.

    Args:
        df (pd.DataFrame): DataFrame chứa dữ liệu giá.
        i (int): Chỉ số (index) của ngày cần kiểm tra.

    Returns:
        bool: True nếu mẫu hình xuất hiện, ngược lại là False.
    """
    if i == 0: return False
    prev_row = df.iloc[i-1]
    curr_row = df.iloc[i]
    if prev_row['Close'] >= prev_row['Open'] or curr_row['Close'] <= curr_row['Open']:
        return False
    if curr_row['Open'] < prev_row['Close'] and curr_row['Close'] > prev_row['Open']:
        return True
    return False

def is_bearish_engulfing(df: pd.DataFrame, i: int) -> bool:
    """Kiểm tra mẫu hình nến Bearish Engulfing (Nhấn chìm giảm).

    Lý thuyết: Mẫu hình này xảy ra trong một xu hướng tăng, bao gồm một nến tăng
    được theo sau bởi một nến giảm lớn hơn "nhấn chìm" hoàn toàn thân nến tăng
    trước đó. Nó báo hiệu sự đảo chiều tiềm năng từ tăng sang giảm.

    Args:
        df (pd.DataFrame): DataFrame chứa dữ liệu giá.
        i (int): Chỉ số (index) của ngày cần kiểm tra.

    Returns:
        bool: True nếu mẫu hình xuất hiện, ngược lại là False.
    """
    if i == 0: return False
    prev_row = df.iloc[i-1]
    curr_row = df.iloc[i]
    if prev_row['Close'] <= prev_row['Open'] or curr_row['Close'] >= curr_row['Open']:
        return False
    if curr_row['Open'] > prev_row['Close'] and curr_row['Close'] < prev_row['Open']:
        return True
    return False

# ==============================================================================
# PHẦN 3: PHÂN TÍCH VECTOR ĐỘNG LỰC
# ==============================================================================

def analyze_momentum_phase(df: pd.DataFrame, i: int, config: Dict[str, Any]) -> Optional[str]:
    """Phân tích giai đoạn chuyển đổi động lượng dựa trên giá và khối lượng.

    Lý thuyết: Sử dụng các quy tắc heuristic để xác định các giai đoạn sớm của
    sự thay đổi động lượng, ví dụ như xu hướng giảm đang suy yếu do khối lượng
    cạn kiệt, hoặc xu hướng tăng đang chững lại.

    Args:
        df (pd.DataFrame): DataFrame chứa dữ liệu giá.
        i (int): Chỉ số của ngày cần phân tích.
        config (Dict[str, Any]): Dictionary cấu hình.

    Returns:
        Optional[str]: Một chuỗi mô tả giai đoạn động lượng, hoặc None nếu
                       không phát hiện được gì đặc biệt.
    """
    cfg_rsi = config['rsi']
    if i < 20: return "Không đủ dữ liệu để phân tích động lượng."
    recent_df = df.iloc[i-10:i+1]
    is_downtrend = df['MA9'].iloc[i] < df['MA50'].iloc[i]
    volume_drying_up = recent_df['Volume'].iloc[-5:].mean() < df['Vol_Avg_20'].iloc[i]
    if is_downtrend and volume_drying_up:
        return "Giai đoạn 1: Có dấu hiệu suy yếu giảm (khối lượng cạn kiệt)."
    is_uptrend = df['MA9'].iloc[i] > df['MA50'].iloc[i]
    price_stalling = (df['Close'].iloc[i] - df['Open'].iloc[i]) < (df['Close'].iloc[i-5:i].mean() - df['Open'].iloc[i-5:i].mean())
    if is_uptrend and price_stalling and df['RSI'].iloc[i] > (cfg_rsi['overbought'] - 5):
         return "Giai đoạn 1: Có dấu hiệu suy yếu tăng (đà tăng chững lại)."
    return None

# ==============================================================================
# PHẦN 4: THUẬT TOÁN QUÉT TÍN HIỆU
# ==============================================================================

def analyze_day(df: pd.DataFrame, i: int, config: Dict[str, Any]) -> List[Dict[str, str]]:
    """Phân tích và quét tất cả các tín hiệu riêng lẻ cho một ngày cụ thể.

    Hàm này duyệt qua các quy tắc đã được định nghĩa, tuân thủ các công tắc
    bật/tắt trong config['indicator_switches'].

    Args:
        df (pd.DataFrame): DataFrame chứa dữ liệu giá và các chỉ báo.
        i (int): Chỉ số của ngày cần phân tích.
        config (Dict[str, Any]): Dictionary cấu hình chứa các ngưỡng và tham số.

    Returns:
        List[Dict[str, str]]: Một danh sách các tín hiệu được tìm thấy.
    """
    cfg_rsi = config['rsi']
    cfg_volume = config['volume']
    cfg_squeeze = config['squeeze']
    cfg_obv = config['obv']
    switches = config.get('indicator_switches', {})

    notifications = []
    row = df.iloc[i]
    prev_row = df.iloc[i-1] if i > 0 else None
    if prev_row is None: return []

    # Quét tín hiệu kết hợp Nến Engulfing & RSI
    if switches.get('use_rsi_engulfing_combo', True):
        if is_bullish_engulfing(df, i) and row['RSI'] < cfg_rsi['oversold'] and row['Volume'] > row['Vol_Avg_20'] * cfg_volume['spike_multiplier']:
            notifications.append({'type': 'BUY', 'strength': 'STRONG', 'description': f"[MUA MẠNH - Hội tụ đáy]\n  - Dữ liệu: Nến Bullish Engulfing, RSI={row['RSI']:.2f}, KLGD tăng {row['Volume']/row['Vol_Avg_20']:.2f} lần."})
        if is_bearish_engulfing(df, i) and row['RSI'] > cfg_rsi['overbought'] and row['Volume'] > row['Vol_Avg_20'] * cfg_volume['spike_multiplier']:
            notifications.append({'type': 'SELL', 'strength': 'STRONG', 'description': f"[BÁN MẠNH - Hội tụ đỉnh]\n  - Dữ liệu: Nến Bearish Engulfing, RSI={row['RSI']:.2f}, KLGD tăng {row['Volume']/row['Vol_Avg_20']:.2f} lần."})

    # Quét tín hiệu MACD Crossover
    if switches.get('use_macd_crossover', True):
        if prev_row['MACD'] < prev_row['Signal_Line'] and row['MACD'] > row['Signal_Line'] and row['MACD'] < 0 and row['Close'] > row['MA50']:
            notifications.append({'type': 'BUY', 'strength': 'STRONG', 'description': f"[MUA MẠNH - Bùng nổ xu hướng mới]\n  - Dữ liệu: MACD cắt lên Signal dưới 0, Giá ({row['Close']:.2f}) vượt MA50 ({row['MA50']:.2f})."})
    
    # Quét tín hiệu MA Crossover (Golden Cross)
    if switches.get('use_ma_crossover', True):
        if prev_row['MA9'] < prev_row['MA50'] and row['MA9'] > row['MA50']:
            notifications.append({'type': 'BUY', 'strength': 'STRONG', 'description': f"[MUA MẠNH - Golden Cross]\n  - Dữ liệu: MA9 ({row['MA9']:.2f}) cắt lên MA50 ({row['MA50']:.2f})."})
    
    # Quét tín hiệu Bollinger Squeeze
    if switches.get('use_bb_squeeze', True):
        if i > cfg_squeeze['lookback_period'] and row['BB_Width'] <= df['BB_Width'].iloc[i-cfg_squeeze['lookback_period']:i].min() * 1.05:
             notifications.append({'type': 'WATCH', 'strength': 'MEDIUM', 'description': f"[CẢNH BÁO - Bollinger Squeeze]\n  - Dữ liệu: Độ rộng dải băng thu hẹp, báo hiệu sắp có biến động giá mạnh."})
    
    # Quét tín hiệu phân kỳ OBV
    if switches.get('use_obv_divergence', True):
        if i > cfg_obv['divergence_lookback']:
            lookback_df = df.iloc[i-cfg_obv['divergence_lookback']:i]
            price_trough_idx = lookback_df['Low'].idxmin()
            if not pd.isna(price_trough_idx) and row['Close'] < df.loc[price_trough_idx, 'Low'] * 0.99 and row['OBV'] > df.loc[price_trough_idx, 'OBV']:
                 notifications.append({'type': 'BUY', 'strength': 'STRONG', 'description': f"[MUA MẠNH - Phân kỳ dương OBV]\n  - Dữ liệu: Giá tạo đáy mới thấp hơn nhưng OBV tạo đáy cao hơn."})
            price_peak_idx = lookback_df['High'].idxmax()
            if not pd.isna(price_peak_idx) and row['Close'] > df.loc[price_peak_idx, 'High'] * 1.01 and row['OBV'] < df.loc[price_peak_idx, 'OBV']:
                 notifications.append({'type': 'SELL', 'strength': 'STRONG', 'description': f"[BÁN MẠNH - Phân kỳ âm OBV]\n  - Dữ liệu: Giá tạo đỉnh mới cao hơn nhưng OBV tạo đỉnh thấp hơn."})

    return notifications

# ==============================================================================
# PHẦN 5: HÀM PHÂN TÍCH BỐI CẢNH
# ==============================================================================

def analyze_ichimoku_context(df: pd.DataFrame, i: int, config: Dict[str, Any]) -> str:
    """Phân tích bối cảnh xu hướng dựa trên hệ thống Ichimoku.

    Lý thuyết: Ichimoku cung cấp một cái nhìn toàn diện về xu hướng. Một tín hiệu MUA
    sẽ đáng tin cậy hơn nhiều nếu nó xảy ra trong một bối cảnh xu hướng TĂNG MẠNH
    (giá trên mây, mây xanh, etc.). Ngược lại với tín hiệu BÁN.

    Args:
        df (pd.DataFrame): DataFrame chứa dữ liệu và chỉ báo Ichimoku.
        i (int): Chỉ số của ngày cần phân tích.
        config (Dict[str, Any]): Dictionary cấu hình.

    Returns:
        str: Một chuỗi mô tả trạng thái xu hướng chung.
    """
    cfg_ichimoku = config['ichimoku']
    if i < cfg_ichimoku['senkou_b_period']:
        return "Ichimoku: Không đủ dữ liệu."
    
    row = df.iloc[i]
    try:
        price_above_cloud = row['Close'] > row['Senkou_Span_A'] and row['Close'] > row['Senkou_Span_B']
        cloud_is_green = row['Senkou_Span_A'] > row['Senkou_Span_B']
        tenkan_above_kijun = row['Tenkan_sen'] > row['Kijun_sen']
        chikou_above_price_past = row['Close'] > df['Close'].iloc[i-cfg_ichimoku['kijun_period']] 
        if price_above_cloud and cloud_is_green and tenkan_above_kijun and chikou_above_price_past:
            return "Xác nhận Ichimoku: XU HƯỚNG TĂNG MẠNH."

        price_below_cloud = row['Close'] < row['Senkou_Span_A'] and row['Close'] < row['Senkou_Span_B']
        cloud_is_red = row['Senkou_Span_A'] < row['Senkou_Span_B']
        tenkan_below_kijun = row['Tenkan_sen'] < row['Kijun_sen']
        chikou_below_price_past = row['Close'] < df['Close'].iloc[i-cfg_ichimoku['kijun_period']]
        if price_below_cloud and cloud_is_red and tenkan_below_kijun and chikou_below_price_past:
            return "Xác nhận Ichimoku: XU HƯỚNG GIẢM MẠNH."
            
        if (row['Close'] > row['Senkou_Span_A'] and row['Close'] < row['Senkou_Span_B']) or \
           (row['Close'] < row['Senkou_Span_A'] and row['Close'] > row['Senkou_Span_B']):
            return "Xác nhận Ichimoku: TRẠNG THÁI SIDEWAYS (Giá trong mây)."
    except (IndexError, TypeError, ValueError):
        return "Ichimoku: Không đủ dữ liệu quá khứ cho ngày hiện tại."

    return "Xác nhận Ichimoku: TRẠNG THÁI TRUNG LẬP."

# ==============================================================================
# PHẦN 5B: PHÂN TÍCH CHUYỂN ĐỔI TÍN HIỆU
# ==============================================================================

def _get_daily_recommendation_state(df: pd.DataFrame, i: int, config: Dict[str, Any]) -> str:
    """Hàm trợ giúp nội bộ để lấy trạng thái khuyến nghị (MUA/BÁN/THEO DÕI) cho một ngày."""
    day_signals = analyze_day(df, i, config)
    
    switches = config.get('indicator_switches', {})
    ichimoku_context = "TRUNG LẬP"
    if switches.get('use_ichimoku_context', True):
        ichimoku_context = analyze_ichimoku_context(df, i, config)
    
    cfg_scoring = config['scoring']
    weights = cfg_scoring['weights']
    multipliers = cfg_scoring['context_multipliers']
    thresholds = cfg_scoring['thresholds']
    
    buy_score_base, sell_score_base = 0.0, 0.0
    for signal in day_signals:
        strength = signal.get('strength', 'WEAK')
        base_weight = weights.get(strength, 1)
        if signal['type'] == 'BUY':
            buy_score_base += base_weight
        elif signal['type'] == 'SELL':
            sell_score_base += base_weight

    buy_score, sell_score = buy_score_base, sell_score_base
    if switches.get('use_ichimoku_context', True):
        if "TĂNG MẠNH" in ichimoku_context:
            buy_score *= multipliers['uptrend_buy']
            sell_score *= multipliers['uptrend_sell']
        elif "GIẢM MẠNH" in ichimoku_context:
            sell_score *= multipliers['downtrend_sell']
            buy_score *= multipliers['downtrend_buy']
        elif "SIDEWAYS" in ichimoku_context:
            buy_score *= multipliers['sideways']
            sell_score *= multipliers['sideways']

    total_potential_score = buy_score + sell_score
    final_score = 0 if total_potential_score == 0 else ((sell_score - buy_score) / total_potential_score) * 100
    
    if final_score <= thresholds['buy_medium']:
        return "MUA"
    elif final_score >= thresholds['sell_medium']:
        return "BÁN"
    else:
        return "THEO DÕI"

def analyze_signal_transition(df: pd.DataFrame, i: int, config: Dict[str, Any], lookback_period: int = 10) -> Optional[str]:
    """Phân tích N phiên gần nhất để tìm sự chuyển đổi trạng thái tín hiệu MUA/BÁN."""
    if i < lookback_period:
        return None

    daily_states = [_get_daily_recommendation_state(df, day_idx, config) for day_idx in range(i - lookback_period + 1, i + 1)]

    for j in range(len(daily_states) - 1, 0, -1):
        current_state = daily_states[j]
        previous_state = daily_states[j-1]
        
        if current_state in ["MUA", "BÁN"] and previous_state in ["MUA", "BÁN"] and current_state != previous_state:
            days_ago = (len(daily_states) - 1) - (j - 1)
            return f"Ghi chú: Tín hiệu đã chuyển trạng thái từ {previous_state} sang {current_state} cách đây {days_ago} phiên."
            
    return None

# ==============================================================================
# PHẦN 6: HÀM TỔNG HỢP VÀ ĐƯA RA KHUYẾN NGHỊ
# ==============================================================================

def generate_final_recommendation(signals: List[Dict[str, str]], ichimoku_context: str, config: Dict[str, Any]) -> List[str]:
    """Tổng hợp các tín hiệu, chấm điểm và đưa ra một khuyến nghị hành động cuối cùng."""
    cfg_scoring = config['scoring']
    weights = cfg_scoring['weights']
    multipliers = cfg_scoring['context_multipliers']
    thresholds = cfg_scoring['thresholds']
    switches = config.get('indicator_switches', {})
    
    buy_score, sell_score = 0.0, 0.0
    score_details = []

    buy_multiplier, sell_multiplier = 1.0, 1.0
    if switches.get('use_ichimoku_context', True):
        if "TĂNG MẠNH" in ichimoku_context:
            buy_multiplier = multipliers['uptrend_buy']
            sell_multiplier = multipliers['uptrend_sell']
        elif "GIẢM MẠNH" in ichimoku_context:
            sell_multiplier = multipliers['downtrend_sell']
            buy_multiplier = multipliers['downtrend_buy']
        elif "SIDEWAYS" in ichimoku_context:
            buy_multiplier = sell_multiplier = multipliers['sideways']

    for signal in signals:
        strength = signal.get('strength', 'WEAK')
        base_weight = weights.get(strength, 1)
        description = signal['description'].split('\n')[0]

        if signal['type'] == 'BUY':
            signal_contribution = base_weight * buy_multiplier
            buy_score += signal_contribution
            score_details.append({"description": description, "contribution": f"+{signal_contribution:.2f} điểm MUA"})
        elif signal['type'] == 'SELL':
            signal_contribution = base_weight * sell_multiplier
            sell_score += signal_contribution
            score_details.append({"description": description, "contribution": f"+{signal_contribution:.2f} điểm BÁN"})

    total_potential_score = buy_score + sell_score
    final_score = 0 if total_potential_score == 0 else ((sell_score - buy_score) / total_potential_score) * 100
    
    final_action, final_strength = "THEO DÕI", "TRUNG LẬP"

    if final_score <= thresholds['buy_strong']:
        final_action, final_strength = "MUA", "RẤT MẠNH"
    elif final_score <= thresholds['buy_medium']:
        final_action, final_strength = "MUA", "TRUNG BÌNH"
    elif final_score >= thresholds['sell_strong']:
        final_action, final_strength = "BÁN", "RẤT MẠNH"
    elif final_score >= thresholds['sell_medium']:
        final_action, final_strength = "BÁN", "TRUNG BÌNH"

    recommendation = [
        f"ĐIỂM KHUYẾN NGHỊ: {final_score:.2f} / 100  (-100: Mua, 100: Bán)",
        f"HÀNH ĐỘNG KHUYẾN NGHỊ: {final_action}",
        f"Mức độ: {final_strength}"
    ]
    
    if score_details:
        recommendation.append("\n" + "-"*15 + " PHÂN TÍCH ĐIỂM ĐÓNG GÓP " + "-"*15)
        for detail in score_details:
             recommendation.append(f"  - {detail['description']}: {detail['contribution']}")
        
        recommendation.append("\nCăn cứ dựa trên các tín hiệu chính:")
        basis_signals = [detail['description'] for detail in score_details]
        recommendation.extend(['  - ' + s for s in basis_signals])
    else:
        recommendation.append("Căn cứ: Không có tín hiệu giao dịch rõ ràng trong phiên hôm nay.")
        
    return recommendation

# ==============================================================================
# PHẦN 7: HÀM PHÂN TÍCH TỔNG HỢP
# ==============================================================================

def analyze_ticker(df: pd.DataFrame, ticker: str, config: Optional[Dict[str, Any]] = None) -> List[str]:
    """Hàm chính để chạy toàn bộ quy trình phân tích cho một mã cổ phiếu."""
    if config is None:
        config = DEFAULT_CONFIG

    min_data_points = config['ichimoku']['senkou_b_period'] + config['ichimoku']['kijun_period'] + 10 # Thêm 10 cho lookback
    if len(df) < min_data_points:
        return [f"Không đủ dữ liệu (cần ít nhất {min_data_points} phiên) để phân tích đầy đủ."]

    df_with_indicators = add_technical_indicators(df.copy(), config)
    
    final_notifications = []
    
    last_day_index = len(df_with_indicators) - 1
    last_day = df_with_indicators.index[last_day_index]
    
    day_signals_structured = analyze_day(df_with_indicators, last_day_index, config)
    
    if day_signals_structured:
        final_notifications.append(f"Tín hiệu chi tiết ngày {last_day.strftime('%d-%m-%Y')} cho mã {ticker}:")
        for signal in day_signals_structured:
            final_notifications.append(f"  -> {signal['description']}")
        final_notifications.append("-" * 50)

    momentum_context = analyze_momentum_phase(df_with_indicators, last_day_index, config)
    if momentum_context:
        final_notifications.append(f"Bối cảnh động lượng: {momentum_context}")
    
    switches = config.get('indicator_switches', {})
    ichimoku_confirmation = "Xác nhận Ichimoku: Đã tắt."
    if switches.get('use_ichimoku_context', True):
        ichimoku_confirmation = analyze_ichimoku_context(df_with_indicators, last_day_index, config)
    final_notifications.append(ichimoku_confirmation)
    
    transition_note = analyze_signal_transition(df_with_indicators, last_day_index, config)
    if transition_note:
        final_notifications.append(transition_note)

    recommendation_output = generate_final_recommendation(day_signals_structured, ichimoku_confirmation, config)
    
    final_notifications.append("\n" + "="*25 + " TỔNG HỢP VÀ KHUYẾN NGHỊ " + "="*25)
    final_notifications.extend(recommendation_output)
    final_notifications.append("="*75)
        
    return final_notifications

