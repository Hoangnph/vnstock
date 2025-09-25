/**
 * Advanced Signal Analysis for Stock Trading
 * Analyzes multiple technical indicators to generate buy/sell signals
 */

function analyzeSignals(priceChange, volume, rsi, macdHist, foreignNet, avgVolume) {
  let buySignals = 0;
  let sellSignals = 0;
  
  // Price signal
  if (priceChange > 0) buySignals++;
  else if (priceChange < 0) sellSignals++;
  
  // Volume signal (higher volume = stronger signal)
  if (volume > avgVolume * 1.2) {
    if (priceChange > 0) buySignals++;
    else if (priceChange < 0) sellSignals++;
  }
  
  // RSI signal
  if (rsi < 30) buySignals++; // oversold = buy
  else if (rsi > 70) sellSignals++; // overbought = sell
  
  // MACD signal
  if (macdHist > 0.05) buySignals++; // positive MACD = buy
  else if (macdHist < -0.05) sellSignals++; // negative MACD = sell
  
  // Foreign trading signal
  if (foreignNet > 0) buySignals++; // foreign buying = buy
  else if (foreignNet < 0) sellSignals++; // foreign selling = sell
  
  // Determine final signal
  if (buySignals >= 3) return { 
    color: '#16a34a', 
    signal: 'BUY', 
    strength: buySignals,
    confidence: buySignals / 5
  };
  else if (sellSignals >= 3) return { 
    color: '#ef4444', 
    signal: 'SELL', 
    strength: sellSignals,
    confidence: sellSignals / 5
  };
  else return { 
    color: '#6b7280', 
    signal: 'NEUTRAL', 
    strength: Math.max(buySignals, sellSignals),
    confidence: Math.max(buySignals, sellSignals) / 5
  };
}

function calculateAverageVolume(volumeArray, currentIndex, lookbackPeriod = 10) {
  const startIndex = Math.max(0, currentIndex - lookbackPeriod);
  const endIndex = currentIndex + 1;
  const slice = volumeArray.slice(startIndex, endIndex);
  return slice.reduce((a, b) => a + b, 0) / slice.length;
}

function getSignalDescription(signalAnalysis) {
  const { signal, strength, confidence } = signalAnalysis;
  
  if (signal === 'BUY') {
    if (strength >= 4) return 'Strong Buy Signal';
    else if (strength === 3) return 'Buy Signal';
  } else if (signal === 'SELL') {
    if (strength >= 4) return 'Strong Sell Signal';
    else if (strength === 3) return 'Sell Signal';
  }
  
  return 'Neutral Signal';
}

// Export functions for use in HTML
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    analyzeSignals,
    calculateAverageVolume,
    getSignalDescription
  };
}
