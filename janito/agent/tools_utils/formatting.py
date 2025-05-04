class OutlineFormatter:
    """
    Utility class for formatting code and markdown outlines into human-readable tables.
    """

    @staticmethod
    def format_outline_table(outline_items):
        """
        Format a list of code outline items (classes, functions, variables) into a table.

        Args:
            outline_items (list of dict): Each dict should contain keys: 'type', 'name', 'start', 'end', 'parent', 'docstring'.

        Returns:
            str: Formatted table as a string.
        """
        if not outline_items:
            return "No classes, functions, or variables found."
        header = "| Type    | Name        | Start | End | Parent   | Docstring                |\n|---------|-------------|-------|-----|----------|--------------------------|"
        rows = []
        for item in outline_items:
            docstring = item.get("docstring", "").replace("\n", " ")
            if len(docstring) > 24:
                docstring = docstring[:21] + "..."
            rows.append(
                f"| {item['type']:<7} | {item['name']:<11} | {item['start']:<5} | {item['end']:<3} | {item['parent']:<8} | {docstring:<24} |"
            )
        return header + "\n" + "\n".join(rows)

    @staticmethod
    def format_markdown_outline_table(outline_items):
        """
        Format a list of markdown outline items (headers) into a table.

        Args:
            outline_items (list of dict): Each dict should contain keys: 'level', 'title', 'line'.

        Returns:
            str: Formatted table as a string.
        """
        if not outline_items:
            return "No headers found."
        header = "| Level | Header                          | Line |\n|-------|----------------------------------|------|"
        rows = []
        for item in outline_items:
            rows.append(
                f"| {item['level']:<5} | {item['title']:<32} | {item['line']:<4} |"
            )
        return header + "\n" + "\n".join(rows)
