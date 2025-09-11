from janito.tools.tool_base import ToolBase, ToolPermissions
from janito.report_events import ReportAction
from janito.plugins.tools.local.adapter import register_local_tool
from janito.i18n import tr
from janito.tools.loop_protection_decorator import protect_against_loops
from typing import Sequence


@register_local_tool
class ShowImageGridTool(ToolBase):
    """Display multiple images in a grid inline in the terminal using rich.

    Args:
        paths (list[str]): List of image file paths.
        columns (int, optional): Number of columns in the grid. Default: 2.
        width (int, optional): Max width for each image cell. Default: None (auto).
        height (int, optional): Max height for each image cell. Default: None (auto).
        preserve_aspect (bool, optional): Preserve aspect ratio. Default: True.

    Returns:
        str: Status string summarizing the grid display.
    """

    permissions = ToolPermissions(read=True)
    tool_name = "show_image_grid"

    @protect_against_loops(max_calls=5, time_window=10.0, key_field="paths")
    def run(
        self,
        paths: Sequence[str],
        columns: int = 2,
        width: int | None = None,
        height: int | None = None,
        preserve_aspect: bool = True,
    ) -> str:
        from janito.tools.path_utils import expand_path
        from janito.tools.tool_utils import display_path
        import os

        try:
            from rich.console import Console
            from rich.columns import Columns
            from PIL import Image as PILImage
            from rich.panel import Panel
        except Exception as e:
            msg = tr("⚠️ Missing dependency: PIL/Pillow ({error})", error=e)
            self.report_error(msg)
            return msg

        if not paths:
            return tr("No images provided")

        self.report_action(tr("🖼️ Show image grid ({n} images)", n=len(paths)), ReportAction.READ)

        console = Console()
        images = []
        shown = 0
        
        # Import numpy for ASCII art conversion
        import numpy as np
        
        # Create ASCII art representation function
        def image_to_ascii(image, target_width=20, target_height=10):
            try:
                # Convert to grayscale and resize
                img_gray = image.convert('L')
                img_resized = img_gray.resize((target_width, target_height))
                
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
        
        for p in paths:
            fp = expand_path(p)
            if not os.path.exists(fp):
                self.report_warning(tr("❗ not found: {p}", p=display_path(fp)))
                continue
            try:
                img = PILImage.open(fp)
                
                # Create ASCII art preview
                ascii_art = image_to_ascii(img, 20, 10)
                
                if ascii_art:
                    from rich.text import Text
                    title_text = Text(f"{display_path(fp)}\n{img.width}×{img.height}", style="bold")
                    ascii_text = Text(ascii_art, style="dim")
                    combined_text = Text.assemble(title_text, "\n", ascii_text)
                    panel = Panel(combined_text, title="Image", border_style="dim")
                else:
                    # Fallback to just info if ASCII art fails
                    title = f"{display_path(fp)} ({img.width}x{img.height})"
                    panel = Panel.fit(title, title=display_path(fp), border_style="dim")
                
                images.append(panel)
                shown += 1
            except Exception as e:
                self.report_warning(tr("⚠️ Skipped {p}: {e}", p=display_path(fp), e=e))

        if not images:
            return tr("No images could be displayed")

        # Use manual column layout since Columns doesn't support columns parameter
        if columns > 1:
            # Group images into rows
            rows = []
            for i in range(0, len(images), columns):
                row_images = images[i:i+columns]
                rows.append(Columns(row_images, equal=True, expand=True))
            
            # Print all rows
            for row in rows:
                console.print(row)
        else:
            # Single column - print each image panel separately
            for image_panel in images:
                console.print(image_panel)
        self.report_success(tr("✅ Displayed {n} images", n=shown))
        return tr("Displayed {shown}/{total} images in a {cols}x? grid", shown=shown, total=len(paths), cols=columns)
