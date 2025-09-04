"""Blocked sites management for fetch_url tool to prevent access to known problematic sites."""

from pathlib import Path
from typing import Set
from urllib.parse import urlparse


class BlockedSitesManager:
    """Manages blocked sites for the fetch_url tool using the local blocked.txt file."""

    def __init__(self):
        # Use package data directory for blocked.txt
        import janito
        package_dir = Path(janito.__file__).parent
        self.blocked_file_path = package_dir / "data" / "blocked.txt"
        self._blocked_sites = self._load_blocked_sites()

    def _load_blocked_sites(self) -> Set[str]:
        """Load blocked sites from the blocked.txt file."""
        blocked = set()
        
        if self.blocked_file_path.exists():
            try:
                with open(self.blocked_file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            # Extract domain from URL if it's a full URL
                            if line.startswith("http://") or line.startswith("https://"):
                                parsed = urlparse(line)
                                domain = parsed.netloc
                                if domain:
                                    blocked.add(domain.lower())
                            else:
                                # Assume it's already a domain
                                blocked.add(line.lower())
            except IOError:
                pass
        
        return blocked

    def is_url_blocked(self, url: str) -> bool:
        """Check if a URL is blocked."""
        if not self._blocked_sites:
            return False

        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Check exact matches and subdomain matches
            for blocked in self._blocked_sites:
                if domain == blocked or domain.endswith("." + blocked):
                    return True

            return False
        except Exception:
            return False  # Invalid URLs are not blocked by default

    def get_blocked_sites(self) -> list[str]:
        """Get the list of blocked sites."""
        return sorted(self._blocked_sites)


# Global singleton
_blocked_sites_manager = None


def get_blocked_sites_manager() -> BlockedSitesManager:
    """Get the global blocked sites manager instance."""
    global _blocked_sites_manager
    if _blocked_sites_manager is None:
        _blocked_sites_manager = BlockedSitesManager()
    return _blocked_sites_manager