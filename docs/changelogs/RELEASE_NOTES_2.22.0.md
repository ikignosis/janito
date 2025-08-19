# Janito v2.22.0 Release Notes

## 🚀 New Features

### IBM WatsonX Provider Support
- **New Provider**: Added comprehensive IBM WatsonX provider integration
- **Model Support**: Includes IBM Granite models and various open-source models available through WatsonX
- **Documentation**: Complete setup guide with authentication and configuration instructions
- **Enhanced Capabilities**: Access to enterprise-grade AI models for business and financial analysis

### Market Analyst Profile
- **New Profile**: Added specialized Market Analyst profile for financial analysis workflows
- **Financial Analysis**: Optimized for stock market analysis, financial data interpretation, and market research
- **Data Sources**: Integrated support for public financial data sources and market APIs
- **Templates**: Comprehensive system prompt template for market-focused conversations

## 🔧 Improvements

### Enhanced fetch_url Tool
- **Error Handling**: Added intelligent error caching for 403 (Forbidden) and 404 (Not Found) responses
- **Performance**: Reduced redundant network requests when URLs are known to be inaccessible
- **Reliability**: Better handling of rate limiting and temporary access restrictions

### Documentation Updates
- **IBM Setup Guide**: Complete step-by-step documentation for IBM WatsonX configuration
- **Market Data Sources**: Comprehensive guide to public financial data sources
- **Stock Market Guide**: Detailed instructions for stock market analysis workflows
- **Provider Platform Access**: Updated documentation covering all supported providers
- **Portuguese Translation**: Updated README-pt.md with latest features

## 🐛 Bug Fixes

- **Profile Selection**: Fixed profile template path resolution in session selection
- **Template Loading**: Improved handling of profile template paths across different environments

## 📚 Documentation

### New Documentation Files
- `docs/ibm-setup.md` - Complete IBM WatsonX setup guide
- `docs/guides/market-data-sources.md` - Public financial data sources guide
- `docs/guides/stock-market-guide.md` - Stock market analysis workflows
- `docs/public-sources.md` - Comprehensive public data sources documentation

### Updated Documentation
- `docs/drivers.md` - Updated with IBM WatsonX driver information
- `docs/index.md` - Enhanced with new provider and profile information
- `docs/provider-platform-access.md` - Updated provider comparison table
- `docs/supported-providers-models.md` - Added IBM WatsonX model listings

## 🎯 Usage Examples

### IBM WatsonX Configuration
```bash
# Set up IBM WatsonX provider
janito config set provider ibm
janito config set model ibm/granite-3-8b-instruct
janito config set api_key YOUR_IBM_API_KEY
```

### Market Analyst Profile
```bash
# Use the new Market Analyst profile
janito --profile market_analyst "Analyze AAPL stock performance for Q3 2024"
```

## 🔍 Technical Details

### Files Added/Modified
- `janito/providers/ibm/model_info.py` - IBM WatsonX model definitions
- `janito/agent/templates/profiles/system_prompt_template_market_analyst.txt.j2` - Market analyst profile template
- `janito/cli/chat_mode/session_profile_select.py` - Fixed profile selection logic
- `janito/tools/adapters/local/fetch_url.py` - Enhanced error handling and caching

### Dependencies
- No new dependencies added
- Compatible with existing Janito installations

## 🎉 Acknowledgments

Special thanks to the community for feedback and contributions that helped shape this release, particularly around financial analysis use cases and enterprise AI integration.

---

**Full Changelog**: https://github.com/ikignosis/janito/compare/v2.21.0...v2.22.0

**Installation**: `pip install janito==2.22.0` or `pip install --upgrade janito`