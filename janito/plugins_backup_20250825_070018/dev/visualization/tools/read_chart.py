from janito.tools.tool_base import ToolBase, ToolPermissions
from janito.report_events import ReportAction
from janito.tools.adapters.local.adapter import register_local_tool
from janito.tools.tool_utils import display_path
from janito.i18n import tr
import json
import os
from janito.tools.loop_protection_decorator import protect_against_loops


@register_local_tool
class ReadChartTool(ToolBase):
    """
    Display charts and data visualizations in the terminal using rich.

    Args:
        data (dict): Chart data in JSON format. Should contain 'type' (bar, line, pie, table) and 'data' keys.
        title (str, optional): Chart title. Defaults to "Chart".
        width (int, optional): Chart width. Defaults to 80.
        height (int, optional): Chart height. Defaults to 20.

    Returns:
        str: Formatted chart display in terminal or error message.
    """

    permissions = ToolPermissions(read=True)
    tool_name = "read_chart"

    @protect_against_loops(max_calls=5, time_window=10.0, key_field="data")
    def run(
        self, data: dict, title: str = "Chart", width: int = 80, height: int = 20
    ) -> str:
        try:
            from rich.console import Console
            from rich.table import Table
            from rich.text import Text
            from rich.layout import Layout
            from rich.panel import Panel
            from rich.columns import Columns
            from rich import box

            console = Console(width=width)

            if not isinstance(data, dict):
                return "❌ Error: Data must be a dictionary"

            chart_type = data.get("type", "table").lower()
            chart_data = data.get("data", [])

            if not chart_data:
                return "⚠️ Warning: No data provided for chart"

            self.report_action(
                tr(
                    "📊 Displaying {chart_type} chart: {title}",
                    chart_type=chart_type,
                    title=title,
                ),
                ReportAction.READ,
            )

            if chart_type == "table":
                return self._display_table(console, chart_data, title, width)
            elif chart_type == "bar":
                return self._display_bar(console, chart_data, title, width, height)
            elif chart_type == "line":
                return self._display_line(console, chart_data, title, width, height)
            elif chart_type == "pie":
                return self._display_pie(console, chart_data, title, width)
            else:
                return f"❌ Error: Unsupported chart type '{chart_type}'. Use: table, bar, line, pie"

        except ImportError:
            return "❌ Error: rich library not available for chart display"
        except Exception as e:
            return f"❌ Error displaying chart: {e}"

    def _display_table(self, console, data, title, width):
        """Display data as a rich table."""
        from rich.table import Table

        if not data:
            return "No data to display"

        table = Table(title=title, show_header=True, header_style="bold magenta")

        # Handle different data formats
        if isinstance(data, dict):
            # Dictionary format: key-value pairs
            table.add_column("Key", style="cyan")
            table.add_column("Value", style="green")
            for key, value in data.items():
                table.add_row(str(key), str(value))
        elif isinstance(data, list):
            if data and isinstance(data[0], dict):
                # List of dictionaries (records)
                headers = list(data[0].keys()) if data else []
                for header in headers:
                    table.add_column(str(header).title(), style="cyan")
                for row in data:
                    table.add_row(*[str(row.get(h, "")) for h in headers])
            else:
                # Simple list
                table.add_column("Items", style="cyan")
                for item in data:
                    table.add_row(str(item))

        console.print(table)
        return f"✅ Table chart displayed: {title}"

    def _display_bar(self, console, data, title, width, height):
        """Display data as a simple bar chart using unicode blocks."""
        try:
            if isinstance(data, dict):
                items = list(data.items())
            elif isinstance(data, list) and data and isinstance(data[0], dict):
                # Assume first two keys are labels and values
                keys = list(data[0].keys())
                if len(keys) >= 2:
                    label_key, value_key = keys[0], keys[1]
                    items = [(item[label_key], item[value_key]) for item in data]
                else:
                    items = [(str(i), v) for i, v in enumerate(data)]
            else:
                items = [(str(i), v) for i, v in enumerate(data)]

            if not items:
                return "No data to display"

            # Convert values to numbers
            numeric_items = []
            for label, value in items:
                try:
                    numeric_items.append((str(label), float(value)))
                except (ValueError, TypeError):
                    numeric_items.append((str(label), 0.0))

            if not numeric_items:
                return "No valid numeric data to display"

            max_val = max(val for _, val in numeric_items) if numeric_items else 1

            console.print(f"\n[bold]{title}[/bold]")
            console.print("=" * min(len(title), width))

            for label, value in numeric_items:
                bar_length = int((value / max_val) * (width - 20)) if max_val > 0 else 0
                bar = "█" * bar_length
                console.print(f"{label:<15} {bar} {value:.1f}")

            return f"✅ Bar chart displayed: {title}"

        except Exception as e:
            return f"❌ Error displaying bar chart: {e}"

    def _display_line(self, console, data, title, width, height):
        """Display data as a simple line chart using unicode characters."""
        try:
            if isinstance(data, dict):
                items = list(data.items())
            elif isinstance(data, list):
                if data and isinstance(data[0], dict):
                    keys = list(data[0].keys())
                    if len(keys) >= 2:
                        label_key, value_key = keys[0], keys[1]
                        items = [(item[label_key], item[value_key]) for item in data]
                    else:
                        items = [(str(i), v) for i, v in enumerate(data)]
                else:
                    items = [(str(i), v) for i, v in enumerate(data)]
            else:
                return "Unsupported data format"

            # Convert to numeric values
            points = []
            for x, y in items:
                try:
                    points.append((float(x), float(y)))
                except (ValueError, TypeError):
                    continue

            if len(points) < 2:
                return "Need at least 2 data points for line chart"

            points.sort(key=lambda p: p[0])

            # Simple ASCII line chart
            min_x, max_x = min(p[0] for p in points), max(p[0] for p in points)
            min_y, max_y = min(p[1] for p in points), max(p[1] for p in points)

            if max_x == min_x or max_y == min_y:
                return "Cannot display line chart: all values are the same"

            console.print(f"\n[bold]{title}[/bold]")
            console.print("=" * min(len(title), width))

            # Simple representation
            for x, y in points:
                x_norm = int(((x - min_x) / (max_x - min_x)) * (width - 20))
                y_norm = int(((y - min_y) / (max_y - min_y)) * 10)
                line = " " * x_norm + "●" + " " * (width - 20 - x_norm)
                console.print(f"{x:>8.1f}: {line} {y:.1f}")

            return f"✅ Line chart displayed: {title}"

        except Exception as e:
            return f"❌ Error displaying line chart: {e}"

    def _display_pie(self, console, data, title, width):
        """Display data as a simple pie chart representation."""
        try:
            if isinstance(data, dict):
                items = list(data.items())
            elif isinstance(data, list) and data and isinstance(data[0], dict):
                keys = list(data[0].keys())
                if len(keys) >= 2:
                    label_key, value_key = keys[0], keys[1]
                    items = [(item[label_key], item[value_key]) for item in data]
                else:
                    items = [(str(i), v) for i, v in enumerate(data)]
            else:
                items = [(str(i), v) for i, v in enumerate(data)]

            # Convert to numeric values
            values = []
            for label, value in items:
                try:
                    values.append((str(label), float(value)))
                except (ValueError, TypeError):
                    continue

            if not values:
                return "No valid numeric data to display"

            total = sum(val for _, val in values)
            if total == 0:
                return "Cannot display pie chart: total is zero"

            console.print(f"\n[bold]{title}[/bold]")
            console.print("=" * min(len(title), width))

            # Unicode pie chart segments
            segments = ["🟦", "🟥", "🟩", "🟨", "🟪", "🟧", "⬛", "⬜"]

            for i, (label, value) in enumerate(values):
                percentage = (value / total) * 100
                segment = segments[i % len(segments)]
                bar_length = int((value / total) * (width - 30))
                bar = "█" * bar_length
                console.print(
                    f"{segment} {label:<15} {bar} {percentage:5.1f}% ({value})"
                )

            console.print(f"\n[dim]Total: {total}[/dim]")

            return f"✅ Pie chart displayed: {title}"

        except Exception as e:
            return f"❌ Error displaying pie chart: {e}"
