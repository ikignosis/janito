#!/usr/bin/env python3
"""
Count Emails Tool - A class-based tool for counting emails in Gmail folders via IMAP.

This tool connects to Gmail using IMAP and counts emails in folders
without fetching the full email content. Credentials are securely retrieved
from the secrets module.
"""

import imaplib
from typing import Any

from ...tooling import BaseTool
from ...tooling.decorator import tool
from .imap_utils import (
    connect_gmail,
    decode_imap_error,
    get_gmail_credentials,
    missing_password_result,
    missing_username_result,
    resolve_search_criteria,
    safe_decode,
)


@tool(permissions="r")
class CountEmails(BaseTool):
    """
    Tool for counting emails in Gmail folders via IMAP.

    This is a lightweight operation that only counts emails without fetching
    their content, making it faster than ReadEmails for quick checks.

    Requires the following secrets to be configured:
    - gmail_username: Your Gmail address
    - gmail_password: Your Gmail app password (for 2FA accounts, use an app password)

    Usage:
        janito --set-secret gmail_username=your-email@gmail.com
        janito --set-secret gmail_password=your-app-password
    """

    IMAP_SERVER = "imap.gmail.com"
    IMAP_PORT = 993

    def _select_folder(self, mail, folder: str) -> dict[str, Any] | None:
        """Select the mailbox; returns an error result dict or None."""
        # Encode folder name as ASCII for Gmail compatibility
        folder_encoded = (
            folder.encode("ascii", "strict") if isinstance(folder, str) else folder
        )
        status, messages = mail.select(folder_encoded)
        if status != "OK":
            mail.logout()
            self.report_error(f"Failed to select folder: {folder}")
            raw = messages[0] if messages else None
            decoded = safe_decode(raw) if raw else "Unknown error"
            return {
                "success": False,
                "error": f"Failed to select folder '{folder}': {decoded}",
                "folder": folder,
            }
        return None

    def _count_by_criteria(self, mail, criteria: str, label: str) -> int | None:
        """Search and count emails; returns None when the search fails."""
        self.report_progress(f" Counting {label}...")
        status, data = mail.search(None, criteria)
        if status != "OK":
            self.report_error(f"Failed to count {label}")
            return None
        return len(data[0].split()) if data[0] else 0

    def run(
        self,
        folder: str = "INBOX",
        unread_only: bool = False,
        search_query: str | None = None,
    ) -> dict[str, Any]:
        """
        Count emails in a Gmail folder.

        Args:
            folder (str): Mailbox folder to count from (default: INBOX)
            unread_only (bool): If True, count only unread emails (default: False)
            search_query (Optional[str]): Custom IMAP search query (e.g., "SINCE 01-Jan-2024")

        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if operation succeeded
                - 'folder': the folder that was accessed
                - 'total_count': total number of emails in folder
                - 'unread_count': number of unread emails
                - 'matching_count': number of emails matching the search criteria
                - 'error': error message if operation failed (only present if success=False)
        """
        try:
            # Fetch credentials from secrets
            self.report_start(
                f"\ud83d\udcca Connecting to Gmail to count emails in {folder}"
            )

            username, password = get_gmail_credentials()

            if not username:
                self.report_error("Gmail username not found in secrets")
                return missing_username_result(folder=folder)

            if not password:
                self.report_error("Gmail password not found in secrets")
                return missing_password_result(folder=folder)

            # Connect to Gmail IMAP server
            self.report_progress(" Connecting to imap.gmail.com...")

            mail = connect_gmail(username, password, self.IMAP_SERVER, self.IMAP_PORT)

            # Select the mailbox
            select_error = self._select_folder(mail, folder)
            if select_error:
                return select_error

            # Count total emails
            total_count = self._count_by_criteria(mail, "ALL", "total emails")
            if total_count is None:
                mail.logout()
                return {
                    "success": False,
                    "error": "Failed to count total emails",
                    "folder": folder,
                }

            # Count unread emails
            unread_count = self._count_by_criteria(mail, "UNSEEN", "unread emails")
            if unread_count is None:
                mail.logout()
                return {
                    "success": False,
                    "error": "Failed to count unread emails",
                    "folder": folder,
                }

            # Count emails matching search criteria
            search_criteria = resolve_search_criteria(search_query, unread_only)
            matching_count = self._count_by_criteria(
                mail, search_criteria, f"emails matching: {search_criteria}"
            )
            if matching_count is None:
                mail.logout()
                return {
                    "success": False,
                    "error": "Failed to count matching emails",
                    "folder": folder,
                }

            # Logout
            mail.logout()

            self.report_result(
                f"Total: {total_count}, Unread: {unread_count}, "
                f"Matching '{search_criteria}': {matching_count}"
            )

            return {
                "success": True,
                "folder": folder,
                "total_count": total_count,
                "unread_count": unread_count,
                "matching_count": matching_count,
                "search_criteria": search_criteria,
            }

        except imaplib.IMAP4.error as e:
            error_msg = decode_imap_error(e)
            self.report_error(f"IMAP error: {error_msg}")
            return {
                "success": False,
                "error": f"IMAP connection error: {error_msg}",
                "folder": folder,
            }

        except Exception as e:
            self.report_error(f"Error counting emails: {e!s}")
            return {
                "success": False,
                "error": f"Failed to count emails: {e!s}",
                "folder": folder,
            }
