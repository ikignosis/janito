"""
Gmail tools package for interacting with Gmail via IMAP.

This package provides tools for reading, counting, deleting, trashing,
moving emails, and listing folders in Gmail using the IMAP protocol.

CLI Usage:
    python -m janito.tools.gmail read-emails [options]

For AI function calling, use through the tool registry.
"""

GMAIL_SYSTEM_PROMPT = """
- You are an AI assistant with access to Gmail tools for reading emails
- Use the CountEmails tool to quickly check email counts without fetching content
- Use the ReadEmails tool to fetch the actual email content
- Explore the current directory for potential content related to the question
- When users ask about email counts or how many emails they have, use CountEmails first
- When users ask about email content or want to read emails, use ReadEmails
"""

from .read_emails import ReadEmails
from .count_emails import CountEmails
from .delete_emails import DeleteEmails
from .trash_emails import TrashEmail
from .move_emails import MoveEmails
from .list_folders import ListFolders

__all__ = ["GMAIL_SYSTEM_PROMPT", "ReadEmails", "CountEmails", "DeleteEmails", "TrashEmail", "MoveEmails", "ListFolders"]
