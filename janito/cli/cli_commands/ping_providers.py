from janito.provider_registry import list_providers
from janito.providers.registry import LLMProviderRegistry
from janito.cli.console import shared_console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
import asyncio
import time


def handle_ping_providers(args):
    """Ping/test connectivity for all providers."""
    try:
        # Get all providers
        providers = list_providers()

        # Create table for results
        table = Table(title="Provider Connectivity Test")
        table.add_column("Provider", style="cyan")
        table.add_column("Status", style="magenta")
        table.add_column("Time", style="green")
        table.add_column("Details", style="yellow")

        # Test each provider
        for provider_name in providers:
            start_time = time.time()
            try:
                # Get provider class
                provider_class = LLMProviderRegistry.get(provider_name)
                provider = provider_class()

                # Test the provider (simplified - just check if we can instantiate and get models)
                models = provider.get_models()
                if models:
                    status = "✓ Connected"
                    details = f"{len(models)} models available"
                else:
                    status = "⚠ No models"
                    details = "Provider reachable but no models returned"

            except Exception as e:
                status = "✗ Failed"
                details = str(e)

            end_time = time.time()
            elapsed = f"{(end_time - start_time)*1000:.0f}ms"

            table.add_row(provider_name, status, elapsed, details)

        # Print results
        shared_console.print(table)

    except Exception as e:
        print(f"Error testing provider connectivity: {e}")

    return
