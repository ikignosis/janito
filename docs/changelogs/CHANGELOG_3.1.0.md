# Janito v3.1.0 Release Notes

**Release Date:** August 23, 2025  
**Version:** v3.1.0  
**PyPI:** [janito 3.1.0](https://pypi.org/project/janito/3.1.0/)

## 🚀 New Features

### Enter Key Cancellation Support for Chat Mode

This release introduces a significant usability improvement for the interactive chat mode: **Enter key cancellation support**.

#### What's New
- **Instant Request Cancellation**: Press the **Enter key** at any time during a request to immediately cancel the current LLM operation
- **Global Cancellation Manager**: Robust cancellation system that works across all components (agent, driver, prompt handler)
- **User Feedback**: Clear visual confirmation when a request is cancelled
- **Clean State Management**: Proper cleanup of cancellation state after request completion

#### How It Works
When you're in chat mode and a request is taking longer than expected:
1. Simply press **Enter** - no need for Ctrl+C or other interrupt combinations
2. The current LLM request is immediately cancelled
3. You'll see a red confirmation message: "Request cancelled by Enter key"
4. The chat session remains active and ready for your next prompt

#### Technical Implementation
- **Global Cancellation Manager**: New `janito.llm.cancellation_manager` module provides centralized cancellation handling
- **Key Binding Integration**: Chat mode now has dedicated Enter key handling for cancellation
- **Cross-Component Support**: Cancellation signals propagate properly through agent, driver, and prompt handler layers
- **Thread-Safe**: Robust handling across multiple threads and async operations

## 🔄 Changes

- Enhanced chat mode user experience with intuitive cancellation
- Improved responsiveness during long-running LLM requests
- Better error handling and state cleanup for cancelled operations

## 📚 Documentation Updates

- Updated CLI options documentation
- Added cancellation behavior to chat mode guides
- Enhanced troubleshooting sections for long-running requests

## 🛠️ Developer Notes

The cancellation system is designed to be extensible and can be integrated with other components as needed. The global cancellation manager provides a clean API for starting, cancelling, and clearing requests across the entire application stack.

---

**Installation:** `pip install janito==3.1.0`  
**Upgrade:** `pip install --upgrade janito`