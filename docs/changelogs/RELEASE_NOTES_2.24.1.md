# Janito v2.24.1 Release Notes

## 🚀 New Features

### Loop Protection for Local Tools
- **Enhanced Safety**: Implemented comprehensive loop protection mechanisms for all local tools to prevent infinite loops and excessive resource consumption
- **Decorator System**: Added `@loop_protection` decorator that can be applied to tool functions to automatically monitor and limit execution cycles
- **Configurable Limits**: Set maximum execution times and iteration counts for protected tools with customizable thresholds
- **Smart Detection**: Automatic detection of repetitive patterns and potential infinite loops in tool execution

### Improved Error Reporting
- **Detailed Diagnostics**: Enhanced error messages now include context information, execution stack traces, and resource usage statistics
- **Protection Status**: Clear indication when loop protection mechanisms are triggered, with detailed information about what caused the intervention
- **Recovery Suggestions**: Error reports now include actionable suggestions for resolving loop-related issues

## 🔧 Improvements

### Tool Adapter Enhancements
- **Performance Monitoring**: Added execution time tracking for all local tool adapters
- **Resource Management**: Improved memory and CPU usage monitoring during tool execution
- **Graceful Degradation**: Better handling of resource exhaustion scenarios with informative user feedback

### Developer Experience
- **Example Scripts**: Added comprehensive example scripts demonstrating loop protection usage (`examples/loop_protection_example.py`)
- **Tool Examples**: Practical examples showing how to implement loop protection in custom tools (`examples/loop_protection_tool_example.py`)
- **Documentation**: Updated developer documentation with loop protection implementation guidelines

## 🐛 Bug Fixes

- **Resource Leaks**: Fixed potential memory leaks in long-running tool executions
- **Exception Handling**: Improved exception handling in tool adapters to prevent crashes during protection interventions
- **Status Reporting**: Corrected issues with protection status reporting in complex execution scenarios

## 📚 Documentation

### New Documentation Files
- `docs/guides/tools-developer-guide.md` - Comprehensive guide for developing tools with loop protection
- `docs/tools/loop-protection.md` - Detailed documentation on loop protection mechanisms and usage

### Updated Documentation
- `README-dev.md` - Enhanced with loop protection development guidelines
- `janito/tools/README.md` - Updated with loop protection implementation details

## 🔍 Technical Details

### Files Added/Modified
- `janito/tools/loop_protection.py` - Core loop protection implementation
- `janito/tools/loop_protection_decorator.py` - Decorator for applying loop protection to functions
- `examples/loop_protection_example.py` - Example demonstrating loop protection usage
- `examples/loop_protection_tool_example.py` - Tool-specific loop protection example
- `janito/tools/adapters/local/*.py` - All local tool adapters updated with loop protection integration
- `test_loop_protection_return.py` - Test suite for loop protection functionality

### Dependencies
- No new dependencies added
- Compatible with existing Janito installations

## 🎯 Usage Examples

### Applying Loop Protection to Custom Tools
```python
from janito.tools.loop_protection_decorator import loop_protection

@loop_protection(max_iterations=100, timeout_seconds=30)
def my_custom_tool(data):
    # Your tool implementation here
    # Loop protection will automatically monitor execution
    pass
```

### Configuration Options
```bash
# Set global loop protection limits
janito config set loop_protection.max_iterations 500
janito config set loop_protection.timeout_seconds 60
```

## 🎉 Acknowledgments

Special thanks to the community for feedback and contributions that helped shape this release, particularly around safety and reliability improvements.

---

**Full Changelog**: https://github.com/ikignosis/janito/compare/v2.24.0...v2.24.1

**Installation**: `pip install janito==2.24.1` or `pip install --upgrade janito`