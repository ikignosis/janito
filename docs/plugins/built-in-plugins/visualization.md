# Visualization Plugin

## Overview

The Visualization plugin provides data visualization and charting capabilities. This plugin enables the display of data in various visual formats, making it easier to understand and analyze information.

## Resources Provided

### Tools

| Tool Name | Function | Description |
|-----------|----------|-------------|

| `show_image` | Display single image | Shows a single image inline in the terminal using rich |
| `show_image_grid` | Display image grid | Shows multiple images in a grid inline in the terminal |

## Usage Examples

### Displaying an Image
```json
{
  "tool": "show_image",
  "path": "chart.png",
  "width": 80,
  "preserve_aspect": true
}
```

### Creating an Image Grid
```json
{
  "tool": "show_image_grid",
  "paths": ["image1.png", "image2.png", "image3.png"],
  "columns": 2,
  "width": 40
}
```




## Configuration

This plugin does not require any specific configuration. Image display uses default dimensions and styling.


## Security Considerations

- Images are displayed client-side with no external dependencies
- No data is transmitted to external services
- Large images are resized to prevent performance issues

## Integration

The Visualization plugin provides image display capabilities for:

- Visual content presentation
- Multi-image comparisons
- Documentation with visual elements
- Terminal-based image viewing

This enables rich visual presentation capabilities within the terminal interface.