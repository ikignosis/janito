"""URL whitelist management for fetch_url tool."""

import json
from pathlib import Path
from typing import Set, List, Optional
from urllib.parse import urlparse


class UrlWhitelistManager:
    """Manages allowed sites for the fetch_url tool."""

    def __init__(self):
        self.config_path = Path.home() / ".janito" / "url_whitelist.json"
        self._allowed_sites = self._load_whitelist()
        self._unrestricted_mode = False

    def set_unrestricted_mode(self, enabled: bool = True):
        """Enable or disable unrestricted mode (bypasses whitelist)."""
        self._unrestricted_mode = enabled

    def _load_whitelist(self) -> Set[str]:
        """Load the whitelist from config file."""
        if not self.config_path.exists():
            return set()

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data.get("allowed_sites", []))
        except (json.JSONDecodeError, IOError):
            return set()

    def _save_whitelist(self):
        """Save the whitelist to config file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump({"allowed_sites": list(self._allowed_sites)}, f, indent=2)
        except IOError:
            pass  # Silently fail if we can't write

    def is_url_allowed(self, url: str) -> bool:
        """Check if a URL is allowed based on the whitelist."""
        if self._unrestricted_mode:
            return True  # Unrestricted mode bypasses all whitelist checks

        if not self._allowed_sites:
            return True  # No whitelist means all sites allowed

        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Check exact matches and subdomain matches
            for allowed in self._allowed_sites:
                allowed = allowed.lower()
                if domain == allowed or domain.endswith("." + allowed):
                    return True

            return False
        except Exception:
            return False  # Invalid URLs are blocked

    def add_allowed_site(self, site: str) -> bool:
        """Add a site to the whitelist."""
        # Clean up the site format
        site = site.strip().lower()
        if site.startswith("http://") or site.startswith("https://"):
            parsed = urlparse(site)
            site = parsed.netloc

        if site and site not in self._allowed_sites:
            self._allowed_sites.add(site)
            self._save_whitelist()
            return True
        return False

    def remove_allowed_site(self, site: str) -> bool:
        """Remove a site from the whitelist."""
        site = site.strip().lower()
        if site.startswith("http://") or site.startswith("https://"):
            parsed = urlparse(site)
            site = parsed.netloc

        if site in self._allowed_sites:
            self._allowed_sites.remove(site)
            self._save_whitelist()
            return True
        return False

    def get_allowed_sites(self) -> List[str]:
        """Get the list of allowed sites."""
        return sorted(self._allowed_sites)

    def set_allowed_sites(self, sites: List[str]):
        """Set the complete list of allowed sites."""
        self._allowed_sites = set()
        for site in sites:
            site = site.strip().lower()
            if site.startswith("http://") or site.startswith("https://"):
                parsed = urlparse(site)
                site = parsed.netloc
            if site:
                self._allowed_sites.add(site)
        self._save_whitelist()

    def clear_whitelist(self):
        """Clear all allowed sites."""
        self._allowed_sites.clear()
        self._save_whitelist()


# Global singleton
_url_whitelist_manager = None


def get_url_whitelist_manager() -> UrlWhitelistManager:
    """Get the global URL whitelist manager instance."""
    global _url_whitelist_manager
    if _url_whitelist_manager is None:
        _url_whitelist_manager = UrlWhitelistManager()
    return _url_whitelist_manager
