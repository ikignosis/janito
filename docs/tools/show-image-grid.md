# show_image_grid

Display multiple images in a grid inline in the terminal using rich.

Arguments:

- paths (list[str]): List of image file paths.
- columns (int, optional): Number of columns in the grid. Default: 2.
- width (int, optional): Max width for each image cell. Default: None (auto).
- height (int, optional): Max height for each image cell. Default: None (auto).
- preserve_aspect (bool, optional): Preserve aspect ratio. Default: True.

Returns:

- Status string summarizing the grid display.

Example Usage:

- `show_image_grid(paths=["img/tux.png", "img/tux_display.png"], columns=2, width=40)`
