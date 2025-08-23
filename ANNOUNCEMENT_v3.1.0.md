# 🚀 Janito v3.1.0 Released - Enter Key Cancellation for Chat Mode

**Release Date:** August 23, 2025  
**Version:** v3.1.0  
**PyPI:** [janito 3.1.0](https://pypi.org/project/janito/3.1.0/)

## 🎯 What's New

### Instant Request Cancellation in Chat Mode

Say goodbye to waiting for stuck LLM requests! Janito v3.1.0 introduces **Enter key cancellation support** for interactive chat mode.

#### ✨ Key Features
- **Press Enter to Cancel**: Instantly cancel any running request with a single key press
- **Real-time Feedback**: Clear visual confirmation when cancellation occurs
- **Clean Recovery**: Session remains active and ready for your next prompt
- **Cross-Platform**: Works seamlessly across all supported platforms

#### 🎮 How to Use
1. Start chat mode: `janito`
2. Submit any prompt
3. **Press Enter** at any time to cancel the current request
4. See immediate confirmation: "Request cancelled by Enter key"
5. Continue chatting without interruption

## 📦 Installation & Upgrade

```bash
# New installation
pip install janito==3.1.0

# Upgrade existing installation
pip install --upgrade janito
```

## 🔧 Technical Highlights

- **Global Cancellation Manager**: Robust cross-component cancellation system
- **Thread-Safe**: Safe cancellation across async operations
- **Backward Compatible**: All existing functionality preserved
- **Clean Architecture**: Extensible design for future enhancements

## 📚 Documentation

- [Full Release Notes](docs/changelogs/CHANGELOG_3.1.0.md)
- [Updated Usage Guide](docs/guides/using.md)
- [CLI Options Reference](docs/reference/cli-options.md)

## 🌟 Try It Now

Experience the improved chat mode with instant cancellation:

```bash
janito
# Then try: "Write a comprehensive analysis of quantum computing applications"
# Press Enter anytime to cancel if needed!
```

---

**Happy coding!** 🎉

*Join our community for support and discussions.*