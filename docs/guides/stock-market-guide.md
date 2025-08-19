# Stock Market Data Access Guide

This guide explains how to access and work with stock market data using Janito's built-in tools and external resources.

## Overview

While Janito doesn't include built-in stock market APIs, you can use its web scraping and data processing capabilities to gather financial information from public sources. This guide covers reliable approaches to access market data.

## Current Market Data Sources

| Source Type | Platform | URL | Data Available | Access Method |
|-------------|----------|-----|----------------|---------------|
| **Government** | SEC EDGAR | https://www.sec.gov/edgar/searchedgar/companysearch.html | Company filings, 10-K, 10-Q reports | Web scraping + official API |
| **Government** | Federal Reserve FRED | https://fred.stlouisfed.org/ | Economic indicators, market data | Free API with registration |
| **Public** | TradingView | https://www.tradingview.com/markets/ | Real-time quotes, charts, analysis | Web scraping friendly |
| **Public** | Investing.com | https://www.investing.com/indices/ | Global indices, commodities, stocks | Web scraping |

**Note**: Many major financial sites (Yahoo Finance, Bloomberg, MarketWatch) have implemented strict anti-bot measures that may block automated access.

### Recommended Approach

1. **Use TradingView for current market data**
   ```bash
   janito "Fetch Apple's current stock information from tradingview.com"
   ```

2. **Access SEC filings for fundamental data**
   ```bash
   janito "Get the latest 10-K filing for Apple Inc from SEC EDGAR"
   ```

3. **Use Federal Reserve data for economic indicators**
   ```bash
   janito "Fetch current S&P 500 data from FRED API"
   ```

## Working with Stock Data

### Basic Stock Information

To get basic stock information, you can use:

```bash
# Get Apple's current trading information
janito "Visit https://www.tradingview.com/symbols/NASDAQ-AAPL/ and extract key metrics"

# Get market indices
janito "Fetch current S&P 500, Dow Jones, and Nasdaq values from investing.com"
```

### Historical Data

For historical data, use:

```bash
# Get historical price data
janito "Find Apple's stock price history for the last 30 days from a reliable source"

# Access SEC filings for quarterly reports
janito "Download Apple's latest quarterly report from SEC EDGAR"
```

## Alternative Data Sources

| Source Category | Provider | Data Types | Access Method | Key Features |
|----------------|----------|------------|---------------|--------------|
| **Government** | SEC EDGAR | Company filings, 10-K, 10-Q reports | Web + API | Official financial statements |
| **Government** | Federal Reserve | Economic indicators, interest rates | API + Web | Monetary policy data |
| **Government** | Bureau of Labor Statistics | Employment data | API + Downloads | Labor market indicators |
| **Government** | Treasury Department | Bond yields, economic data | API + Reports | Treasury rates and auctions |

| API Provider | Free Tier Limits | Data Types | Registration Required | Rate Limits |
|--------------|------------------|------------|----------------------|-------------|
| **Alpha Vantage** | 5 calls/min, 500/day | Stocks, forex, crypto | Yes - API key | 5 API calls per minute |
| **Financial Modeling Prep** | Limited daily calls | Financial statements, ratios | Yes - API key | Daily quota system |
| **Twelve Data** | 8 calls/minute | Real-time and historical | Yes - API key | 8 API calls per minute |

## Example Workflows

### Quick Stock Check

```bash
# Check current Apple stock price
janito "What is Apple's current stock price and recent performance?"

# Get market overview
janito "Show me today's market summary including major indices"
```

### Detailed Analysis

```bash
# Comprehensive stock analysis
janito "Analyze Apple's financial performance using latest SEC filings and market data"

# Compare multiple stocks
janito "Compare performance of AAPL, MSFT, GOOGL, and TSLA over the past month"
```

## Troubleshooting

### Common Issues & Solutions

| Issue | Description | Solution |
|-------|-------------|----------|
| **Blocked Access** | Many financial sites block automated requests | Use public APIs or government sources |
| **Rate Limiting** | Free APIs have usage limits | Implement caching or use multiple sources |
| **Data Accuracy** | Ensure reliable data sources | Cross-reference multiple sources |

### Best Practices

| Practice | Description | Implementation |
|----------|-------------|----------------|
| **Source Verification** | Always verify data from multiple sources | Compare results across different providers |
| **Government Sources** | Use official sources for regulatory filings | SEC EDGAR for company filings |
| **Rate Limiting** | Implement delays to avoid blocks | Add sleep timers between requests |
| **Data Caching** | Cache frequently accessed data locally | Use local files or databases for storage |

## Related Documentation

- [Public Data Sources](../public-sources.md) - Government and public financial data
- [Using Tools](using_tools.md) - How to use Janito's web scraping capabilities
- [CLI Options](../reference/cli-options.md) - Command-line options for data fetching

## Getting Help

If you need help accessing specific financial data:

1. Check the [troubleshooting section](configuration.md) for common issues
2. Use `janito --help` to see available options
3. Open an issue on GitHub for specific data access requests