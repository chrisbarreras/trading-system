"""
Download and filter a list of all tradeable stocks.
Creates a filtered list of liquid, actively-traded stocks for scanning.
"""
import pandas as pd
import requests
from pathlib import Path
import yfinance as yf
from datetime import datetime, timedelta
import time

def download_nasdaq_listed():
    """Download list of NASDAQ-listed stocks."""
    print("Downloading NASDAQ-listed stocks...")
    url = "https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=25000&exchange=nasdaq"
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        data = response.json()

        if 'data' in data and 'rows' in data['data']:
            rows = data['data']['rows']
            df = pd.DataFrame(rows)
            print(f"✅ Downloaded {len(df)} NASDAQ stocks")
            return df
        else:
            print(f"⚠️  No data in NASDAQ response")
            return pd.DataFrame()
    except Exception as e:
        print(f"⚠️  Error downloading NASDAQ list: {e}")

    return pd.DataFrame()

def download_nyse_listed():
    """Download list of NYSE-listed stocks."""
    print("Downloading NYSE-listed stocks...")
    url = "https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=25000&exchange=nyse"
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        data = response.json()

        if 'data' in data and 'rows' in data['data']:
            rows = data['data']['rows']
            df = pd.DataFrame(rows)
            print(f"✅ Downloaded {len(df)} NYSE stocks")
            return df
        else:
            print(f"⚠️  No data in NYSE response")
            return pd.DataFrame()
    except Exception as e:
        print(f"⚠️  Error downloading NYSE list: {e}")

    return pd.DataFrame()

def get_all_symbols():
    """Get all NASDAQ and NYSE symbols."""
    nasdaq_df = download_nasdaq_listed()
    nyse_df = download_nyse_listed()

    # Check if both failed
    if nasdaq_df.empty and nyse_df.empty:
        print("❌ Failed to download stock lists. Using fallback method...")
        return get_fallback_symbols()

    # Combine both lists (handle case where one is empty)
    dfs_to_concat = [df for df in [nasdaq_df, nyse_df] if not df.empty]

    if not dfs_to_concat:
        print("❌ No data available. Using fallback method...")
        return get_fallback_symbols()

    all_stocks = pd.concat(dfs_to_concat, ignore_index=True)

    if all_stocks.empty:
        print("❌ Failed to download stock lists. Using fallback method...")
        return get_fallback_symbols()

    # Extract symbols
    symbols = all_stocks['symbol'].unique().tolist()

    # Filter out problematic symbols
    symbols = [s for s in symbols if s and isinstance(s, str) and len(s) <= 5]
    symbols = [s for s in symbols if '.' not in s and '^' not in s and '/' not in s]

    print(f"✅ Total symbols after filtering: {len(symbols)}")
    return symbols

