# Security Commands Guide

This guide explains how to use the `/security` command in chat mode to manage security settings, particularly for restricting the `fetch_url` tool to trusted domains.

## Overview

The `/security` command provides a centralized way to manage security settings in chat mode. Currently, it supports managing allowed sites for the `fetch_url` tool, which is particularly useful for market analysts who should only access trusted financial data sources.

## Security Command Structure

```
/security <subcommand> [arguments...]
```

### Available Subcommands

- `allowed-sites` - Manage the URL whitelist for fetch_url tool

## Allowed Sites Management

The `/security allowed-sites` subcommand allows you to control which websites the `fetch_url` tool can access.

### Commands

```
/security allowed-sites list                    # Show all allowed sites
/security allowed-sites add <site>             # Add a site to whitelist
/security allowed-sites remove <site>          # Remove a site from whitelist
/security allowed-sites clear                  # Clear all restrictions
```

## Quick Start for Market Analysts

### Step 1: Configure Trusted Market Data Sources

```
/security allowed-sites add sec.gov
/security allowed-sites add fred.stlouisfed.org
/security allowed-sites add tradingview.com
/security allowed-sites add investing.com
/security allowed-sites add alphavantage.co
/security allowed-sites add financialmodelingprep.com
/security allowed-sites add twelvedata.com
```

### Step 2: Verify Configuration

```
/security allowed-sites list
```

### Step 3: Test with Market Analysis

```
Fetch Apple's current stock price from tradingview.com
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

### Adding Sites

```
# Add a single trusted source
/security allowed-sites add sec.gov

# Add multiple sources one by one
/security allowed-sites add tradingview.com
/security allowed-sites add investing.com
/security allowed-sites add alphavantage.co
```

### Removing Sites

```
# Remove a specific site
/security allowed-sites remove yahoo.com

# Verify removal
/security allowed-sites list
```

### Managing Restrictions

```
# List current restrictions
/security allowed-sites list

# Temporarily allow all sites
/security allowed-sites clear

# Re-establish restrictions
/security allowed-sites add sec.gov
/security allowed-sites add tradingview.com
```

## Best Practices

### For Market Analysts

1. **Start with Tier 1 sources**: Begin with government sources for reliability
2. **Add Tier 2 gradually**: Include public sources as needed
3. **Document changes**: Keep track of which sites are added/removed
4. **Regular review**: Periodically review the whitelist for relevance

### Security Guidelines

1. **Principle of least privilege**: Only add sites you actually need
2. **Domain specificity**: Use specific domains rather than wildcards
3. **Regular audits**: Review the whitelist regularly
4. **Backup configuration**: Save your whitelist configuration

## Configuration Persistence

The whitelist configuration is stored in `~/.janito/url_whitelist.json` and persists across sessions:

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

## Integration with Profiles

When using the Market Analyst profile, you can pre-configure trusted sources:

```
# Set up security before using market analyst
/security allowed-sites add sec.gov
/security allowed-sites add fred.stlouisfed.org
/security allowed-sites add tradingview.com

# Then use market analyst profile
/profile market-analyst
Analyze Apple's financial performance
```

## Troubleshooting

### Common Issues

**Problem**: `fetch_url` returns "URL blocked by whitelist"
```
# Check current whitelist
/security allowed-sites list

# Add the missing site
/security allowed-sites add missing-site.com
```

**Problem**: Need to allow subdomains
```
# The whitelist automatically includes subdomains
# Adding "tradingview.com" also allows "www.tradingview.com", "api.tradingview.com", etc.
```

**Problem**: Want to temporarily disable whitelist
```
# Clear all restrictions
/security allowed-sites clear

# Restore later by adding sites back
/security allowed-sites add sec.gov
/security allowed-sites add tradingview.com
```

## Advanced Usage

### Batch Configuration

```
# Configure comprehensive market sources
/security allowed-sites add sec.gov
/security allowed-sites add fred.stlouisfed.org
/security allowed-sites add tradingview.com
/security allowed-sites add investing.com
/security allowed-sites add alphavantage.co
/security allowed-sites add financialmodelingprep.com
/security allowed-sites add twelvedata.com
```

### Team Configuration Sharing

```
# Share configuration with team
/security allowed-sites list
# Copy the output and share with team members

# Team members can then configure their instances
/security allowed-sites add sec.gov
/security allowed-sites add tradingview.com
# ... etc
```

## Related Documentation

- [Market Data Sources Guide](market-data-sources.md) - Comprehensive list of reliable sources
- [URL Whitelist Guide](url-whitelist.md) - Detailed whitelist configuration
- [Using Tools](using_tools.md) - General tool usage documentation
- [CLI Options](../reference/cli-options.md) - Complete CLI reference