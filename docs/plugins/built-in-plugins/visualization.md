# Visualization Plugin

## Overview

The Visualization plugin provides data visualization and charting capabilities. This plugin enables the display of data in various visual formats, making it easier to understand and analyze information.

## Resources Provided

### Tools

| Tool Name | Function | Description |
|-----------|----------|-------------|
| `read_chart` | Display charts in terminal | Renders various chart types (bar, line, pie, table) in the terminal using rich formatting |
| `show_image` | Display single image | Shows a single image inline in the terminal using rich |
| `show_image_grid` | Display image grid | Shows multiple images in a grid inline in the terminal |

## Usage Examples

### Creating a Bar Chart
```json
{
  "tool": "read_chart",
  "data": {
    "type": "bar",
    "data": {
      "labels": ["January", "February", "March"],
      "values": [65, 59, 80]
    }
  },
  "title": "Monthly Sales",
  "width": 80,
  "height": 20
}
```

### Displaying a Pie Chart
```json
{
  "tool": "read_chart",
  "data": {
    "type": "pie",
    "data": {
      "labels": ["Direct", "Referral", "Social"],
      "values": [55, 30, 15]
    }
  },
  "title": "Traffic Sources"
}
```

### Showing a Data Table
```json
{
  "tool": "read_chart",
  "data": {
    "type": "table",
    "data": {
      "headers": ["Name", "Age", "City"],
      "rows": [
        ["Alice", "25", "New York"],
        ["Bob", "30", "San Francisco"],
        ["Charlie", "35", "Chicago"]
      ]
    }
  },
  "title": "User Data"
}
```

## Configuration

This plugin does not require any specific configuration. Chart rendering uses default dimensions and styling.

Image Display tools (core.imagedisplay) have optional settings:
- default_width (int): Default width for image display
- default_height (int): Default height for image display
- preserve_aspect (bool): Preserve aspect ratio by default

## Security Considerations

- Chart data is rendered client-side with no external dependencies
- No data is transmitted to external services
- Large datasets are truncated to prevent performance issues

## Integration

The Visualization plugin integrates with the reporting system to provide:

- Data analysis and exploration
- Report generation with visual elements
- Interactive data exploration
- Performance metric visualization

This enables rich data presentation capabilities within the terminal interface, enhancing the user's ability to understand and interpret information.