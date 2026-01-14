"""
CLI Command: List providers with configured authentication keys
"""

from rich.table import Table
from janito.cli.console import shared_console
from janito.llm.auth import LLMAuthManager
from janito.providers.registry import LLMProviderRegistry


def handle_list_auth(args=None):
    """List all providers that have API keys configured in auth.json."""
    auth_manager = LLMAuthManager()
    providers = LLMProviderRegistry.list_providers()
    
    # Create table
    table = Table(title="Providers with Configured Authentication")
    table.add_column("Provider", style="cyan")
    table.add_column("Status", style="green", justify="center")
    
    # Check each provider for configured auth
    has_auth = False
    for provider_name in sorted(providers):
        provider_class = LLMProviderRegistry.get(provider_name)
        api_key = auth_manager.get_credentials(provider_name)
        
        if api_key:
            # Mask the API key for security (show first 4 and last 4 chars)
            masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "****"
            table.add_row(provider_name, f"? {masked_key}")
            has_auth = True
    
    if not has_auth:
        shared_console.print("[yellow]No providers have configured authentication keys.[/yellow]")
        shared_console.print("\nTo set an API key for a provider, use:")
        shared_console.print("  janito --set-api-key YOUR_API_KEY -p PROVIDER")
    else:
        shared_console.print(table)
    
    return