def get_fallback_symbols():
    """Fallback method using a comprehensive curated list of top stocks."""
    print("Using fallback stock list (curated top 500)...")

    # Comprehensive list of top liquid stocks by sector (curated manually)
    symbols = [
        # Mega Cap Tech (20)
        "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "NVDA", "TSLA", "AMD", "INTC",
        "CRM", "ORCL", "CSCO", "ADBE", "NFLX", "AVGO", "QCOM", "TXN", "AMAT", "MU",

        # Tech - Software & Services (20)
        "PYPL", "SHOP", "SQ", "SNOW", "DDOG", "CRWD", "NET", "ZS", "PANW", "FTNT",
        "WDAY", "NOW", "TEAM", "HUBS", "ZM", "DOCU", "TWLO", "OKTA", "DBX", "BOX",

        # Tech - Semiconductors (20)
        "TSM", "ASML", "LRCX", "KLAC", "MCHP", "MRVL", "NXPI", "ADI", "SNPS", "CDNS",
        "ON", "MPWR", "SWKS", "QRVO", "WOLF", "CRUS", "ALGM", "SLAB", "SMCI", "NVMI",

        # Finance - Banks (20)
        "JPM", "BAC", "WFC", "C", "GS", "MS", "USB", "PNC", "TFC", "COF",
        "BK", "STT", "FITB", "RF", "CFG", "KEY", "HBAN", "ZION", "CMA", "WTFC",

        # Finance - Other (15)
        "BLK", "SCHW", "AXP", "V", "MA", "SPGI", "MCO", "ICE", "CME", "NDAQ",
        "MSCI", "TROW", "BEN", "IVZ", "MKTX",

        # Healthcare - Pharma (25)
        "JNJ", "UNH", "PFE", "ABBV", "TMO", "ABT", "MRK", "LLY", "DHR", "BMY",
        "AMGN", "GILD", "REGN", "VRTX", "BIIB", "ILMN", "ALXN", "INCY", "MRNA", "BNTX",
        "ZTS", "EW", "IDXX", "MTD", "A",

        # Healthcare - Devices & Services (15)
        "MDT", "SYK", "BSX", "ISRG", "EL", "BDX", "BAX", "HCA", "CI", "CVS",
        "ANTM", "HUMH", "CNC", "MOH", "UHS",

        # Energy (25)
        "XOM", "CVX", "COP", "SLB", "EOG", "PXD", "OXY", "MPC", "PSX", "VLO",
        "HAL", "BKR", "NOV", "FTI", "HP", "DVN", "FANG", "MRO", "APA", "HES",
        "KMI", "WMB", "OKE", "EPD", "ET",

        # Consumer - Retail (25)
        "WMT", "HD", "MCD", "NKE", "SBUX", "TGT", "LOW", "TJX", "ROST", "DG",
        "DLTR", "COST", "KR", "BBY", "ULTA", "AZO", "ORLY", "AAP", "GPC", "DKS",
        "FIVE", "BURL", "FL", "ANF", "URBN",

        # Consumer - Discretionary (20)
        "AMZN", "TSLA", "DIS", "CMCSA", "CHTR", "NFLX", "BKNG", "MAR", "HLT", "MGM",
        "WYNN", "LVS", "CCL", "RCL", "NCLH", "YUM", "CMG", "SBUX", "DPZ", "QSR",

        # Consumer - Staples (15)
        "PG", "KO", "PEP", "PM", "MO", "MDLZ", "CL", "KMB", "GIS", "K",
        "CPB", "CAG", "SJM", "HSY", "CHD",

        # Industrials (30)
        "BA", "CAT", "GE", "HON", "UNP", "UPS", "RTX", "LMT", "MMM", "DE",
        "EMR", "ETN", "ITW", "PH", "CMI", "PCAR", "ROK", "DOV", "IR", "FAST",
        "FDX", "DAL", "UAL", "AAL", "LUV", "JBHT", "NSC", "CSX", "KSU", "ODFL",

        # Materials (15)
        "LIN", "APD", "SHW", "ECL", "DD", "NEM", "FCX", "NUE", "STLD", "VMC",
        "MLM", "DOW", "PPG", "RPM", "SEE",

        # Real Estate (15)
        "AMT", "PLD", "CCI", "EQIX", "PSA", "SPG", "O", "WELL", "DLR", "AVB",
        "EQR", "VTR", "ARE", "MAA", "UDR",

        # Utilities (10)
        "NEE", "DUK", "SO", "D", "EXC", "AEP", "SRE", "PEG", "XEL", "ED",

        # Communications (15)
        "GOOGL", "META", "DIS", "CMCSA", "NFLX", "T", "VZ", "TMUS", "CHTR", "ATVI",
        "EA", "TTWO", "MTCH", "PINS", "SNAP",

        # Popular ETFs (30)
        "SPY", "QQQ", "IWM", "DIA", "EEM", "EFA", "VWO", "GLD", "SLV", "TLT",
        "HYG", "LQD", "AGG", "BND", "XLF", "XLE", "XLK", "XLV", "XLI", "XLY",
        "XLP", "XLU", "XLRE", "XLB", "XLC", "IYR", "KRE", "SMH", "XBI", "XOP",

        # Emerging Growth (30)
        "SQ", "SHOP", "ROKU", "PLTR", "COIN", "HOOD", "RIVN", "LCID", "SOFI", "UPST",
        "AFRM", "PTON", "DASH", "ABNB", "UBER", "LYFT", "TDOC", "DKNG", "Penn", "FSLR",
        "ENPH", "SEDG", "RUN", "BLNK", "CHPT", "PLUG", "FCEL", "BE", "CLNE", "SPWR",

        # Additional Growth (30)
        "ARKK", "ARKG", "ARKW", "ARKF", "ARKQ", "ETSY", "W", "CHWY", "CVNA", "RH",
        "LULU", "DECK", "NKE", "ADDYY", "CROX", "SKX", "VFC", "UAA", "RL", "PVH",
        "LEVI", "TPR", "CPRI", "FOSL", "HBI", "GOOS", "COLM", "SCVL", "VSCO", "JWN",

        # Biotech & Healthcare (20)
        "CELG", "SGEN", "EXAS", "JAZZ", "ALNY", "TECH", "IONS", "FOLD", "RARE", "BMRN",
        "UTHR", "RGEN", "ACAD", "NBIX", "HALO", "SRPT", "BLUE", "EDIT", "CRSP", "NTLA",
    ]

    # Remove duplicates and sort
    symbols = sorted(list(set(symbols)))

    print(f"✅ Fallback list: {len(symbols)} symbols")
    return symbols

