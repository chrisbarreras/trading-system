"""
Market scanner that generates trading signals and sends them to the trading system.
"""
import requests
import time
from datetime import datetime
from typing import List, Optional
from scanner.data_source import DataSource, YahooFinanceSource
from scanner.strategies import (
    TechnicalStrategy,
    RSIStrategy,
    MACDStrategy,
    MovingAverageCrossStrategy,
    BollingerBandsStrategy,
    ComboStrategy
)


class MarketScanner:
    """
    Scans multiple symbols using technical analysis strategies.
    Sends trading signals to the trading system via webhook.
    """

    def __init__(
        self,
        symbols: List[str],
        data_source: DataSource,
        api_url: str = "http://localhost:8080/webhook/tradingview",
        strategy: Optional[TechnicalStrategy] = None,
        min_signals: int = 1,
        period: str = "3mo",
        interval: str = "1d"
    ):
        """
        Initialize market scanner.

        Args:
            symbols: List of symbols to scan
            data_source: Data source instance (Yahoo, Alpaca, etc.)
            api_url: Trading system webhook URL
            strategy: Technical strategy to use (default: RSI)
            min_signals: Minimum number of signals required to trigger trade
            period: Historical data period
            interval: Bar interval
        """
        self.symbols = symbols
        self.data_source = data_source
        self.api_url = api_url
        self.strategy = strategy or RSIStrategy()
        self.min_signals = min_signals
        self.period = period
        self.interval = interval

    def scan(self) -> List[dict]:
        """
        Scan all symbols and return signals.

        Returns:
            List of signal dictionaries
        """
        print(f"\n{'='*80}")
        print(f"Market Scan - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Strategy: {self.strategy.name}")
        print(f"Symbols: {', '.join(self.symbols)}")
        print(f"{'='*80}\n")

        all_signals = []

        for symbol in self.symbols:
            try:
                # Get market data
                df = self.data_source.get_bars(
                    symbol,
                    period=self.period,
                    interval=self.interval
                )

                # Analyze with strategy
                result = self.strategy.analyze(df, symbol)

                # Display results
                self._display_result(result)

                # Check if we should trigger a trade
                if result['action'] and len(result['signals']) >= self.min_signals:
                    all_signals.append(result)

                # Rate limiting (be nice to APIs)
                time.sleep(0.5)

            except Exception as e:
                print(f"❌ Error scanning {symbol}: {e}\n")

        return all_signals

    def scan_and_execute(self, dry_run: bool = False) -> List[dict]:
        """
        Scan markets and execute trades.

        Args:
            dry_run: If True, show signals but don't execute trades

        Returns:
            List of executed trades
        """
        signals = self.scan()

        if not signals:
            print("\n📊 No trading signals found.\n")
            return []

        print(f"\n{'='*80}")
        print(f"Found {len(signals)} trading signal(s)")
        print(f"{'='*80}\n")

        executed = []

        for signal in signals:
            if dry_run:
                print(f"🔔 [DRY RUN] Would {signal['action'].upper()} {signal['symbol']} @ ${signal['price']:.2f}")
            else:
                success = self._execute_trade(signal)
                if success:
                    executed.append(signal)

        return executed

    def _execute_trade(self, signal: dict) -> bool:
        """
        Send trade signal to trading system.

        Args:
            signal: Signal dictionary

        Returns:
            True if successful
        """
        try:
            payload = {
                "ticker": signal['symbol'],
                "action": signal['action'],
                "strategy": "momentum",  # Map to your trading system strategy
                "price": signal['price']
            }

            response = requests.post(
                self.api_url,
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✅ Trade triggered: {signal['action'].upper()} {signal['symbol']}")
                print(f"   Response: {result}\n")
                return True
            else:
                print(f"❌ Trade failed: {response.status_code} - {response.text}\n")
                return False

        except Exception as e:
            print(f"❌ Error executing trade for {signal['symbol']}: {e}\n")
            return False

    def _display_result(self, result: dict):
        """Display analysis result in a readable format."""
        symbol = result['symbol']
        price = result['price']

        # Determine color/emoji based on signal
        if result['action'] == 'buy':
            indicator = '🟢 BUY'
        elif result['action'] == 'sell':
            indicator = '🔴 SELL'
        else:
            indicator = '⚪ HOLD'

        print(f"{indicator:12} {symbol:6} @ ${price:7.2f}", end="")

        # Show indicator values
        if 'rsi' in result:
            print(f" | RSI: {result['rsi']:5.1f}", end="")
        if 'macd' in result:
            print(f" | MACD: {result['macd']:6.2f}", end="")
        if 'sma_fast' in result:
            print(f" | SMA{result.get('fast', 50)}: {result['sma_fast']:.2f}", end="")

        print()

        # Show signal reasons
        if result['signals']:
            for sig in result['signals']:
                print(f"           └─ {sig}")

        print()


def create_scanner(
    symbols: List[str],
    strategy_name: str = "rsi",
    data_source: str = "yahoo"
) -> MarketScanner:
    """
    Factory function to create a configured scanner.

    Args:
        symbols: List of symbols to scan
        strategy_name: Strategy to use (rsi, macd, ma_cross, bb, combo)
        data_source: Data source to use (yahoo, alpaca)

    Returns:
        Configured MarketScanner instance
    """
    # Select data source
    if data_source.lower() == "yahoo":
        ds = YahooFinanceSource()
    elif data_source.lower() == "alpaca":
        # You'd need to provide API keys
        from scanner.data_source import AlpacaDataSource
        from app.config import get_settings
        settings = get_settings()
        ds = AlpacaDataSource(settings.alpaca_api_key, settings.alpaca_secret_key)
    else:
        raise ValueError(f"Unknown data source: {data_source}")

    # Select strategy
    strategies = {
        "rsi": RSIStrategy(),
        "macd": MACDStrategy(),
        "ma_cross": MovingAverageCrossStrategy(fast_period=50, slow_period=200),
        "bb": BollingerBandsStrategy(),
        "combo": ComboStrategy()
    }

    strategy = strategies.get(strategy_name.lower())
    if not strategy:
        raise ValueError(f"Unknown strategy: {strategy_name}. Options: {list(strategies.keys())}")

    return MarketScanner(
        symbols=symbols,
        data_source=ds,
        strategy=strategy
    )
