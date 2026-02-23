"""
Technical analysis strategies for signal generation.
"""
import pandas as pd
import pandas_ta as ta
from typing import Dict, List, Optional


class TechnicalStrategy:
    """Base class for technical analysis strategies."""

    def __init__(self, name: str):
        self.name = name

    def analyze(self, df: pd.DataFrame, symbol: str) -> Dict:
        """
        Analyze price data and generate signals.

        Args:
            df: DataFrame with OHLCV data
            symbol: Stock symbol

        Returns:
            Dict with signal information
        """
        raise NotImplementedError


class RSIStrategy(TechnicalStrategy):
    """RSI-based mean reversion strategy."""

    def __init__(self, period: int = 14, oversold: int = 30, overbought: int = 70):
        super().__init__("RSI Strategy")
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    def analyze(self, df: pd.DataFrame, symbol: str) -> Dict:
        """Generate signals based on RSI levels."""
        # Calculate RSI
        df['rsi'] = ta.rsi(df['close'], length=self.period)

        # Get latest values
        latest = df.iloc[-1]
        prev = df.iloc[-2]

        result = {
            'symbol': symbol,
            'price': float(latest['close']),
            'rsi': float(latest['rsi']),
            'signals': [],
            'action': None
        }

        # BUY: RSI crosses up through oversold threshold (was below, now above)
        if prev['rsi'] < self.oversold and latest['rsi'] >= self.oversold:
            result['signals'].append(
                f"RSI crossed up through oversold ({prev['rsi']:.1f} -> {latest['rsi']:.1f}, threshold={self.oversold})"
            )
            result['action'] = 'buy'

        # SELL: RSI crosses down through overbought threshold (was above, now below)
        elif prev['rsi'] > self.overbought and latest['rsi'] <= self.overbought:
            result['signals'].append(
                f"RSI crossed down through overbought ({prev['rsi']:.1f} -> {latest['rsi']:.1f}, threshold={self.overbought})"
            )
            result['action'] = 'sell'

        return result


class MACDStrategy(TechnicalStrategy):
    """MACD crossover strategy."""

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        super().__init__("MACD Strategy")
        self.fast = fast
        self.slow = slow
        self.signal = signal

    def analyze(self, df: pd.DataFrame, symbol: str) -> Dict:
        """Generate signals based on MACD crossovers."""
        # Calculate MACD
        macd = ta.macd(df['close'], fast=self.fast, slow=self.slow, signal=self.signal)
        df['macd'] = macd[f'MACD_{self.fast}_{self.slow}_{self.signal}']
        df['macd_signal'] = macd[f'MACDs_{self.fast}_{self.slow}_{self.signal}']
        df['macd_hist'] = macd[f'MACDh_{self.fast}_{self.slow}_{self.signal}']

        # Get latest values
        latest = df.iloc[-1]
        prev = df.iloc[-2]

        result = {
            'symbol': symbol,
            'price': float(latest['close']),
            'macd': float(latest['macd']),
            'macd_signal': float(latest['macd_signal']),
            'signals': [],
            'action': None
        }

        # Bullish crossover
        if prev['macd'] <= prev['macd_signal'] and latest['macd'] > latest['macd_signal']:
            result['signals'].append("MACD bullish crossover")
            result['action'] = 'buy'

        # Bearish crossover
        elif prev['macd'] >= prev['macd_signal'] and latest['macd'] < latest['macd_signal']:
            result['signals'].append("MACD bearish crossover")
            result['action'] = 'sell'

        return result


