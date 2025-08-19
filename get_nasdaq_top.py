#!/usr/bin/env python3
"""
Get top NASDAQ stocks by market cap and trading volume
Uses yfinance library to fetch real-time market data
"""

import yfinance as yf
import pandas as pd
from datetime import datetime


def get_top_nasdaq_stocks(limit=20):
    """Get top NASDAQ stocks by market cap and volume"""

    # Popular NASDAQ tickers (top companies by market cap)
    nasdaq_tickers = [
        "AAPL",
        "MSFT",
        "GOOGL",
        "GOOG",
        "AMZN",
        "TSLA",
        "NVDA",
        "META",
        "AVGO",
        "COST",
        "NFLX",
        "ADBE",
        "AMD",
        "PEP",
        "INTC",
        "CSCO",
        "TMUS",
        "CMCSA",
        "TXN",
        "QCOM",
        "AMGN",
        "HON",
        "INTU",
        "AMAT",
        "ADI",
        "BKNG",
        "MU",
        "LRCX",
        "ADP",
        "MDLZ",
        "ISRG",
        "GILD",
        "VRTX",
        "REGN",
        "FISV",
        "CSX",
        "ATVI",
        "CHTR",
        "MAR",
        "ILMN",
        "SBUX",
        "PANW",
        "ORLY",
        "MNST",
        "KLAC",
        "SNPS",
        "CDNS",
        "FTNT",
        "MELI",
        "DXCM",
        "KDP",
        "NXPI",
        "EXC",
        "ASML",
        "CTAS",
        "MCHP",
        "PAYX",
        "AZN",
        "BIIB",
        "ROST",
        "ODFL",
        "LULU",
        "WDAY",
        "DLTR",
        "IDXX",
        "TTWO",
        "CPRT",
        "CSGP",
        "FAST",
        "MRNA",
        "DDOG",
        "TEAM",
        "ZM",
        "DOCU",
        "OKTA",
        "TWLO",
        "SNOW",
        "CRWD",
        "NET",
        "PLTR",
        "SQ",
        "ROKU",
        "UBER",
        "LYFT",
        "ABNB",
        "DASH",
        "PINS",
        "SNAP",
        "SHOP",
        "CRSR",
        "NIO",
        "XPEV",
        "LI",
        "LCID",
        "RBLX",
        "COIN",
        "HOOD",
        "RIVN",
        "BYND",
        "PTON",
        "ZM",
        "DOCU",
        "OKTA",
        "TWLO",
    ]

    print("🚀 Fetching NASDAQ market data...")

    stocks_data = []

    for ticker in nasdaq_tickers[:limit]:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            # Get current price and volume
            current_data = stock.history(period="1d", interval="1m")
            if not current_data.empty:
                current_price = current_data["Close"].iloc[-1]
                volume = current_data["Volume"].iloc[-1]
            else:
                current_price = info.get(
                    "currentPrice", info.get("regularMarketPrice", 0)
                )
                volume = info.get("volume", 0)

            stock_info = {
                "Symbol": ticker,
                "Company": info.get("longName", "N/A"),
                "Current Price": f"${current_price:.2f}" if current_price else "N/A",
                "Market Cap": (
                    f"${info.get('marketCap', 0):,.0f}"
                    if info.get("marketCap")
                    else "N/A"
                ),
                "Volume": f"{volume:,}" if volume else "N/A",
                "Change %": (
                    f"{info.get('regularMarketChangePercent', 0):.2f}%"
                    if info.get("regularMarketChangePercent")
                    else "N/A"
                ),
                "Sector": info.get("sector", "N/A"),
                "Industry": info.get("industry", "N/A"),
            }

            stocks_data.append(stock_info)
            print(
                f"✅ {ticker}: {stock_info['Current Price']} ({stock_info['Change %']})"
            )

        except Exception as e:
            print(f"❌ Error fetching {ticker}: {e}")

    return stocks_data


def display_top_stocks():
    """Display top NASDAQ stocks in a formatted table"""

    print("\n" + "=" * 80)
    print("📈 TOP NASDAQ STOCKS - REAL-TIME DATA")
    print("=" * 80)
    print(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 80)

    stocks = get_top_nasdaq_stocks(25)

    if not stocks:
        print("❌ No data available")
        return

    # Sort by market cap (descending)
    try:
        stocks_sorted = sorted(
            stocks,
            key=lambda x: (
                float(x["Market Cap"].replace("$", "").replace(",", ""))
                if x["Market Cap"] != "N/A"
                else 0
            ),
            reverse=True,
        )
    except:
        stocks_sorted = stocks

    # Display as table
    print(
        f"{'Rank':<4} {'Symbol':<6} {'Company':<25} {'Price':<10} {'Change %':<10} {'Volume':<12} {'Market Cap':<15}"
    )
    print("-" * 90)

    for i, stock in enumerate(stocks_sorted[:20], 1):
        company_name = (
            stock["Company"][:24] if len(stock["Company"]) > 24 else stock["Company"]
        )
        print(
            f"{i:<4} {stock['Symbol']:<6} {company_name:<25} {stock['Current Price']:<10} "
            f"{stock['Change %']:<10} {stock['Volume']:<12} {stock['Market Cap']:<15}"
        )

    print("-" * 90)
    print("💡 Data provided by Yahoo Finance via yfinance")


if __name__ == "__main__":
    try:
        import yfinance as yf
    except ImportError:
        print("📦 Installing yfinance...")
        import subprocess
        import sys

        subprocess.check_call([sys.executable, "-m", "pip", "install", "yfinance"])
        import yfinance as yf

    display_top_stocks()
