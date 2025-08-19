# Intermediate Plugin Example

## Overview

This example demonstrates a more advanced plugin that integrates with external APIs and provides configuration options. It shows how to create plugins with real-world functionality.

## Plugin Code

```python
from janito.plugins.base import Plugin, PluginMetadata, PluginResource
from janito.tools.tool_base import ToolBase, ToolPermissions
from typing import Dict, Any
import requests

# Weather tool that uses an external API
class WeatherTool(ToolBase):
    tool_name = "get_weather"
    permissions = ToolPermissions(read=True, write=False, execute=True)
    
    def __init__(self):
        super().__init__()
        self.api_key = None
    
    def run(self, city: str, units: str = "metric") -> str:
        """Get current weather for a city."""
        if not self.api_key:
            return "Error: Weather API key not configured. Please set api_key in plugin configuration."
        
        try:
            url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={self.api_key}&units={units}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            temp = data["main"]["temp"]
            description = data["weather"][0]["description"]
            
            unit_symbol = "°C" if units == "metric" else "°F"
            return f"Current weather in {city}: {temp}{unit_symbol}, {description}"
            
        except requests.RequestException as e:
            return f"Error retrieving weather data: {str(e)}"
        except KeyError as e:
            return f"Error parsing weather data: {str(e)}"

# Define the plugin
class WeatherPlugin(Plugin):
    def __init__(self):
        super().__init__()
        self.weather_tool = WeatherTool()
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="weather",
            version="1.0.0",
            description="Weather information plugin",
            author="Janito Team",
            license="MIT",
            homepage="https://github.com/janito/plugins/weather",
            dependencies=["requests"]
        )
    
    def get_tools(self):
        return [WeatherTool]
    
    def initialize(self):
        # Load configuration on startup
        config = self.get_config()
        if config and "api_key" in config:
            self.weather_tool.api_key = config["api_key"]
        
    def get_config_schema(self) -> Dict[str, Any]:
        """Return JSON schema for plugin configuration."""
        return {
            "type": "object",
            "properties": {
                "api_key": {
                    "type": "string",
                    "description": "OpenWeatherMap API key",
                    "minLength": 32
                },
                "default_units": {
                    "type": "string",
                    "description": "Default temperature units (metric/imperial)",
                    "enum": ["metric", "imperial"],
                    "default": "metric"
                }
            },
            "required": ["api_key"]
        }
    
    def get_resources(self) -> list:
        return [
            PluginResource(
                name="get_weather",
                type="tool",
                description="Retrieve current weather information for cities"
            )
        ]

# Register the plugin
class PLUGIN_CLASS(WeatherPlugin):
    pass
```

## Configuration

Configure the plugin with your API key in `janito.json`:

```json
{
  "plugins": {
    "load": {
      "weather": true
    },
    "config": {
      "weather": {
        "api_key": "your_openweathermap_api_key_here",
        "default_units": "metric"
      }
    }
  }
}
```

## Usage

```json
{
  "tool": "get_weather",
  "city": "London",
  "units": "metric"
}
```

## Key Concepts Demonstrated

- **External API Integration**: Using the `requests` library to call external services
- **Configuration**: Defining a schema and accessing configuration values
- **Error Handling**: Robust error handling for network requests and data parsing
- **Initialization**: Using `initialize()` to set up the plugin on load
- **Dependencies**: Declaring external package dependencies
- **Resource Declaration**: Explicitly defining provided resources

This intermediate example shows how to create plugins with external dependencies, configuration, and real-world functionality, preparing you for more complex plugin development.