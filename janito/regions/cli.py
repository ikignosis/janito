"""
CLI commands for region management and geolocation utilities.
"""

import argparse
import json
from typing import Optional

from .geo_utils import get_region_info
from .provider_regions import (
    get_provider_regions,
    get_optimal_endpoint,
    get_all_providers,
)


def handle_region_info(args=None):
    """Display current region information."""
    info = get_region_info()
    print(json.dumps(info, indent=2))


def handle_provider_regions(args):
    """Display regions for a specific provider."""
    provider = args.provider.lower()
    regions = get_provider_regions(provider)

    if not regions:
        print(f"Provider '{provider}' not found")
        return

    result = {
        "provider": provider,
        "regions": [
            {
                "code": r.region_code,
                "name": r.name,
                "endpoint": r.endpoint,
                "location": r.location,
                "priority": r.priority,
            }
            for r in regions
        ],
    }
    print(json.dumps(result, indent=2))


def handle_optimal_endpoint(args):
    """Get optimal endpoint for a provider based on user location."""
    from .geo_utils import get_user_location, get_closest_region

    country_code, _ = get_user_location()
    major_region = get_closest_region(country_code)

    provider = args.provider.lower()
    endpoint = get_optimal_endpoint(provider, major_region)

    if not endpoint:
        print(f"Provider '{provider}' not found")
        return

    result = {
        "provider": provider,
        "user_region": major_region,
        "country_code": country_code,
        "optimal_endpoint": endpoint,
    }
    print(json.dumps(result, indent=2))


def handle_list_providers(args=None):
    """List all supported providers."""
    providers = get_all_providers()
    result = {"providers": providers, "count": len(providers)}
    print(json.dumps(result, indent=2))


def setup_region_parser(subparsers):
    """Setup region-related CLI commands."""
    region_parser = subparsers.add_parser(
        "region", help="Region and geolocation utilities"
    )
    region_subparsers = region_parser.add_subparsers(
        dest="region_command", help="Region commands"
    )

    # region info
    info_parser = region_subparsers.add_parser(
        "info", help="Show current region information"
    )
    info_parser.set_defaults(func=handle_region_info)

    # region providers
    providers_parser = region_subparsers.add_parser(
        "providers", help="List all supported providers"
    )
    providers_parser.set_defaults(func=handle_list_providers)

    # region list
    list_parser = region_subparsers.add_parser(
        "list", help="List regions for a provider"
    )
    list_parser.add_argument("provider", help="Provider name (e.g., openai, anthropic)")
    list_parser.set_defaults(func=handle_provider_regions)

    # region endpoint
    endpoint_parser = region_subparsers.add_parser(
        "endpoint", help="Get optimal endpoint for provider"
    )
    endpoint_parser.add_argument(
        "provider", help="Provider name (e.g., openai, anthropic)"
    )
    endpoint_parser.set_defaults(func=handle_optimal_endpoint)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Region utilities")
    setup_region_parser(parser.add_subparsers(dest="command"))

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()
