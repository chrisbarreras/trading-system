"""
Data source abstraction layer.
Makes it easy to swap between Yahoo Finance, Alpaca, or other providers.
"""
from abc import ABC, abstractmethod
import pandas as pd
from typing import Optional
from datetime import datetime, timedelta


class DataSource(ABC):
    """Abstract base class for market data sources."""

    @abstractmethod
    def get_bars(self, symbol: str, period: str = "1mo", interval: str = "1d") -> pd.DataFrame:
        """
        Get historical price bars.

        Args:
            symbol: Stock symbol (e.g., "AAPL")
            period: Time period (e.g., "1d", "5d", "1mo", "3mo", "1y")
            interval: Bar interval (e.g., "1m", "5m", "1h", "1d")

        Returns:
            DataFrame with columns: open, high, low, close, volume
        """
        pass

    @abstractmethod
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current/latest price for a symbol."""
        pass


class YahooFinanceSource(DataSource):
    """Yahoo Finance data source (free, unlimited)."""

    def __init__(self):
        """Initialize Yahoo Finance data source."""
        import yfinance as yf
        self.yf = yf

    def get_bars(self, symbol: str, period: str = "1mo", interval: str = "1d") -> pd.DataFrame:
        """
        Get historical bars from Yahoo Finance.

        Args:
            symbol: Stock symbol
            period: Valid periods: 1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max
            interval: Valid intervals: 1m,2m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo,3mo

        Returns:
            DataFrame with lowercase column names
        """
        try:
            df = self.yf.download(symbol, period=period, interval=interval, progress=False)

            if df.empty:
                raise ValueError(f"No data returned for {symbol}")

            # Normalize column names to lowercase
            # Handle both Index and MultiIndex cases
            if isinstance(df.columns, pd.MultiIndex):
                # For MultiIndex, get the first level (the actual column names)
                df.columns = df.columns.get_level_values(0).str.lower()
            else:
                df.columns = df.columns.str.lower()

            return df

        except Exception as e:
            raise ValueError(f"Error fetching data for {symbol}: {str(e)}")

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price from Yahoo Finance."""
        try:
            ticker = self.yf.Ticker(symbol)
            info = ticker.info

            # Try different price fields in order of preference
            for field in ['currentPrice', 'regularMarketPrice', 'previousClose']:
                if field in info and info[field]:
                    return float(info[field])

            # Fallback: get latest close from recent data
            df = self.get_bars(symbol, period="1d", interval="1m")
            if not df.empty:
                return float(df['close'].iloc[-1])

            return None

        except Exception as e:
            print(f"Error getting current price for {symbol}: {e}")
            return None


class AlpacaDataSource(DataSource):
    """Alpaca data source (free tier or Data+ subscription)."""

    def __init__(self, api_key: str, secret_key: str):
        """
        Initialize Alpaca data source.

        Args:
            api_key: Alpaca API key
            secret_key: Alpaca secret key
        """
        from alpaca.data.historical import StockHistoricalDataClient
        self.client = StockHistoricalDataClient(api_key, secret_key)

    def get_bars(self, symbol: str, period: str = "1mo", interval: str = "1d") -> pd.DataFrame:
        """
        Get historical bars from Alpaca.

        Args:
            symbol: Stock symbol
            period: Period string (e.g., "1mo", "3mo", "1y")
            interval: Interval string (e.g., "1m", "1h", "1d")

        Returns:
            DataFrame with lowercase column names
        """
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame

        # Convert period to days
        period_map = {
            "1d": 1, "5d": 5, "1mo": 30, "3mo": 90,
            "6mo": 180, "1y": 365, "2y": 730
        }
        days = period_map.get(period, 30)

        # Convert interval to TimeFrame
        interval_map = {
            "1m": TimeFrame.Minute,
            "5m": TimeFrame(5, "Min"),
            "15m": TimeFrame(15, "Min"),
            "1h": TimeFrame.Hour,
            "1d": TimeFrame.Day,
        }
        timeframe = interval_map.get(interval, TimeFrame.Day)

        # Create request
        request = StockBarsRequest(
            symbol_or_symbols=[symbol],
            timeframe=timeframe,
            start=datetime.now() - timedelta(days=days)
        )

        # Get bars
        bars = self.client.get_stock_bars(request)
        df = bars.df

        # Reset index to get timestamp as column
        df = df.reset_index()
        df = df.set_index('timestamp')

        return df

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get latest price from Alpaca."""
        try:
            df = self.get_bars(symbol, period="1d", interval="1m")
            if not df.empty:
                return float(df['close'].iloc[-1])
            return None
        except Exception as e:
            print(f"Error getting current price for {symbol}: {e}")
            return None
