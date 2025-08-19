"""
CLI Command: List providers with their regional API information
"""

import json
from typing import Dict, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from janito.regions.provider_regions import PROVIDER_REGIONS, get_all_providers
from janito.regions.geo_utils import get_region_info

console = Console()


def handle_list_providers_region(args=None):
    """List all providers with their regional API information."""

    # Get user location info
    user_info = get_region_info()
    user_region = user_info["major_region"]

    # Get all providers
    providers = get_all_providers()

    # Create table
    table = Table(title="LLM Providers by Region")
    table.add_column("Provider", style="cyan", no_wrap=True)
    table.add_column("Region", style="green")
    table.add_column("Endpoint", style="bright_white")

    for provider in sorted(providers):
        regions = PROVIDER_REGIONS.get(provider, [])
        if not regions:
            table.add_row(provider, "N/A", "N/A", "N/A", "N/A")
            continue

        # Find the best region for the user
        best_region = None
        for region in regions:
            if region.region_code.startswith(user_region):
                best_region = region
                break

        # If no exact match, use first available
        if not best_region:
            best_region = regions[0]

        # Extract 2-letter region code
        if provider == "azure-openai":
            region_code = "ALL"
        else:
            region_code = (
                user_region
                if any(r.region_code.startswith(user_region) for r in regions)
                else (
                    "APAC"
                    if best_region.region_code == "ASIA-PACIFIC"
                    else best_region.region_code[:2]
                )
            )

        table.add_row(
            provider,
            region_code,
            best_region.endpoint,
        )

    console.print(table)

    # Show user location info
    console.print(
        f"\n[dim]Your location: {user_info['country_code']} ({user_region})[/dim]"
    )
    console.print(f"[dim]Detection source: {user_info['source']}[/dim]")

    # Show region mapping info
    console.print(
        "\n[dim]Regions: US (United States), EU (Europe), CN (China), CH (Switzerland), APAC (Asia Pacific)[/dim]"
    )


if __name__ == "__main__":
    handle_list_providers_region()
