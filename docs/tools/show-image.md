# show_image

Display an image inline in the terminal using the rich library.

## Terminal Compatibility

Image display requires a terminal that supports inline image rendering. **Windows Terminal is the primary supported terminal** for the best image display experience. Other modern terminals with image support may also work, but results can vary depending on terminal capabilities and configuration.

Arguments:
- path (str): Path to the image file.
- width (int, optional): Target width in terminal cells. If unset, auto-fit.
- height (int, optional): Target height in terminal rows. If unset, auto-fit.
- preserve_aspect (bool, optional): Preserve aspect ratio. Default: True.

Returns:
- Status message indicating display result or error details.

Example Usage:
- show a PNG: `show_image(path="img/tux.png", width=60)`
- auto-fit: `show_image(path="~/Pictures/photo.jpg")`
