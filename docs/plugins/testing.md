# Testing Plugins

## Overview

This guide explains how to test plugins in the Janito system. Comprehensive testing ensures that plugins work correctly and reliably in various scenarios.

## Test Structure

Tests should be organized in the `tests/` directory with a structure that mirrors the plugin organization:

```
tests/
└── plugins/
    └── myplugin/
        └── test_myplugin.py
```

## Basic Test Example

```python
# tests/plugins/myplugin/test_myplugin.py
def test_hello_world_tool():
    """Test the HelloWorldTool functionality."""
    from plugins.myplugin.tools.hello_world import HelloWorldTool
    
    tool = HelloWorldTool()
    result = tool.run(name="Test")
    assert "Hello, Test!" in result

def test_hello_world_default_name():
    """Test HelloWorldTool with default name."""
    from plugins.myplugin.tools.hello_world import HelloWorldTool
    
    tool = HelloWorldTool()
    result = tool.run()
    assert "Hello, World!" in result
```

## Testing Plugin Metadata

```python
def test_plugin_metadata():
    """Test that plugin metadata is correctly defined."""
    from plugins.myplugin.plugin import MyPlugin
    
    plugin = MyPlugin()
    metadata = plugin.get_metadata()
    
    assert metadata.name == "myplugin"
    assert metadata.version == "1.0.0"
    assert "description" in metadata.description
    assert "author" in metadata.author
```

## Testing Tool Permissions

```python
def test_tool_permissions():
    """Test that tool permissions are correctly set."""
    from plugins.myplugin.tools.hello_world import HelloWorldTool
    
    tool = HelloWorldTool()
    
    # Check that the tool has the expected permissions
    assert tool.permissions.read == True
    assert tool.permissions.write == False
    assert tool.permissions.execute == True
```

## Testing Configuration

```python
def test_plugin_config_schema():
    """Test that the plugin configuration schema is valid."""
    from plugins.myplugin.plugin import MyPlugin
    import jsonschema
    
    plugin = MyPlugin()
    schema = plugin.get_config_schema()
    
    # Test that the schema is valid JSON Schema
    assert "type" in schema
    assert schema["type"] == "object"
    
    # Test that required properties are defined
    if "required" in schema:
        for prop in schema["required"]:
            assert prop in schema["properties"]

def test_config_validation():
    """Test configuration validation."""
    from plugins.myplugin.plugin import MyPlugin
    
    plugin = MyPlugin()
    
    # Test valid configuration
    valid_config = {"api_key": "test1234567890"}
    assert plugin.validate_config(valid_config) == True
    
    # Test invalid configuration
    invalid_config = {"wrong_key": "value"}
    assert plugin.validate_config(invalid_config) == False
```

## Testing Commands

```python
def test_cli_commands():
    """Test that CLI commands are properly registered."""
    from plugins.myplugin.plugin import MyPlugin
    
    plugin = MyPlugin()
    commands = plugin.get_commands()
    
    assert "mycommand" in commands
    assert callable(commands["mycommand"])
```

## Integration Testing

```python
def test_plugin_integration():
    """Test the complete plugin integration."""
    from janito.plugins.manager import PluginManager
    from janito.config import Config
    
    # Create a temporary config
    config = Config()
    config.set("plugins.load.myplugin", True)
    
    # Initialize plugin manager
    manager = PluginManager(config)
    manager.load_plugins()
    
    # Check that the plugin was loaded
    assert "myplugin" in manager.get_loaded_plugins()
    
    # Check that tools are registered
    tools = manager.get_all_tools()
    assert "hello_world" in [tool.tool_name for tool in tools]
```

## Best Practices

### Test Coverage

- **Unit Tests**: Test individual tools and methods
- **Integration Tests**: Test plugin loading and registration
- **Edge Cases**: Test error conditions and invalid inputs
- **Performance**: Test with large inputs and edge cases

### Mocking External Dependencies

```python
from unittest.mock import patch, Mock
def test_weather_tool_with_mock():
    """Test weather tool with mocked API call."""
    from plugins.weather.tools.weather import WeatherTool
    
    # Mock the requests.get method
    with patch('requests.get') as mock_get:
        # Configure the mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "main": {"temp": 20},
            "weather": [{"description": "clear sky"}]
        }
        mock_get.return_value = mock_response
        
        # Create and test the tool
        tool = WeatherTool()
        # Set the API key (normally from config)
        tool.api_key = "test_key"
        result = tool.run(city="London")
        
        # Verify the result
        assert "20°C" in result
        assert "clear sky" in result
        
        # Verify the mock was called correctly
        mock_get.assert_called_once()
```

### Testing Lifecycle Methods

```python
def test_plugin_lifecycle():
    """Test plugin initialization and cleanup."""
    from plugins.myplugin.plugin import MyPlugin
    
    plugin = MyPlugin()
    
    # Test initialization
    plugin.initialize()
    # Add assertions for expected initialization behavior
    
    # Test cleanup
    plugin.cleanup()
    # Add assertions for expected cleanup behavior
```

## Running Tests

Run tests using pytest:

```bash
# Run all plugin tests
pytest tests/plugins/

# Run tests for a specific plugin
pytest tests/plugins/myplugin/

# Run with coverage report
pytest tests/plugins/ --cov=plugins --cov-report=html
```

## Continuous Integration

Include plugin tests in your CI/CD pipeline:

```yaml
# .github/workflows/test.yml
name: Test Plugins

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.12'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      run: |
        pytest tests/plugins/ --cov=plugins --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v1
```

Comprehensive testing ensures that your plugins are reliable, secure, and maintainable.