# Janito Market Analyst Profile

## Overview
The Market Analyst profile in janito provides comprehensive financial market analysis capabilities, including stock recommendations, technical analysis, and trading strategies.

## Usage

### Command Line
```bash
# Use Market Analyst profile
janito --market "Analyze AAPL stock"

# Or explicitly specify profile
janito --profile "Market Analyst" "List top tech stocks to buy"
```

### Interactive Mode
```bash
# Start interactive chat with Market Analyst profile
janito --market

# Then ask questions like:
# "What are the best NASDAQ stocks to sell tomorrow?"
# "Analyze TSLA technical indicators"
# "Provide options strategy for NVDA earnings"
```

## Capabilities

### Technical Analysis
- **Indicators**: RSI, MACD, Bollinger Bands, VWAP, Moving averages
- **Patterns**: Head & shoulders, triangles, flags, support/resistance levels
- **Volume Analysis**: OBV, volume profile, accumulation/distribution
- **Multi-timeframe**: Daily, 4-hour, 15-minute analysis

### Fundamental Analysis
- **Valuation Metrics**: P/E, EV/EBITDA, P/S, P/B ratios
- **Growth Analysis**: EPS revisions, revenue growth trends
- **Financial Health**: Debt ratios, cash flow analysis, ROIC
- **DCF Modeling**: 2-stage and 3-stage models

### Sentiment & Flow Analysis
- **Analyst Sentiment**: EPS revisions, price target changes
- **Options Flow**: Put/call ratios, unusual activity, implied volatility
- **Institutional Flows**: 13F changes, short interest, ETF flows
- **Retail Sentiment**: Social media trends, Google search data

### Risk Management
- **Position Sizing**: Kelly criterion, fixed fractional risk
- **Stop Loss**: ATR-based, structure-based stops
- **Options Strategies**: Vertical spreads, straddles, strangles
- **Portfolio Management**: Correlation analysis, beta adjustment

## Example Queries

### Stock Analysis
```
"Analyze TSLA with technical and fundamental view"
"Compare NVDA vs AMD valuation metrics"
"What are the key risks for AAPL in Q3?"
```

### Market Timing
```
"Best NASDAQ stocks to sell tomorrow based on technicals"
"Which tech stocks are showing bearish divergence?"
"Identify oversold stocks in the S&P 500"
```

### Strategy Development
```
"Create a pairs trading strategy for FAANG stocks"
"Design an options strategy for earnings season"
"Build a momentum screening system"
```

## Data Sources
The Market Analyst uses publicly available data and standard analytical frameworks. No real-time brokerage feeds or proprietary data is accessed.

## Important Disclaimer
This tool provides analytical insights for educational and research purposes. It does not provide personalized investment advice. Always conduct your own due diligence and consult with qualified financial professionals before making investment decisions.

## Troubleshooting

### Profile Not Found
If you see "Could not find profile 'Market Analyst'", ensure you're using the correct syntax:
```bash
janito --profile "Market Analyst" "your query"
# or
janito --market "your query"
```

### Permission Issues
For full functionality, ensure read permissions are enabled:
```bash
janito --read --market "analyze stock data"
```