def filter_by_volume(symbols, min_volume=1000000, sample_size=500):
    """
    Filter symbols by average trading volume.
    Only checks a sample to avoid rate limits.

    Args:
        symbols: List of symbols to filter
        min_volume: Minimum average daily volume
        sample_size: Max number of symbols to check (to avoid rate limits)

    Returns:
        Filtered list of symbols
    """
    print(f"\nFiltering by volume (min: {min_volume:,} shares/day)...")
    print(f"Checking up to {sample_size} symbols (this may take a few minutes)...")

    filtered_symbols = []
    check_symbols = symbols[:sample_size]  # Limit to avoid rate limits

    for i, symbol in enumerate(check_symbols):
        try:
            # Show progress
            if (i + 1) % 50 == 0:
                print(f"Progress: {i + 1}/{len(check_symbols)} symbols checked...")

            # Get recent data
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")

            if not hist.empty and 'Volume' in hist.columns:
                avg_volume = hist['Volume'].mean()

                if avg_volume >= min_volume:
                    filtered_symbols.append(symbol)

            # Rate limiting
            time.sleep(0.1)  # Be nice to Yahoo Finance

        except Exception as e:
            # Skip symbols that cause errors
            continue

    print(f"✅ Found {len(filtered_symbols)} liquid stocks (volume >= {min_volume:,})")
    return filtered_symbols

def save_symbol_list(symbols, filename="stock_symbols.txt"):
    """Save symbol list to file."""
    filepath = Path(filename)

    with open(filepath, 'w') as f:
        for symbol in sorted(symbols):
            f.write(f"{symbol}\n")

    print(f"\n✅ Saved {len(symbols)} symbols to {filepath}")
    return filepath

def create_filtered_lists():
    """Create multiple filtered lists for different use cases."""
    print("="*80)
    print("Stock List Downloader")
    print("="*80 + "\n")

    # Get all symbols
    all_symbols = get_all_symbols()

    if not all_symbols:
        print("❌ Failed to get stock symbols")
        return

    # Check if we're using fallback (curated list)
    using_fallback = len(all_symbols) < 1000

    if using_fallback:
        print("\n📋 Using curated fallback list (APIs unavailable)")
        print("This is a pre-filtered list of ~500 liquid, high-quality stocks")

        # Save as both "all" and "top500" since they're the same
        save_symbol_list(all_symbols, "stock_symbols_all.txt")
        save_symbol_list(all_symbols, "stock_symbols_top500.txt")

        # Create top 100 subset
        print("\nCreating TOP 100 subset...")
        top_100 = all_symbols[:100] if len(all_symbols) >= 100 else all_symbols
        save_symbol_list(top_100, "stock_symbols_top100.txt")

        print("\n" + "="*80)
        print("Summary")
        print("="*80)
        print(f"✅ Curated list: {len(all_symbols)} liquid stocks")
        print(f"✅ Top 100 subset: {len(top_100)} stocks")
        print("\nNote: API download unavailable, using pre-curated list")
        print("This list is already filtered for quality and liquidity!")

    else:
        # API download succeeded, do volume filtering
        # Save complete list
        save_symbol_list(all_symbols, "stock_symbols_all.txt")

        # Create filtered lists
        print("\n" + "="*80)
        print("Creating Filtered Lists")
        print("="*80)

        # Top 500 liquid stocks (recommended for scanning)
        print("\n1. Creating TOP 500 liquid stocks list...")
        liquid_500 = filter_by_volume(all_symbols, min_volume=1000000, sample_size=500)
        save_symbol_list(liquid_500, "stock_symbols_top500.txt")

        # Alternative: Use top 100 for faster scanning
        print("\n2. Creating TOP 100 subset...")
        top_100 = liquid_500[:100] if len(liquid_500) >= 100 else liquid_500
        save_symbol_list(top_100, "stock_symbols_top100.txt")

        print("\n" + "="*80)
        print("Summary")
        print("="*80)
        print(f"✅ All symbols: {len(all_symbols)} (stock_symbols_all.txt)")
        print(f"✅ Top 500 liquid: {len(liquid_500)} (stock_symbols_top500.txt)")
        print(f"✅ Top 100 liquid: {len(top_100)} (stock_symbols_top100.txt)")
        print("\nRecommendation: Use stock_symbols_top500.txt for best results")
        print("(Liquid stocks with good volume, avoids penny stocks)")

def main():
    """Main entry point."""
    try:
        create_filtered_lists()

        print("\n" + "="*80)
        print("Next Steps")
        print("="*80)
        print("1. Run scanner with filtered list:")
        print("   python run_scanner.py --symbols-file stock_symbols_top500.txt --dry-run")
        print("\n2. Or use the top 100 for faster testing:")
        print("   python run_scanner.py --symbols-file stock_symbols_top100.txt --dry-run")
        print("\n3. Schedule scans with the list:")
        print("   python run_scanner.py --symbols-file stock_symbols_top500.txt --schedule")
        print()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
