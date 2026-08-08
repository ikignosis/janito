#!/usr/bin/env python3
"""
Delete Emails Tool - A class-based tool for deleting emails from Gmail via IMAP.

This tool connects to Gmail using IMAP and deletes emails from the inbox
or other folders. Credentials are securely retrieved from the secrets module.

WARNING: This operation is destructive and cannot be undone.
Emails are permanently deleted after the expunge operation.
"""

import imaplib
from typing import Any

from ...tooling import BaseTool
from ...tooling.decorator import tool
from .imap_utils import (
    build_search_criteria,
    connect_gmail,
    get_gmail_credentials,
    missing_password_result,
    missing_username_result,
    safe_decode,
)


@tool(permissions="rw")
class DeleteEmails(BaseTool):
    """
    Tool for deleting emails from Gmail via IMAP.

    This tool can delete emails by message ID, subject search, or older than date.
    Uses IMAP flags to mark emails as deleted, then expunges them permanently.

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
        status, messages = mail.select(folder)
        if status != "OK":
            mail.logout()
            self.report_error(f"Failed to select folder: {folder}")
            return {
                "success": False,
                "error": (
                    f"Failed to select folder '{folder}':"
                    f" {safe_decode(messages[0]) if messages else 'Unknown error'}"
                ),
                "folder": folder,
            }
        return None

    def _mark_deleted(self, mail, ids_to_delete) -> int:
        """Mark message IDs as deleted using the STORE command."""
        deleted_count = 0
        for msg_id in ids_to_delete:
            try:
                status, response = mail.store(msg_id, "+FLAGS", "\\Deleted")
                if status == "OK":
                    deleted_count += 1
            except Exception:
                continue
        return deleted_count

    def _do_delete(
        self,
        folder: str,
        message_ids: list[str] | None,
        search_query: str | None,
        older_than_days: int | None,
        older_than_date: str | None,
        from_address: str | None,
        subject_contains: str | None,
        dry_run: bool,
    ) -> dict[str, Any]:
        """Perform the delete (or dry-run count); returns the result dict."""
        action = "Counting (dry run)" if dry_run else "Deleting"
        self.report_start(f"\ud83d\uddd1\ufe0f {action} emails in {folder}")

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

        # Build search criteria
        search_criteria = build_search_criteria(
            message_ids=message_ids,
            search_query=search_query,
            older_than_days=older_than_days,
            older_than_date=older_than_date,
            from_address=from_address,
            subject_contains=subject_contains,
        )

        if not search_criteria:
            mail.logout()
            self.report_error("No deletion criteria specified")
            return {
                "success": False,
                "error": (
                    "Must specify at least one deletion criteria:"
                    " message_ids, search_query, older_than_days,"
                    " older_than_date, from_address, or"
                    " subject_contains"
                ),
                "folder": folder,
            }

        self.report_progress(" Searching for emails to delete...")

        # Search for emails matching criteria
        status, message_ids_list = mail.search(None, search_criteria)

        if status != "OK":
            mail.logout()
            self.report_error("Failed to search emails")
            return {
                "success": False,
                "error": "Failed to search emails",
                "folder": folder,
            }

        # Get list of message IDs
        ids_to_delete = message_ids_list[0].split()
        found_count = len(ids_to_delete)

        if found_count == 0:
            mail.logout()
            self.report_result("No emails found matching deletion criteria")
            return {
                "success": True,
                "folder": folder,
                "found_count": 0,
                "deleted_count": 0,
                "message_ids": [],
                "dry_run": dry_run,
            }

        # Convert bytes to strings for display
        id_strings = [safe_decode(mid) for mid in ids_to_delete]

        if dry_run:
            self.report_progress(
                f" Found {found_count} emails matching criteria (dry run - no deletion)"
            )
            mail.logout()
            self.report_result(
                f"DRY RUN: Would delete {found_count} emails: {id_strings[:10]}"
                f"{'...' if found_count > 10 else ''}"
            )
            return {
                "success": True,
                "folder": folder,
                "found_count": found_count,
                "deleted_count": 0,
                "message_ids": id_strings,
                "dry_run": True,
            }

        # Confirm deletion with Gmail
        self.report_progress(f" Found {found_count} emails, marking as deleted...")

        # Mark emails as deleted using STORE command
        deleted_count = self._mark_deleted(mail, ids_to_delete)

        self.report_progress(f" Marked {deleted_count} emails as deleted, expunging...")

        # Permanently delete marked emails
        status, expunge_result = mail.expunge()

        # Logout
        mail.logout()

        if status == "OK":
            self.report_result(
                f"Successfully deleted {deleted_count} emails from {folder}"
            )
            return {
                "success": True,
                "folder": folder,
                "found_count": found_count,
                "deleted_count": deleted_count,
                "message_ids": id_strings,
                "dry_run": False,
            }
        else:
            self.report_error(f"Expunge returned status: {status}")
            return {
                "success": False,
                "error": f"Expunge failed with status: {status}",
                "folder": folder,
            }

    def run(
        self,
        folder: str = "INBOX",
        message_ids: list[str] | None = None,
        search_query: str | None = None,
        older_than_days: int | None = None,
        older_than_date: str | None = None,
        from_address: str | None = None,
        subject_contains: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """
        Delete emails from Gmail.

        You can specify emails to delete using one of these methods:
        - message_ids: List of specific message IDs
        - search_query: Custom IMAP search query
        - older_than_days: Delete emails older than N days
        - older_than_date: Delete emails older than a specific date (e.g., "01-Jan-2024")
        - from_address + subject_contains: Filter by sender and/or subject

        Args:
            folder (str): Mailbox folder to delete from (default: INBOX)
            message_ids (Optional[List[str]]): List of specific message IDs to delete
            search_query (Optional[str]): Custom IMAP search query
            older_than_days (Optional[int]): Delete emails older than N days
            older_than_date (Optional[str]): Delete emails older than date (e.g., "01-Jan-2024")
            from_address (Optional[str]): Delete emails from specific sender
            subject_contains (Optional[str]): Delete emails with subject containing text
            dry_run (bool): If True, only count emails without deleting (default: False)

        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if operation succeeded
                - 'folder': the folder that was accessed
                - 'deleted_count': number of emails deleted (0 if dry_run=True)
                - 'found_count': number of emails matching deletion criteria
                - 'message_ids': list of message IDs that were/would be deleted
                - 'dry_run': whether this was a dry run
                - 'error': error message if operation failed (only present if success=False)
        """
        try:
            return self._do_delete(
                folder,
                message_ids,
                search_query,
                older_than_days,
                older_than_date,
                from_address,
                subject_contains,
                dry_run,
            )
        except imaplib.IMAP4.error as e:
            error_msg = safe_decode(e.args[0]) if e.args else str(e)
            self.report_error(f"IMAP error: {error_msg}")
            return {
                "success": False,
                "error": f"IMAP connection error: {error_msg}",
                "folder": folder,
            }

        except Exception as e:
            self.report_error(f"Error deleting emails: {e!s}")
            return {
                "success": False,
                "error": f"Failed to delete emails: {e!s}",
                "folder": folder,
            }
