# Market Data Sources Guide

This guide provides information about reliable sources for accessing financial market data and stock information.

## Reliable Market Data Sources

### Government & Regulatory Sources

| Source | URL | Data Type | Access Method | Notes |
|--------|-----|-----------|---------------|--------|
| **SEC EDGAR** | https://www.sec.gov/edgar/searchedgar/companysearch.html | Company filings, 10-K, 10-Q, 8-K reports | Web scraping + official API | Official financial statements, insider trading reports |
| **Federal Reserve FRED** | https://fred.stlouisfed.org/ | Economic indicators, interest rates, market indices | Free API with registration | Comprehensive economic and market data |

### Public Financial Data Sources

| Source | URL | Data Type | Access Method | Coverage |
|--------|-----|-----------|---------------|----------|
| **TradingView** | https://www.tradingview.com/markets/ | Real-time quotes, charts, technical analysis | Web scraping friendly | Global markets with proper user-agent |
| **Investing.com** | https://www.investing.com/indices/ | Global indices, commodities, currencies, stocks | Web scraping | International markets and real-time data |
| **Yahoo Finance** | https://finance.yahoo.com/ | Stock prices, historical data | Limited access | May have restrictions, use alternatives |

### Financial APIs with Free Tiers

| API Provider | URL | Free Tier Limits | Data Types | Rate Limits |
|--------------|-----|------------------|------------|-------------|
| **Alpha Vantage** | https://www.alphavantage.co/ | 5 calls/min, 500/day | Stocks, forex, crypto, historical | 5 API calls per minute |
| **Financial Modeling Prep** | https://financialmodelingprep.com/developer/docs/ | Limited daily calls | Financial statements, ratios, prices | Daily quota system |
| **Twelve Data** | https://twelvedata.com/ | 8 calls/minute | Stocks, forex, crypto, real-time | 8 API calls per minute |

## Working with Market Data in Janito

### Security Configuration

Before accessing market data, configure trusted sources using the `/security` command:

```
/security allowed-sites add sec.gov
/security allowed-sites add fred.stlouisfed.org
/security allowed-sites add tradingview.com
/security allowed-sites add investing.com
/security allowed-sites add alphavantage.co
/security allowed-sites add financialmodelingprep.com
/security allowed-sites add twelvedata.com

# Verify configuration
/security allowed-sites list
```

### Quick Stock Price Check

```
# Get current Apple stock information
Fetch Apple's current stock price and key metrics from tradingview.com

# Get market indices overview
Retrieve current S&P 500, Dow Jones, and Nasdaq values from investing.com
```

### Historical Data Access

```
# Get historical price data
Find historical stock price data for Apple from FRED database

# Access SEC filings
Download Apple's latest 10-K filing from SEC EDGAR
```

### Economic Indicators

```
# Get Federal Reserve data
Fetch current federal funds rate and economic indicators from FRED

# Market analysis
Analyze current market conditions using available public data sources
```

## Data Source Reliability

| Tier | Sources | Reliability | Access Notes |
|------|---------|-------------|--------------|
| **Tier 1** | SEC, FRED, Census Bureau, Official APIs | Most Reliable | Government sources with documented endpoints |
| **Tier 2** | TradingView, Investing.com, Alpha Vantage | Reliable with Limitations | Good for current data, web scraping friendly, free tier limits |
| **Tier 3** | Yahoo Finance, Bloomberg, Reuters | Use with Caution | Access restrictions, typically blocked for automated access |

## Best Practices

### Data Collection Best Practices

| Practice | Description | Implementation |
|----------|-------------|----------------|
| **Official APIs** | Use provided APIs when available | Check developer documentation for endpoints |
| **Rate Limiting** | Implement delays to avoid blocks | Add sleep timers between requests |
| **Data Caching** | Store frequently accessed data locally | Use local files or databases for storage |
| **Cross-Reference** | Verify data from multiple sources | Compare results across different providers |
| **Terms Compliance** | Respect robots.txt and service terms | Review and follow usage guidelines |

### Error Handling

```bash
# Handle blocked access gracefully
janito "If tradingview.com is blocked, try investing.com for Apple stock data"

# Fallback sources
janito "Get Apple's financial data from SEC filings if market data sources are unavailable"
```

## Integration Examples

### Portfolio Tracking

```
# Track multiple stocks
Monitor AAPL, MSFT, GOOGL, and TSLA using available public sources

# Market overview
Generate a daily market summary using government and public data sources
```

### Economic Analysis

```
# Economic indicators
Analyze the relationship between Federal Reserve data and market performance

# Sector analysis
Compare technology sector performance using SEC filings and market data
```

## Security Configuration

For enhanced security, use the `/security` command in chat mode to restrict access to trusted sources:

- [Security Commands Guide](security-commands.md) - Manage allowed sites for fetch_url
- [URL Whitelist Guide](url-whitelist.md) - Detailed whitelist configuration

## Related Documentation

- [Stock Market Guide](stock-market-guide.md) - Comprehensive guide to accessing financial data
- [Public Sources](../public-sources.md) - Government and institutional data sources
- [Using Tools](using_tools.md) - How to use Janito's data fetching capabilities
- [CLI Options](../reference/cli-options.md) - Command-line options for data access

## Getting Help

For assistance with market data access:

1. Configure trusted sources with `/security allowed-sites add <site>`
2. Use `/security allowed-sites list` to verify configuration
3. Check the [troubleshooting section](configuration.md)
4. Open GitHub issues for specific data source requests