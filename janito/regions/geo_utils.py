"""
Geolocation utilities for determining user location and optimal regions.

This module provides utilities to detect user location and determine
optimal API regions based on geographic proximity.
"""

import os
import json
import subprocess
import sys
from typing import Optional, Tuple
from pathlib import Path


def _get_geoip_location() -> Optional[str]:
    """Try to get location using geoip2 if available."""
    try:
        import geoip2.database
        import geoip2.errors
        import urllib.request

        # Common GeoIP database locations
        db_paths = [
            "/usr/share/GeoIP/GeoLite2-City.mmdb",
            "/var/lib/GeoIP/GeoLite2-City.mmdb",
            str(Path.home() / ".local/share/GeoIP/GeoLite2-City.mmdb"),
        ]

        for db_path in db_paths:
            if Path(db_path).exists():
                reader = geoip2.database.Reader(db_path)
                try:
                    with urllib.request.urlopen(
                        "https://api.ipify.org", timeout=2
                    ) as response:
                        ip = response.read().decode().strip()

                    response = reader.city(ip)
                    country_code = response.country.iso_code
                    reader.close()

                    if country_code:
                        return country_code.upper()
                except Exception:
                    reader.close()
                    continue
    except (ImportError, Exception):
        pass
    return None


def _get_ipinfo_location() -> Optional[str]:
    """Try to get location using ipinfo.io via curl."""
    try:
        import subprocess

        result = subprocess.run(
            ["curl", "-s", "https://ipinfo.io/country"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().upper()
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass
    return None


def _get_locale_location() -> Optional[str]:
    """Try to get location from system locale."""
    try:
        import locale

        loc = locale.getdefaultlocale()[0]
        if loc:
            parts = loc.split("_")
            if len(parts) > 1:
                return parts[-1].upper()
    except Exception:
        pass
    return None


def get_user_location() -> Tuple[str, str]:
    """
    Detect user's location using geoip lookup.

    Returns:
        Tuple of (country_code, region_name)

    Note:
        This is a best-effort detection. Falls back to environment variables
        or defaults to 'US' if detection fails.
    """
    # Try environment variable first
    user_region = os.getenv("JANITO_REGION")
    if user_region:
        return user_region.upper(), f"Environment: {user_region}"

    # Try different detection methods
    country_code = (
        _get_geoip_location()
        or _get_ipinfo_location()
        or _get_locale_location()
        or "US"
    )

    source = (
        "GeoIP"
        if _get_geoip_location()
        else (
            "ipinfo.io"
            if _get_ipinfo_location()
            else ("Locale" if _get_locale_location() else "Default")
        )
    )

    return country_code, f"{source}: {country_code}"


def get_closest_region(country_code: str) -> str:
    """
    Map country code to closest major region.

    Args:
        country_code: ISO country code (e.g., 'US', 'DE', 'CN')

    Returns:
        Major region identifier (US, EU, CN, CH, ASIA)
    """
    country_code = country_code.upper()

    # US and Americas
    if country_code in ["US", "CA", "MX", "BR", "AR", "CL", "CO", "PE"]:
        return "US"

    # European Union and Europe
    if country_code in [
        "AT",
        "BE",
        "BG",
        "HR",
        "CY",
        "CZ",
        "DK",
        "EE",
        "FI",
        "FR",
        "DE",
        "GR",
        "HU",
        "IE",
        "IT",
        "LV",
        "LT",
        "LU",
        "MT",
        "NL",
        "PL",
        "PT",
        "RO",
        "SK",
        "SI",
        "ES",
        "SE",
        "GB",
        "NO",
        "CH",
        "IS",
        "LI",
    ]:
        return "EU"

    # China and nearby
    if country_code in ["CN", "HK", "MO", "TW"]:
        return "CN"

    # Switzerland
    if country_code == "CH":
        return "CH"

    # Asia Pacific
    if country_code in [
        "JP",
        "KR",
        "SG",
        "MY",
        "TH",
        "VN",
        "PH",
        "ID",
        "IN",
        "AU",
        "NZ",
        "BD",
        "LK",
        "MM",
        "KH",
        "LA",
        "BN",
        "MV",
    ]:
        return "ASIA"

    # Middle East
    if country_code in ["AE", "SA", "QA", "KW", "OM", "BH", "IL", "TR"]:
        return "ASIA"

    # Africa
    if country_code in ["ZA", "NG", "KE", "EG", "MA", "TN", "GH", "UG"]:
        return "EU"  # Route through EU for better connectivity

    # Default to US for unknown regions
    return "US"


def get_region_info() -> dict:
    """
    Get comprehensive region information for the current user.

    Returns:
        Dictionary with location details
    """
    country_code, source = get_user_location()
    major_region = get_closest_region(country_code)

    return {
        "country_code": country_code,
        "major_region": major_region,
        "source": source,
        "timestamp": str(__import__("datetime").datetime.now()),
    }


if __name__ == "__main__":
    # Test the geolocation functionality
    info = get_region_info()
    print(json.dumps(info, indent=2))
