"""
Indicator Engine - Pure Technical Indicator Calculations

This module provides a clean, modular approach to calculating technical indicators
without any scoring or signal generation logic. It focuses purely on mathematical
calculations of various technical indicators.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class IndicatorConfig:
    """Configuration for technical indicators"""
    # Moving Averages
    ma_short: int = 9
    ma_long: int = 50
    ma_medium: int = 20
    
    # RSI
    rsi_period: int = 14
    rsi_overbought: float = 70
    rsi_oversold: float = 30
    
    # MACD
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    
    # Bollinger Bands
    bb_period: int = 20
    bb_std: float = 2.0
    
    # Volume
    volume_avg_period: int = 20
    volume_spike_multiplier: float = 1.8
    
    # Ichimoku
    ichimoku_tenkan: int = 9
    ichimoku_kijun: int = 26
    ichimoku_senkou_b: int = 52
    
    # OBV
    obv_divergence_lookback: int = 30
    
    # Squeeze
    squeeze_lookback: int = 120


class IndicatorEngine:
    """
    Pure technical indicator calculation engine.
    
    This class focuses solely on calculating technical indicators without
    any scoring, signal generation, or interpretation logic.
    """
    
    def __init__(self, config: Optional[IndicatorConfig] = None):
        self.config = config or IndicatorConfig()
    
    def calculate_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all technical indicators for the given OHLCV data.
        
        Args:
            df: DataFrame with columns ['Open', 'High', 'Low', 'Close', 'Volume']
            
        Returns:
            DataFrame with original data plus all calculated indicators
        """
        if df.empty:
            logger.warning("Empty DataFrame provided to calculate_all_indicators")
            return df.copy()
        
        result_df = df.copy()
        
        try:
            # Moving Averages
            result_df = self._calculate_moving_averages(result_df)
            
            # RSI
            result_df = self._calculate_rsi(result_df)
            
            # MACD
            result_df = self._calculate_macd(result_df)
            
            # Bollinger Bands
            result_df = self._calculate_bollinger_bands(result_df)
            
            # Volume indicators
            result_df = self._calculate_volume_indicators(result_df)
            
            # Ichimoku Cloud
            result_df = self._calculate_ichimoku(result_df)
            
            # OBV
            result_df = self._calculate_obv(result_df)
            
            logger.info(f"Successfully calculated indicators for {len(result_df)} data points")
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            raise
        
        return result_df
    
    def _calculate_moving_averages(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate various moving averages"""
        df['MA9'] = df['Close'].rolling(window=self.config.ma_short).mean()
        df['MA20'] = df['Close'].rolling(window=self.config.ma_medium).mean()
        df['MA50'] = df['Close'].rolling(window=self.config.ma_long).mean()
        return df
    
    def _calculate_rsi(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate RSI (Relative Strength Index)"""
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.config.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.config.rsi_period).mean()
        
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        return df
    
    def _calculate_macd(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        ema_fast = df['Close'].ewm(span=self.config.macd_fast).mean()
        ema_slow = df['Close'].ewm(span=self.config.macd_slow).mean()
        
        df['MACD'] = ema_fast - ema_slow
        df['Signal_Line'] = df['MACD'].ewm(span=self.config.macd_signal).mean()
        df['MACD_Hist'] = df['MACD'] - df['Signal_Line']
        return df
    
    def _calculate_bollinger_bands(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Bollinger Bands"""
        sma = df['Close'].rolling(window=self.config.bb_period).mean()
        std = df['Close'].rolling(window=self.config.bb_period).std()
        
        df['BB_Upper'] = sma + (std * self.config.bb_std)
        df['BB_Lower'] = sma - (std * self.config.bb_std)
        df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / sma
        df['BB_Std'] = std
        return df
    
    def _calculate_volume_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate volume-based indicators"""
        df['Vol_Avg_20'] = df['Volume'].rolling(window=self.config.volume_avg_period).mean()
        df['Volume_Spike'] = df['Volume'] / df['Vol_Avg_20']
        return df
    
    def _calculate_ichimoku(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Ichimoku Cloud indicators"""
        # Tenkan-sen (Conversion Line)
        high_9 = df['High'].rolling(window=self.config.ichimoku_tenkan).max()
        low_9 = df['Low'].rolling(window=self.config.ichimoku_tenkan).min()
        df['Tenkan_sen'] = (high_9 + low_9) / 2
        
        # Kijun-sen (Base Line)
        high_26 = df['High'].rolling(window=self.config.ichimoku_kijun).max()
        low_26 = df['Low'].rolling(window=self.config.ichimoku_kijun).min()
        df['Kijun_sen'] = (high_26 + low_26) / 2
        
        # Senkou Span A (Leading Span A)
        df['Senkou_Span_A'] = ((df['Tenkan_sen'] + df['Kijun_sen']) / 2).shift(self.config.ichimoku_kijun)
        
        # Senkou Span B (Leading Span B)
        high_52 = df['High'].rolling(window=self.config.ichimoku_senkou_b).max()
        low_52 = df['Low'].rolling(window=self.config.ichimoku_senkou_b).min()
        df['Senkou_Span_B'] = ((high_52 + low_52) / 2).shift(self.config.ichimoku_kijun)
        
        return df
    
    def _calculate_obv(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate OBV (On-Balance Volume)"""
        # Ensure Close column is numeric
        close_numeric = pd.to_numeric(df['Close'], errors='coerce')
        volume_numeric = pd.to_numeric(df['Volume'], errors='coerce')
        
        # Calculate price change
        price_change = close_numeric.diff()
        
        # Calculate OBV
        obv = np.where(price_change > 0, volume_numeric,
                      np.where(price_change < 0, -volume_numeric, 0))
        df['OBV'] = np.cumsum(obv)
        
        # OBV Moving Average
        df['OBV_MA20'] = df['OBV'].rolling(window=self.config.ma_medium).mean()
        
        return df
    
    def get_indicator_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Get a summary of all calculated indicators for the latest data point.
        
        Args:
            df: DataFrame with calculated indicators
            
        Returns:
            Dictionary with indicator values for the latest row
        """
        if df.empty:
            return {}
        
        latest_row = df.iloc[-1]
        
        summary = {
            'price': {
                'open': float(latest_row.get('Open', 0)),
                'high': float(latest_row.get('High', 0)),
                'low': float(latest_row.get('Low', 0)),
                'close': float(latest_row.get('Close', 0)),
                'volume': int(latest_row.get('Volume', 0))
            },
            'moving_averages': {
                'ma9': float(latest_row.get('MA9', 0)) if pd.notna(latest_row.get('MA9')) else None,
                'ma20': float(latest_row.get('MA20', 0)) if pd.notna(latest_row.get('MA20')) else None,
                'ma50': float(latest_row.get('MA50', 0)) if pd.notna(latest_row.get('MA50')) else None
            },
            'momentum': {
                'rsi': float(latest_row.get('RSI', 0)) if pd.notna(latest_row.get('RSI')) else None,
                'macd': float(latest_row.get('MACD', 0)) if pd.notna(latest_row.get('MACD')) else None,
                'macd_signal': float(latest_row.get('Signal_Line', 0)) if pd.notna(latest_row.get('Signal_Line')) else None,
                'macd_hist': float(latest_row.get('MACD_Hist', 0)) if pd.notna(latest_row.get('MACD_Hist')) else None
            },
            'volatility': {
                'bb_upper': float(latest_row.get('BB_Upper', 0)) if pd.notna(latest_row.get('BB_Upper')) else None,
                'bb_lower': float(latest_row.get('BB_Lower', 0)) if pd.notna(latest_row.get('BB_Lower')) else None,
                'bb_width': float(latest_row.get('BB_Width', 0)) if pd.notna(latest_row.get('BB_Width')) else None
            },
            'volume': {
                'volume': int(latest_row.get('Volume', 0)),
                'volume_avg': float(latest_row.get('Vol_Avg_20', 0)) if pd.notna(latest_row.get('Vol_Avg_20')) else None,
                'volume_spike': float(latest_row.get('Volume_Spike', 0)) if pd.notna(latest_row.get('Volume_Spike')) else None,
                'obv': float(latest_row.get('OBV', 0)) if pd.notna(latest_row.get('OBV')) else None,
                'obv_ma20': float(latest_row.get('OBV_MA20', 0)) if pd.notna(latest_row.get('OBV_MA20')) else None
            },
            'ichimoku': {
                'tenkan': float(latest_row.get('Tenkan_sen', 0)) if pd.notna(latest_row.get('Tenkan_sen')) else None,
                'kijun': float(latest_row.get('Kijun_sen', 0)) if pd.notna(latest_row.get('Kijun_sen')) else None,
                'senkou_a': float(latest_row.get('Senkou_Span_A', 0)) if pd.notna(latest_row.get('Senkou_Span_A')) else None,
                'senkou_b': float(latest_row.get('Senkou_Span_B', 0)) if pd.notna(latest_row.get('Senkou_Span_B')) else None
            }
        }
        
        return summary
    
    def validate_data(self, df: pd.DataFrame) -> bool:
        """
        Validate that the input DataFrame has the required columns and data.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        
        if df.empty:
            logger.warning("DataFrame is empty")
            return False
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"Missing required columns: {missing_columns}")
            return False
        
        # Check for sufficient data points
        min_required = max(self.config.ichimoku_senkou_b, self.config.ma_long, self.config.bb_period)
        if len(df) < min_required:
            logger.warning(f"Insufficient data points: {len(df)} < {min_required}")
            return False
        
        return True
