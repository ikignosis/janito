#!/usr/bin/env python3
"""
Example showing how to add loop protection to a custom tool.

This example demonstrates how to create a custom tool with loop protection
using the @protect_against_loops decorator.
"""

from janito.tools.tool_base import ToolBase, ToolPermissions
from janito.tools.loop_protection_decorator import protect_against_loops
from janito.tools.adapters.local.adapter import register_local_tool


@register_local_tool
class CustomFileAnalyzerTool(ToolBase):
    """
    Example custom tool that analyzes files with loop protection.

    This tool demonstrates how to use the @protect_against_loops decorator
    to prevent excessive operations on the same file.
    """

    permissions = ToolPermissions(read=True)
    tool_name = "custom_file_analyzer"

    @protect_against_loops(max_calls=5, time_window=10.0)
    def run(self, path: str, analysis_type: str = "basic") -> str:
        """
        Analyze a file with the specified analysis type.

        Args:
            path (str): Path to the file to analyze
            analysis_type (str): Type of analysis to perform ("basic" or "detailed")

        Returns:
            str: Analysis results
        """
        self.report_action(f"Analyzing '{path}' with {analysis_type} analysis")

        try:
            # Simulate file analysis
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            # Perform analysis based on type
            if analysis_type == "basic":
                lines = len(content.splitlines())
                words = len(content.split())
                chars = len(content)
                result = f"Basic analysis of {path}:\n"
                result += f"  Lines: {lines}\n"
                result += f"  Words: {words}\n"
                result += f"  Characters: {chars}\n"
            else:
                # Detailed analysis could include more metrics
                result = f"Detailed analysis of {path}:\n"
                result += f"  Content preview: {content[:100]}...\n"

            self.report_success(f"Analysis of {path} completed")
            return result

        except FileNotFoundError:
            self.report_error(f"File not found: {path}")
            return f"Error: File '{path}' not found"
        except Exception as e:
            self.report_error(f"Error analyzing {path}: {e}")
            return f"Error analyzing file: {e}"


@register_local_tool
class BatchFileProcessorTool(ToolBase):
    """
    Example tool that processes multiple files with loop protection.

    This tool demonstrates how to use the @protect_against_loops decorator
    with tools that operate on multiple files.
    """

    permissions = ToolPermissions(read=True)
    tool_name = "batch_file_processor"

    @protect_against_loops(max_calls=5, time_window=10.0)
    def run(self, file_paths: list, operation: str = "count") -> str:
        """
        Process multiple files with the specified operation.

        Args:
            file_paths (list): List of file paths to process
            operation (str): Operation to perform ("count", "uppercase", etc.)

        Returns:
            str: Processing results
        """
        self.report_action(
            f"Processing {len(file_paths)} files with {operation} operation"
        )

        results = []
        for path in file_paths:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()

                if operation == "count":
                    lines = len(content.splitlines())
                    words = len(content.split())
                    results.append(f"{path}: {lines} lines, {words} words")
                elif operation == "uppercase":
                    results.append(f"{path}: {content.upper()}")

            except FileNotFoundError:
                results.append(f"{path}: File not found")
            except Exception as e:
                results.append(f"{path}: Error - {e}")

        self.report_success(f"Processed {len(file_paths)} files")
        return "\n".join(results)


def usage_examples():
    """Show how to use the custom tools with loop protection."""
    print("=== Custom Tool with Loop Protection Examples ===\n")
    print("Example 1: CustomFileAnalyzerTool")
    print("  @protect_against_loops()")
    print("  def run(self, path: str, analysis_type: str = 'basic') -> str:")
    print("      # Implementation here")
    print()

    print("Example 2: BatchFileProcessorTool")
    print("  @protect_against_loops('file_paths')")
    print("  def run(self, file_paths: list, operation: str = 'count') -> str:")
    print("      # Implementation here")
    print()

    print("To use these tools in your application:")
    print("1. Import the tool classes")
    print("2. Register them with the tools adapter")
    print("3. Call them like any other tool")
    print()
    print("The loop protection will automatically prevent:")
    print("- More than 5 operations on the same file within 10 seconds")
    print("- Excessive resource consumption from repeated file access")
    print("- Potential infinite loops in tool execution")


if __name__ == "__main__":
    usage_examples()
