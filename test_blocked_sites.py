#!/usr/bin/env python3
"""Test script to verify blocked sites functionality."""

from janito.tools.blocked_sites import get_blocked_sites_manager

def test_blocked_sites():
    """Test the blocked sites functionality."""
    manager = get_blocked_sites_manager()
    
    print("Testing blocked sites...")
    
    # Test some known blocked sites
    test_urls = [
        "https://www.reuters.com",
        "https://www.wsj.com", 
        "https://www.nytimes.com",
        "https://www.google.com",
        "https://www.github.com",
    ]
    
    for url in test_urls:
        is_blocked = manager.is_url_blocked(url)
        status = "BLOCKED" if is_blocked else "ALLOWED"
        print(f"{url}: {status}")
    
    print(f"\nTotal blocked sites loaded: {len(manager.get_blocked_sites())}")
    print("Blocked sites:")
    for site in manager.get_blocked_sites():
        print(f"  - {site}")

if __name__ == "__main__":
    test_blocked_sites()