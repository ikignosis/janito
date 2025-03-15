"""
Module for generating token usage reports.
"""

from rich.console import Console
from claudine.token_tracking import MODEL_PRICING, DEFAULT_MODEL

def generate_token_report(agent, verbose=False):
    """
    Generate a token usage report.
    
    Args:
        agent: The Claude agent instance
        verbose: Whether to show detailed token usage information
        
    Returns:
        None - prints the report to the console
    """
    console = Console()
    usage = agent.get_token_usage()
    text_usage = usage.text_usage
    tools_usage = usage.tools_usage
    
    if verbose:
        total_usage = usage.total_usage
        
        # Get the pricing model
        pricing = MODEL_PRICING.get(DEFAULT_MODEL)
        
        # Calculate costs manually
        text_input_cost = pricing.input_tokens.calculate_cost(text_usage.input_tokens)
        text_output_cost = pricing.output_tokens.calculate_cost(text_usage.output_tokens)
        tools_input_cost = pricing.input_tokens.calculate_cost(tools_usage.input_tokens)
        tools_output_cost = pricing.output_tokens.calculate_cost(tools_usage.output_tokens)
        
        # Format costs
        format_cost = lambda cost: f"{cost * 100:.2f}¢" if cost < 1.0 else f"${cost:.6f}"
        
        console.print("\n[bold blue]Detailed Token Usage:[/bold blue]")
        console.print(f"Text Input tokens: {text_usage.input_tokens}")
        console.print(f"Text Output tokens: {text_usage.output_tokens}")
        console.print(f"Text Total tokens: {text_usage.input_tokens + text_usage.output_tokens}")
        console.print(f"Tool Input tokens: {tools_usage.input_tokens}")
        console.print(f"Tool Output tokens: {tools_usage.output_tokens}")
        console.print(f"Tool Total tokens: {tools_usage.input_tokens + tools_usage.output_tokens}")
        console.print(f"Total tokens: {total_usage.input_tokens + total_usage.output_tokens}")
        
        console.print("\n[bold blue]Pricing Information:[/bold blue]")
        console.print(f"Input pricing: ${pricing.input_tokens.cost_per_million_tokens}/million tokens")
        console.print(f"Output pricing: ${pricing.output_tokens.cost_per_million_tokens}/million tokens")
        console.print(f"Text Input cost: {format_cost(text_input_cost)}")
        console.print(f"Text Output cost: {format_cost(text_output_cost)}")
        console.print(f"Text Total cost: {format_cost(text_input_cost + text_output_cost)}")
        console.print(f"Tool Input cost: {format_cost(tools_input_cost)}")
        console.print(f"Tool Output cost: {format_cost(tools_output_cost)}")
        console.print(f"Tool Total cost: {format_cost(tools_input_cost + tools_output_cost)}")
        console.print(f"Total cost: {format_cost(text_input_cost + text_output_cost + tools_input_cost + tools_output_cost)}")

        # Display per-tool breakdown if available
        if usage.by_tool:
            console.print("\n[bold blue]Per-Tool Breakdown:[/bold blue]")
            for tool_name, tool_usage in usage.by_tool.items():
                tool_input_cost = pricing.input_tokens.calculate_cost(tool_usage.input_tokens)
                tool_output_cost = pricing.output_tokens.calculate_cost(tool_usage.output_tokens)
                console.print(f"   Tool: {tool_name}")
                console.print(f"  Input tokens: {tool_usage.input_tokens}")
                console.print(f"  Output tokens: {tool_usage.output_tokens}")
                console.print(f"  Total tokens: {tool_usage.input_tokens + tool_usage.output_tokens}")
                console.print(f"  Total cost: {format_cost(tool_input_cost + tool_output_cost)}")
    else:
        total_tokens = text_usage.input_tokens + text_usage.output_tokens + tools_usage.input_tokens + tools_usage.output_tokens
        cost_info = agent.get_cost()
        console.rule(f"[bold blue]Total tokens: {total_tokens} | Cost: {cost_info.format_total_cost()}[/bold blue]")