class MovingAverageCrossStrategy(TechnicalStrategy):
    """Moving average crossover strategy (Golden Cross / Death Cross)."""

    def __init__(self, fast_period: int = 50, slow_period: int = 200):
        super().__init__("MA Cross Strategy")
        self.fast_period = fast_period
        self.slow_period = slow_period

    def analyze(self, df: pd.DataFrame, symbol: str) -> Dict:
        """Generate signals based on MA crossovers."""
        # Calculate moving averages
        df['sma_fast'] = ta.sma(df['close'], length=self.fast_period)
        df['sma_slow'] = ta.sma(df['close'], length=self.slow_period)

        # Get latest values
        latest = df.iloc[-1]
        prev = df.iloc[-2]

        result = {
            'symbol': symbol,
            'price': float(latest['close']),
            'sma_fast': float(latest['sma_fast']),
            'sma_slow': float(latest['sma_slow']),
            'signals': [],
            'action': None
        }

        # Golden Cross (bullish)
        if prev['sma_fast'] <= prev['sma_slow'] and latest['sma_fast'] > latest['sma_slow']:
            result['signals'].append(f"Golden Cross (SMA{self.fast_period} > SMA{self.slow_period})")
            result['action'] = 'buy'

        # Death Cross (bearish)
        elif prev['sma_fast'] >= prev['sma_slow'] and latest['sma_fast'] < latest['sma_slow']:
            result['signals'].append(f"Death Cross (SMA{self.fast_period} < SMA{self.slow_period})")
            result['action'] = 'sell'

        return result


class BollingerBandsStrategy(TechnicalStrategy):
    """Bollinger Bands mean reversion strategy."""

    def __init__(self, period: int = 20, std: float = 2.0):
        super().__init__("Bollinger Bands Strategy")
        self.period = period
        self.std = std

    def analyze(self, df: pd.DataFrame, symbol: str) -> Dict:
        """Generate signals based on Bollinger Bands."""
        # Calculate Bollinger Bands
        # Use prefix matching instead of exact f-string names because pandas_ta
        # may format the std suffix differently (e.g. "2.0" vs "2") across versions.
        bbands = ta.bbands(df['close'], length=self.period, std=self.std)
        upper_col = next(c for c in bbands.columns if c.startswith('BBU_'))
        middle_col = next(c for c in bbands.columns if c.startswith('BBM_'))
        lower_col = next(c for c in bbands.columns if c.startswith('BBL_'))
        df['bb_upper'] = bbands[upper_col]
        df['bb_middle'] = bbands[middle_col]
        df['bb_lower'] = bbands[lower_col]

        # Get latest values
        latest = df.iloc[-1]

        result = {
            'symbol': symbol,
            'price': float(latest['close']),
            'bb_upper': float(latest['bb_upper']),
            'bb_lower': float(latest['bb_lower']),
            'signals': [],
            'action': None
        }

        # Price near lower band (potential buy)
        if latest['close'] <= latest['bb_lower'] * 1.01:  # Within 1%
            result['signals'].append("Price at lower Bollinger Band (oversold)")
            result['action'] = 'buy'

        # Price near upper band (potential sell)
        elif latest['close'] >= latest['bb_upper'] * 0.99:  # Within 1%
            result['signals'].append("Price at upper Bollinger Band (overbought)")
            result['action'] = 'sell'

        return result


class ComboStrategy(TechnicalStrategy):
    """
    Combination strategy requiring multiple confirmations.
    More conservative - reduces false signals.
    """

    def __init__(self):
        super().__init__("Combo Strategy")
        self.rsi = RSIStrategy()
        self.macd = MACDStrategy()

    def analyze(self, df: pd.DataFrame, symbol: str) -> Dict:
        """Generate signals requiring both RSI and MACD confirmation."""
        rsi_result = self.rsi.analyze(df, symbol)
        macd_result = self.macd.analyze(df, symbol)

        result = {
            'symbol': symbol,
            'price': float(df.iloc[-1]['close']),
            'rsi': rsi_result['rsi'],
            'macd': macd_result['macd'],
            'signals': [],
            'action': None
        }

        # Require both RSI and MACD to agree
        if rsi_result['action'] == 'buy' and macd_result['action'] == 'buy':
            result['signals'] = rsi_result['signals'] + macd_result['signals']
            result['action'] = 'buy'

        elif rsi_result['action'] == 'sell' and macd_result['action'] == 'sell':
            result['signals'] = rsi_result['signals'] + macd_result['signals']
            result['action'] = 'sell'

        return result
