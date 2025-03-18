"""
Module for generating token usage reports.
"""

from rich.console import Console

def generate_token_report(agent, verbose=False, interrupted=False):
    """
    Generate a token usage report.
    
    Args:
        agent: The Claude agent instance
        verbose: Whether to show detailed token usage information
        interrupted: Whether the request was interrupted
        
    Returns:
        None - prints the report to the console
    """
    console = Console()
    usage = agent.get_tokens()
    cost = agent.get_token_cost()
    
    text_usage = usage.text_usage
    tools_usage = usage.tools_usage
    
    if verbose:
        total_usage = usage.total_usage
        
        # Get costs from the cost object
        text_input_cost = cost.input_cost
        text_output_cost = cost.output_cost
        text_cache_creation_cost = cost.cache_creation_cost
        text_cache_read_cost = cost.cache_read_cost
        
        tools_input_cost = cost.input_cost
        tools_output_cost = cost.output_cost
        tools_cache_creation_cost = cost.cache_creation_cost
        tools_cache_read_cost = cost.cache_read_cost
        
        # Format costs
        def format_cost(cost):
            return f"{cost * 100:.2f}¢" if cost < 1.0 else f"${cost:.6f}"
        
        console.print("\n[bold blue]📊 Detailed Token Usage:[/bold blue]")
        console.print(f"📝 Text Input tokens: {text_usage.input_tokens}")
        console.print(f"📤 Text Output tokens: {text_usage.output_tokens}")
        console.print(f"💾 Text Cache Creation tokens: {text_usage.cache_creation_input_tokens}")
        console.print(f"📖 Text Cache Read tokens: {text_usage.cache_read_input_tokens}")
        console.print(f"📋 Text Total tokens: {text_usage.input_tokens + text_usage.output_tokens + text_usage.cache_creation_input_tokens + text_usage.cache_read_input_tokens}")
        
        console.print(f"🔧 Tool Input tokens: {tools_usage.input_tokens}")
        console.print(f"🔨 Tool Output tokens: {tools_usage.output_tokens}")
        console.print(f"💾 Tool Cache Creation tokens: {tools_usage.cache_creation_input_tokens}")
        console.print(f"📖 Tool Cache Read tokens: {tools_usage.cache_read_input_tokens}")
        console.print(f"🧰 Tool Total tokens: {tools_usage.input_tokens + tools_usage.output_tokens + tools_usage.cache_creation_input_tokens + tools_usage.cache_read_input_tokens}")
        
        console.print(f"🔢 Total tokens: {total_usage.input_tokens + total_usage.output_tokens + total_usage.cache_creation_input_tokens + total_usage.cache_read_input_tokens}")
        
        console.print("\n[bold blue]💰 Pricing Information:[/bold blue]")
        console.print(f"📝 Text Input cost: {format_cost(text_input_cost)}")
        console.print(f"📤 Text Output cost: {format_cost(text_output_cost)}")
        console.print(f"💾 Text Cache Creation cost: {format_cost(text_cache_creation_cost)}")
        console.print(f"📖 Text Cache Read cost: {format_cost(text_cache_read_cost)}")
        console.print(f"📋 Text Total cost: {format_cost(text_input_cost + text_output_cost + text_cache_creation_cost + text_cache_read_cost)}")
        
        console.print(f"🔧 Tool Input cost: {format_cost(tools_input_cost)}")
        console.print(f"🔨 Tool Output cost: {format_cost(tools_output_cost)}")
        console.print(f"💾 Tool Cache Creation cost: {format_cost(tools_cache_creation_cost)}")
        console.print(f"📖 Tool Cache Read cost: {format_cost(tools_cache_read_cost)}")
        console.print(f"🧰 Tool Total cost: {format_cost(tools_input_cost + tools_output_cost + tools_cache_creation_cost + tools_cache_read_cost)}")
        
        total_cost_text = f"💵 Total cost: {format_cost(text_input_cost + text_output_cost + text_cache_creation_cost + text_cache_read_cost + tools_input_cost + tools_output_cost + tools_cache_creation_cost + tools_cache_read_cost)}"
        if interrupted:
            total_cost_text += " (interrupted request not accounted)"
        console.print(total_cost_text)
        
        # Show cache delta if available
        if hasattr(cost, 'cache_delta') and cost.cache_delta:
            cache_delta = cost.cache_delta
            console.print(f"\n[bold green]💰 Cache Savings:[/bold green] {format_cost(cache_delta)}")
            
            # Calculate percentage savings
            total_cost_without_cache = cost.total_cost + cache_delta
            if total_cost_without_cache > 0:
                savings_percentage = (cache_delta / total_cost_without_cache) * 100
                console.print(f"[bold green]📊 Cache Savings Percentage:[/bold green] {savings_percentage:.2f}%")
                console.print(f"[bold green]💸 Cost without cache:[/bold green] {format_cost(total_cost_without_cache)}")
                console.print(f"[bold green]💲 Cost with cache:[/bold green] {format_cost(cost.total_cost)}")
            
        # Per-tool breakdown
        if usage.by_tool:
            console.print("\n[bold blue]🔧 Per-Tool Breakdown:[/bold blue]")
            try:
                if hasattr(cost, 'by_tool') and cost.by_tool:
                    for tool_name, tool_usage in usage.by_tool.items():
                        tool_input_cost = cost.by_tool[tool_name].input_cost
                        tool_output_cost = cost.by_tool[tool_name].output_cost
                        tool_cache_creation_cost = cost.by_tool[tool_name].cache_creation_cost
                        tool_cache_read_cost = cost.by_tool[tool_name].cache_read_cost
                        tool_total_cost = tool_input_cost + tool_output_cost + tool_cache_creation_cost + tool_cache_read_cost
                        
                        console.print(f"   🔧 Tool: {tool_name}")
                        console.print(f"  📥 Input tokens: {tool_usage.input_tokens}")
                        console.print(f"  📤 Output tokens: {tool_usage.output_tokens}")
                        console.print(f"  💾 Cache Creation tokens: {tool_usage.cache_creation_input_tokens}")
                        console.print(f"  📖 Cache Read tokens: {tool_usage.cache_read_input_tokens}")
                        console.print(f"  🔢 Total tokens: {tool_usage.input_tokens + tool_usage.output_tokens + tool_usage.cache_creation_input_tokens + tool_usage.cache_read_input_tokens}")
                        console.print(f"  💵 Total cost: {format_cost(tool_total_cost)}")
                else:
                    # Calculate costs manually for each tool if cost.by_tool is not available
                    for tool_name, tool_usage in usage.by_tool.items():
                        # Estimate costs based on overall pricing
                        total_tokens = tool_usage.input_tokens + tool_usage.output_tokens + tool_usage.cache_creation_input_tokens + tool_usage.cache_read_input_tokens
                        estimated_cost = (total_tokens / (usage.total_usage.total_tokens + usage.total_usage.total_cache_tokens)) * cost.total_cost if usage.total_usage.total_tokens > 0 else 0
                        
                        console.print(f"   🔧 Tool: {tool_name}")
                        console.print(f"  📥 Input tokens: {tool_usage.input_tokens}")
                        console.print(f"  📤 Output tokens: {tool_usage.output_tokens}")
                        console.print(f"  💾 Cache Creation tokens: {tool_usage.cache_creation_input_tokens}")
                        console.print(f"  📖 Cache Read tokens: {tool_usage.cache_read_input_tokens}")
                        console.print(f"  🔢 Total tokens: {tool_usage.input_tokens + tool_usage.output_tokens + tool_usage.cache_creation_input_tokens + tool_usage.cache_read_input_tokens}")
                        console.print(f"  💵 Total cost: {format_cost(estimated_cost)}")
            except Exception as e:
                console.print(f"❌ Error: {str(e)}")
    else:
        total_tokens = (text_usage.input_tokens + text_usage.output_tokens + 
                       text_usage.cache_creation_input_tokens + text_usage.cache_read_input_tokens +
                       tools_usage.input_tokens + tools_usage.output_tokens +
                       tools_usage.cache_creation_input_tokens + tools_usage.cache_read_input_tokens)
        
        # Format costs
        def format_cost(cost):
            return f"{cost * 100:.2f}¢" if cost < 1.0 else f"${cost:.6f}"
        
        # Prepare summary message
        cost_text = f"Cost: {format_cost(cost.total_cost)}"
        if interrupted:
            cost_text += " (interrupted request not accounted)"
            
        summary = f"Total tokens: {total_tokens} | {cost_text}"
        
        # Add cache savings if available
        if hasattr(cost, 'cache_delta') and cost.cache_delta != 0:
            cache_delta = cost.cache_delta
            total_cost_without_cache = cost.total_cost + cache_delta
            savings_percentage = 0
            if total_cost_without_cache > 0:
                savings_percentage = (cache_delta / total_cost_without_cache) * 100
            
            summary += f" | Cache savings: {format_cost(cache_delta)} ({savings_percentage:.1f}%)"
        
        # Display with a rule
        console.rule("[blue]Token Usage[/blue]")
        console.print(f"[blue]{summary}[/blue]", justify="center")
