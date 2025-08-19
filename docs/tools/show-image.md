# show_image

Display an image inline in the terminal using the rich library.

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
