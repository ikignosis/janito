"""
Region definitions and geolocation utilities for LLM providers.

This module provides static region definitions for various LLM providers
and utilities to determine optimal API endpoints based on user location.
"""

from .provider_regions import PROVIDER_REGIONS, get_optimal_endpoint
from .geo_utils import get_user_location, get_closest_region

__all__ = [
    "PROVIDER_REGIONS",
    "get_optimal_endpoint",
    "get_user_location",
    "get_closest_region",
]
