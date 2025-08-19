# URL Whitelist Guide

This guide explains how to use the URL whitelist feature to restrict the `fetch_url` tool to specific domains, particularly useful for market analysts who should only access trusted financial data sources.

> **Note**: For interactive use in chat mode, we recommend using the `/security` command instead of CLI options. See [Security Commands Guide](security-commands.md) for details.

## Overview

The URL whitelist feature allows you to restrict which websites the `fetch_url` tool can access. This is particularly useful for:

- **Security**: Prevent access to potentially malicious sites
- **Compliance**: Ensure only approved data sources are used
- **Focus**: Restrict market analysts to reliable financial data sources

## Quick Start

### Setting Up Market Data Sources

Use the `/security` command in chat mode:

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

### Managing Allowed Sites

```
# List all allowed sites
/security allowed-sites list

# Add a single site
/security allowed-sites add yahoo.com

# Remove a site
/security allowed-sites remove yahoo.com

# Clear all restrictions (allow all sites)
/security allowed-sites clear
```

## Configuration Methods

### Method 1: Using --set (Recommended for CLI)

```bash
# Set multiple sites at once
janito --set allowed_sites=site1.com,site2.com,site3.com

# Example for market data
janito --set allowed_sites=sec.gov,fred.stlouisfed.org,tradingview.com
```

### Method 2: Using Chat Mode Commands (Recommended)

```
# Add sites one by one
/security allowed-sites add sec.gov
/security allowed-sites add fred.stlouisfed.org
/security allowed-sites add tradingview.com
/security allowed-sites add investing.com
```

## Market Data Sources

### Tier 1: Government & Official Sources

- **sec.gov** - SEC EDGAR filings and company reports
- **fred.stlouisfed.org** - Federal Reserve economic data

### Tier 2: Public Financial Data

- **tradingview.com** - Real-time quotes and charts
- **investing.com** - Global indices and market data
- **yahoo.com** - Stock prices and historical data (use with caution)

### Tier 3: Financial APIs

- **alphavantage.co** - Free tier API for stocks and forex
- **financialmodelingprep.com** - Financial statements and ratios
- **twelvedata.com** - Real-time and historical data

## Usage Examples

### Setting Up for Market Analysis

```bash
# Configure for comprehensive market analysis
janito --set allowed_sites=sec.gov,fred.stlouisfed.org,tradingview.com,investing.com,alphavantage.co

# Test the configuration
janito "Fetch Apple's current stock price from tradingview.com"
```

### Restricting to Government Sources Only

```bash
# Ultra-secure configuration
janito --set allowed_sites=sec.gov,fred.stlouisfed.org

# This will block non-government sources
janito "Get Apple's 10-K filing"  # ✅ Works (sec.gov)
janito "Get Apple's stock price"  # ❌ Blocked (needs tradingview.com)
```

### Temporary Access for Testing

```bash
# Add a site temporarily
janito --add-allowed-site test-site.com

# Use it for testing
janito "Test data from test-site.com"

# Remove when done
janito --remove-allowed-site test-site.com
```

## Configuration File

The whitelist is stored in `~/.janito/url_whitelist.json`:

```json
{
  "allowed_sites": [
    "sec.gov",
    "fred.stlouisfed.org",
    "tradingview.com",
    "investing.com"
  ]
}
```

## Best Practices

### For Market Analysts

1. **Start with Tier 1 sources**: Begin with government sources for reliability
2. **Add Tier 2 gradually**: Include public sources as needed
3. **Document changes**: Keep track of which sites are added/removed
4. **Regular review**: Periodically review the whitelist for relevance

### For Security

1. **Principle of least privilege**: Only add sites you actually need
2. **Domain specificity**: Use specific domains (e.g., `tradingview.com`) rather than wildcards
3. **Regular audits**: Review the whitelist regularly
4. **Backup configuration**: Save your whitelist configuration

## Troubleshooting

### Common Issues

**Problem**: `fetch_url` returns "URL blocked by whitelist"

```bash
# Check current whitelist
janito --list-allowed-sites

# Add the missing site
janito --add-allowed-site missing-site.com
```

**Problem**: Need to allow subdomains

```bash
# The whitelist automatically includes subdomains
# Adding "tradingview.com" also allows "www.tradingview.com", "api.tradingview.com", etc.
```

**Problem**: Want to temporarily disable whitelist

```bash
# Clear all restrictions
janito --clear-allowed-sites

# Restore later by setting allowed sites again
janito --set allowed_sites=your-previous-list
```

## Integration with Profiles

### Market Analyst Profile

When using the Market Analyst profile, you can pre-configure trusted sources:

```
# Set up security in chat mode
/security allowed-sites add sec.gov
/security allowed-sites add fred.stlouisfed.org
/security allowed-sites add tradingview.com
/security allowed-sites add investing.com

# Then use market analyst profile
/profile market-analyst
Analyze Apple's financial performance
```

## Advanced Usage

### Scripting

```bash
#!/bin/bash
# setup-market-sources.sh

SITES=(
    "sec.gov"
    "fred.stlouisfed.org"
    "tradingview.com"
    "investing.com"
    "alphavantage.co"
    "financialmodelingprep.com"
    "twelvedata.com"
)

# Join array with commas
ALLOWED_SITES=$(IFS=,; echo "${SITES[*]}")

# Set configuration
janito --set allowed_sites="$ALLOWED_SITES"

echo "Market data sources configured:"
janito --list-allowed-sites
```

### Team Configuration

Share configurations across teams:

```bash
# Export current whitelist
janito --list-allowed-sites > market-sources.txt

# Import on another machine
janito --set allowed_sites=$(cat market-sources.txt | tr '\n' ',' | sed 's/,$//')
```

## Related Documentation

- [Security Commands Guide](security-commands.md) - Manage allowed sites with `/security` command
- [Market Data Sources Guide](market-data-sources.md) - Comprehensive list of reliable sources
- [Using Tools](using_tools.md) - General tool usage documentation
- [CLI Options](../reference/cli-options.md) - Complete CLI reference