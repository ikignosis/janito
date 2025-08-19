# Public Sources and Government Data

This section provides information about publicly available government and institutional data sources that can be useful for research, analysis, and development work.

## U.S. Federal Government Sources - Available Public Data

| Source | URL | Content Type | Key Data Available |
|--------|-----|--------------|-------------------|
| **IRS.gov** - Internal Revenue Service | https://www.irs.gov | Tax information, forms, publications | Tax forms, publications, tax statistics |
| **Congressional Budget Office (CBO)** | https://www.cbo.gov | Budget analysis, economic forecasts | Federal budget analysis, economic projections |
| **Bureau of Economic Analysis (BEA)** | https://www.bea.gov | GDP, economic data, industry stats | GDP reports, economic indicators, industry data |
| **Office of Management and Budget (OMB)** | https://www.whitehouse.gov/omb/ | Federal budget, management policies | Budget documents, policy information |
| **Bureau of the Fiscal Service** | https://www.fiscal.treasury.gov | Treasury reports, payment systems | Treasury reports, federal payment data |
| **Government Accountability Office (GAO)** | https://www.gao.gov | Government audits, investigations | Audit reports, government oversight data |
| **Federal Reserve Board** | https://www.federalreserve.gov | Monetary policy, banking regulations | Economic data, policy statements, banking info |
| **U.S. Census Bureau** | https://www.census.gov | Demographic, economic, geographic data | Population data, economic census, business statistics |

## API Access Points

### Official APIs Available

Many government sites offer official APIs for programmatic access:

- **BEA API**: https://apps.bea.gov/api/ - Economic data and GDP statistics
- **Census API**: https://api.census.gov/ - Demographic and business data
- **Federal Reserve API**: Various endpoints for economic indicators
- **GAO API**: Government audit and oversight data
- **IRS SOI Tax Stats**: Tax statistics and income data

### Data.gov Integration

**Data.gov** (https://www.data.gov/) serves as the central repository for government datasets:

- Over 250,000 datasets available
- Searchable by topic, agency, and format
- Direct download links and API access
- Regular updates and new dataset additions

### Best Practices for Access

1. **Respect Rate Limits**: Government sites often have rate limiting
2. **Use Official APIs**: Many sites provide official APIs for programmatic access
3. **Check Terms of Service**: Review usage terms before automated access
4. **Cache Data**: Store frequently accessed data locally to reduce server load
5. **User-Agent Headers**: Use appropriate user-agent strings when accessing programmatically

## Integration with Janito

These sources can be integrated with Janito for research and analysis:

- Use URL fetching tools to retrieve data
- Parse structured data for analysis
- Combine with code execution for data processing
- Generate reports based on public data

For specific integration examples, see the [tools documentation](tools-index.md) and [guides](guides/using.md).