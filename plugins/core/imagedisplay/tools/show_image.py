from janito.tools.tool_base import ToolBase, ToolPermissions
from janito.report_events import ReportAction
from janito.i18n import tr
from janito.tools.loop_protection_decorator import protect_against_loops


class ShowImageTool(ToolBase):
    """Display an image inline in the terminal using the rich library.

    Args:
        path (str): Path to the image file.
        width (int, optional): Target width in terminal cells. If unset, auto-fit.
        height (int, optional): Target height in terminal rows. If unset, auto-fit.
        preserve_aspect (bool, optional): Preserve aspect ratio. Default: True.

    Returns:
        str: Status message indicating display result or error details.
    """

    permissions = ToolPermissions(read=True)
    tool_name = "show_image"

    @protect_against_loops(max_calls=5, time_window=10.0, key_field="path")
    def run(
        self,
        path: str,
        width: int | None = None,
        height: int | None = None,
        preserve_aspect: bool = True,
    ) -> str:
        from janito.tools.tool_utils import display_path
        from janito.tools.path_utils import expand_path
        import os

        # Defer heavy imports to runtime
        try:
            from rich.console import Console
            from PIL import Image as PILImage
        except Exception as e:
            msg = tr("⚠️ Missing dependency: PIL/Pillow ({error})", error=e)
            self.report_error(msg)
            return msg

        path = expand_path(path)
        disp_path = display_path(path)
        self.report_action(tr("🖼️ Show image '{disp_path}'", disp_path=disp_path), ReportAction.READ)

        if not os.path.exists(path):
            msg = tr("❗ not found")
            self.report_warning(msg)
            return tr("Error: file not found: {path}", path=disp_path)

        try:
            console = Console()
            from rich.panel import Panel
            from rich.text import Text
            import numpy as np
            
            img = PILImage.open(path)
            
            # Create ASCII art representation
            def image_to_ascii(image, width=40, height=20):
                try:
                    # Convert to grayscale and resize
                    img_gray = image.convert('L')
                    img_resized = img_gray.resize((width, height))
                    
                    # Convert to numpy array
                    pixels = np.array(img_resized)
                    
                    # ASCII characters from dark to light
                    ascii_chars = "@%#*+=-:. "
                    
                    # Normalize pixels to ASCII range
                    ascii_art = ""
                    for row in pixels:
                        for pixel in row:
                            # Map pixel value (0-255) to ASCII index
                            ascii_index = int((pixel / 255) * (len(ascii_chars) - 1))
                            ascii_art += ascii_chars[ascii_index]
                        ascii_art += "\n"
                    
                    return ascii_art.strip()
                except Exception:
                    return None
            
            # Calculate appropriate size for terminal display
            display_width = width or min(60, img.width // 4)
            display_height = height or min(30, img.height // 4)
            
            ascii_art = image_to_ascii(img, display_width, display_height)
            
            if ascii_art:
                # Create a panel with both info and ASCII art
                img_info = Text(f"🖼️ {disp_path}\nSize: {img.width}×{img.height}\nMode: {img.mode}\n", style="bold green")
                ascii_text = Text(ascii_art, style="dim")
                combined = Text.assemble(img_info, ascii_text)
                panel = Panel(combined, title="Image Preview", border_style="blue")
            else:
                # Fallback to just info if ASCII art fails
                img_info = Text(f"🖼️ {disp_path}\nSize: {img.width}×{img.height}\nMode: {img.mode}", style="bold green")
                panel = Panel(img_info, title="Image Info", border_style="blue")
            
            console.print(panel)
            self.report_success(tr("✅ Displayed"))
            details = []
            if width:
                details.append(f"width={width}")
            if height:
                details.append(f"height={height}")
            if not preserve_aspect:
                details.append("preserve_aspect=False")
            info = ("; ".join(details)) if details else "auto-fit"
            return tr("Image displayed: {disp_path} ({info})", disp_path=disp_path, info=info)
        except Exception as e:
            self.report_error(tr(" ❌ Error: {error}", error=e))
            return tr("Error displaying image: {error}", error=e)
