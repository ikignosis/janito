"""
Gmail tools package for interacting with Gmail via IMAP.

This package provides tools for reading, counting, deleting, trashing,
moving emails, and listing folders in Gmail using the IMAP protocol.

CLI Usage:
    python -m janito.tools.gmail read-emails [options]

For AI function calling, use through the tool registry.
"""

from .read_emails import ReadEmails
from .count_emails import CountEmails
from .delete_emails import DeleteEmails
from .trash_emails import TrashEmail
from .move_emails import MoveEmails
from .list_folders import ListFolders

__all__ = ["ReadEmails", "CountEmails", "DeleteEmails", "TrashEmail", "MoveEmails", "ListFolders"]
