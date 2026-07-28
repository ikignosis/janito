#!/usr/bin/env python3
"""
Trash Emails Tool - A class-based tool for moving emails to Gmail Trash via IMAP.

This is a safer alternative to permanent deletion as emails in Trash
are recoverable for 30 days before permanent deletion.
"""

import imaplib
from typing import Any

from ...tooling import BaseTool
from ..decorator import tool
from .imap_utils import build_search_criteria, safe_decode


@tool(permissions="r")
class TrashEmail(BaseTool):
    """
    Tool for moving emails to Gmail Trash instead of permanent deletion.

    This is a safer alternative to DeleteEmails as emails in Trash
    are recoverable for 30 days before permanent deletion.

    Requires the following secrets to be configured:
    - gmail_username: Your Gmail address
    - gmail_password: Your Gmail app password (for 2FA accounts, use an app password)

    Usage:
        janito --set-secret gmail_username=your-email@gmail.com
        janito --set-secret gmail_password=your-app-password
    """

    IMAP_SERVER = "imap.gmail.com"
    IMAP_PORT = 993

    def run(
        self,
        folder: str = "INBOX",
        message_ids: list[str] | None = None,
        search_query: str | None = None,
        from_address: str | None = None,
        subject_contains: str | None = None,
        older_than_days: int | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """
        Move emails to Gmail Trash.

        Args:
            folder (str): Mailbox folder to trash from (default: INBOX)
            message_ids (Optional[List[str]]): List of specific message IDs to trash
            search_query (Optional[str]): Custom IMAP search query
            from_address (Optional[str]): Trash emails from specific sender
            subject_contains (Optional[str]): Trash emails with subject containing text
            older_than_days (Optional[int]): Trash emails older than N days
            dry_run (bool): If True, only count emails without moving (default: False)

        Returns:
            Dict[str, Any]: A dictionary containing operation results
        """
        try:
            from janito.secrets_config import get_secret

            action = "Counting (dry run)" if dry_run else "Moving to trash"
            self.report_start(f"🗑️ {action} emails from {folder}")

            username = get_secret("gmail_username")
            password = get_secret("gmail_password")

            if not username or not password:
                return {
                    "success": False,
                    "error": "Gmail credentials not configured. Use: janito --set-secret gmail_username=... gmail_password=...",
                    "folder": folder,
                }

            mail = imaplib.IMAP4_SSL(self.IMAP_SERVER, self.IMAP_PORT)
            mail.login(username, password)

            status, messages = mail.select(folder)
            if status != "OK":
                mail.logout()
                return {
                    "success": False,
                    "error": f"Failed to select folder '{folder}'",
                    "folder": folder,
                }

            # Build search criteria
            search_criteria = build_search_criteria(
                message_ids=message_ids,
                search_query=search_query,
                from_address=from_address,
                subject_contains=subject_contains,
                older_than_days=older_than_days,
            )

            if not search_criteria:
                mail.logout()
                return {
                    "success": False,
                    "error": "Must specify at least one criteria: message_ids, search_query, from_address, subject_contains, or older_than_days",
                    "folder": folder,
                }

            self.report_progress(" Searching for emails to trash...")

            status, message_ids_list = mail.search(None, search_criteria)

            if status != "OK":
                mail.logout()
                return {
                    "success": False,
                    "error": "Failed to search emails",
                    "folder": folder,
                }

            ids_to_trash = message_ids_list[0].split()
            found_count = len(ids_to_trash)

            if found_count == 0:
                mail.logout()
                self.report_result("No emails found matching criteria")
                return {
                    "success": True,
                    "folder": folder,
                    "found_count": 0,
                    "trashed_count": 0,
                    "dry_run": dry_run,
                }

            id_strings = [safe_decode(mid) for mid in ids_to_trash]

            if dry_run:
                mail.logout()
                self.report_result(f"DRY RUN: Would trash {found_count} emails")
                return {
                    "success": True,
                    "folder": folder,
                    "found_count": found_count,
                    "trashed_count": 0,
                    "message_ids": id_strings,
                    "dry_run": True,
                }

            # Move to Trash using +FLAGS (\Trashed)
            self.report_progress(f" Found {found_count} emails, moving to trash...")

            trashed_count = 0
            for msg_id in ids_to_trash:
                try:
                    status, response = mail.store(msg_id, "+FLAGS", "\\Trashed")
                    if status == "OK":
                        trashed_count += 1
                except Exception:
                    continue

            mail.logout()

            self.report_result(f"Trashed {trashed_count} emails from {folder}")
            return {
                "success": True,
                "folder": folder,
                "found_count": found_count,
                "trashed_count": trashed_count,
                "message_ids": id_strings,
                "dry_run": False,
            }

        except imaplib.IMAP4.error as e:
            error_msg = safe_decode(e.args[0]) if e.args else str(e)
            self.report_error(f"IMAP error: {error_msg}")
            return {
                "success": False,
                "error": f"IMAP connection error: {error_msg}",
                "folder": folder,
            }

        except Exception as e:
            self.report_error(f"Error trashing emails: {e!s}")
            return {
                "success": False,
                "error": f"Failed to trash emails: {e!s}",
                "folder": folder,
            }
