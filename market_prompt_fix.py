#!/usr/bin/env python3
"""
Script to improve market prompt selection and whitelist configuration
This script provides better guidance for market analysts using the --market flag
"""

import os
import json
from pathlib import Path


def check_current_whitelist():
    """Check current whitelist configuration"""
    whitelist_file = Path.home() / ".janito" / "url_whitelist.json"

    if whitelist_file.exists():
        try:
            with open(whitelist_file, "r") as f:
                data = json.load(f)
                return data.get("allowed_sites", [])
        except Exception as e:
            print(f"❌ Error reading whitelist: {e}")
            return []
    return []


def setup_market_sources():
    """Set up recommended market data sources"""

    print("🎯 Setting up Market Analyst profile with recommended data sources...")

    # Recommended sources for market analysis
    market_sources = [
        "sec.gov",
        "fred.stlouisfed.org",
        "tradingview.com",
        "investing.com",
        "finance.yahoo.com",
        "alphavantage.co",
        "financialmodelingprep.com",
        "twelvedata.com",
    ]

    # Create whitelist file
    whitelist_dir = Path.home() / ".janito"
    whitelist_dir.mkdir(exist_ok=True)

    whitelist_file = whitelist_dir / "url_whitelist.json"

    config = {
        "allowed_sites": market_sources,
        "configured_for": "market_analysis",
        "last_updated": "2024-12-19",
    }

    try:
        with open(whitelist_file, "w") as f:
            json.dump(config, f, indent=2)
        print(f"✅ Market data sources configured: {len(market_sources)} sites")
        for source in market_sources:
            print(f"   • {source}")
        return True
    except Exception as e:
        print(f"❌ Error setting up whitelist: {e}")
        return False


def show_usage_guide():
    """Show improved usage guide for market analysts"""

    print("\n" + "=" * 60)
    print("📈 MARKET ANALYST USAGE GUIDE")
    print("=" * 60)

    print("\n🔧 Quick Setup:")
    print("1. Configure data sources:")
    print(
        "   janito --set allowed_sites=sec.gov,fred.stlouisfed.org,tradingview.com,investing.com"
    )

    print("\n2. Use Market Analyst profile:")
    print("   janito --market 'Analyze AAPL stock performance'")
    print("   janito --profile 'Market Analyst' 'List top NASDAQ stocks'")

    print("\n3. Interactive mode:")
    print("   janito --market")
    print("   Then: 'What are the best stocks to buy tomorrow?'")

    print("\n📊 Available Data Sources:")
    sources = [
        ("SEC EDGAR", "sec.gov", "Company filings, 10-K, 10-Q reports"),
        (
            "Federal Reserve",
            "fred.stlouisfed.org",
            "Economic indicators, interest rates",
        ),
        ("TradingView", "tradingview.com", "Real-time quotes, technical analysis"),
        ("Investing.com", "investing.com", "Global indices, market data"),
        ("Yahoo Finance", "finance.yahoo.com", "Stock prices, historical data"),
        ("Alpha Vantage", "alphavantage.co", "Free API for stocks and forex"),
    ]

    for name, domain, description in sources:
        print(f"   • {name:<15} ({domain:<20}) - {description}")

    print("\n⚡ Advanced Usage:")
    print("   # Add specific sources")
    print("   janito --add-allowed-site financialmodelingprep.com")

    print("   # Check current configuration")
    print("   janito --list-allowed-sites")

    print("   # Interactive security management")
    print("   janito --market")
    print("   /security allowed-sites list")
    print("   /security allowed-sites add new-site.com")


def main():
    """Main function to improve market prompt experience"""

    print("🚀 Janito Market Analyst Profile Enhancement")
    print("-" * 50)

    # Check current configuration
    current_sites = check_current_whitelist()

    if current_sites:
        print(f"📋 Current whitelist: {len(current_sites)} sites")
        for site in current_sites[:5]:  # Show first 5
            print(f"   • {site}")
        if len(current_sites) > 5:
            print(f"   ... and {len(current_sites) - 5} more")
    else:
        print("⚠️  No whitelist configured - all sites allowed")

    # Offer to set up recommended sources
    if not current_sites or len(current_sites) < 3:
        response = input("\n🤖 Set up recommended market data sources? (y/n): ")
        if response.lower() in ["y", "yes"]:
            setup_market_sources()

    # Show usage guide
    show_usage_guide()

    print("\n✅ Market Analyst profile is ready to use!")
    print("   Try: janito --market 'What are the top NASDAQ stocks today?'")


if __name__ == "__main__":
    main()
