# Janito Release Comparison: v2.21.0 vs v2.22.0

## 📊 Side-by-Side Overview

| Aspect | v2.21.0 | v2.22.0 |
|--------|---------|---------|
| **Release Date** | August 12, 2025 | August 14, 2025 |
| **Primary Focus** | IBM WatsonX Provider Foundation | IBM WatsonX Enhancement + Market Analysis |
| **New Providers** | IBM WatsonX (initial) | IBM WatsonX (enhanced) |
| **New Profiles** | - | Market Analyst Profile |
| **Documentation** | Basic IBM setup | Comprehensive guides + market data |

## 🚀 Feature Comparison

### New Features

#### v2.21.0
- **IBM WatsonX Provider**: Initial implementation with basic Granite, Llama, and Mistral models
- **Enhanced fetch_url**: Added configurable limits (max_length, max_lines, context_chars)
- **Environment Variables**: Added examples for all providers
- **Model Lists**: Updated OpenAI, Anthropic, and Google provider models

#### v2.22.0
- **IBM WatsonX Enhancement**: Complete provider with enterprise-grade models
- **Market Analyst Profile**: Specialized for financial analysis workflows
- **Enhanced fetch_url**: Added error caching for 403/404 responses
- **Comprehensive Documentation**: Complete setup guides and market data sources

### Documentation Improvements

#### v2.21.0
- Basic IBM WatsonX setup guide (`janito/providers/ibm/README.md`)
- Updated GETTING_STARTED.md with IBM instructions
- Environment variable examples

#### v2.22.0
- **New Guides**:
  - `docs/ibm-setup.md` - Complete step-by-step IBM configuration
  - `docs/guides/market-data-sources.md` - Public financial data sources
  - `docs/guides/stock-market-guide.md` - Stock market analysis workflows
  - `docs/public-sources.md` - Comprehensive public data sources
- **Enhanced Documentation**: Updated all provider comparisons and model listings

## 🔧 Technical Improvements

### Code Changes

#### v2.21.0
- **Files Modified**: 9 files, +306/-36 lines
- **Focus**: IBM provider foundation and fetch_url enhancements
- **Complexity**: Reduced fetch_url complexity by splitting into helper methods

#### v2.22.0
- **Files Modified**: 14 files, +732/-29 lines
- **Focus**: IBM enhancement, market analyst profile, and comprehensive documentation
- **Bug Fixes**: Profile template path resolution
- **Performance**: fetch_url error caching for better reliability

### Provider Capabilities

#### v2.21.0 IBM WatsonX
- Basic model support (Granite, Llama, Mistral)
- Initial configuration setup
- Basic authentication handling

#### v2.22.0 IBM WatsonX
- **Enhanced Model Support**: IBM Granite enterprise models + open-source models
- **Complete Setup Guide**: Step-by-step configuration with examples
- **Enterprise Integration**: Better suited for business and financial analysis

## 🎯 Usage Evolution

### v2.21.0 Usage
```bash
# Basic IBM setup
janito config set provider ibm
janito config set model ibm/granite-3-8b-instruct
```

### v2.22.0 Usage
```bash
# Enhanced IBM setup with market analysis
janito config set provider ibm
janito config set model ibm/granite-3-8b-instruct
janito --profile market_analyst "Analyze AAPL stock performance"
```

## 📈 Impact Summary

### v2.21.0 Impact
- **Foundation**: Established IBM WatsonX as a supported provider
- **Technical**: Improved URL fetching capabilities
- **Documentation**: Basic setup instructions

### v2.22.0 Impact
- **Specialization**: Added domain-specific profile for financial analysis
- **Completeness**: Comprehensive IBM WatsonX integration
- **Usability**: Rich documentation for market analysis workflows
- **Reliability**: Enhanced error handling in URL fetching

## 🔄 Migration Path

Both versions are fully backward compatible. Users can upgrade seamlessly:

```bash
# From any previous version
pip install --upgrade janito

# New capabilities immediately available
janito --profile market_analyst "help with stock analysis"
```

## 🎉 Summary

- **v2.21.0**: Laid the foundation with IBM WatsonX support
- **v2.22.0**: Built upon that foundation with specialized market analysis capabilities and comprehensive documentation

The progression from v2.21.0 to v2.22.0 represents a shift from basic provider support to domain-specific specialization, making Janito more valuable for financial analysis and market research use cases.