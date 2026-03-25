"""
Gmail tools package for reading emails via IMAP.

This package provides tools for interacting with Gmail using the IMAP protocol.

CLI Usage:
    python -m janito4.tools.gmail read-emails [options]

For AI function calling, use through the tool registry.
"""

from .read_emails import ReadEmails
from .count_emails import CountEmails

__all__ = ["ReadEmails", "CountEmails"]
