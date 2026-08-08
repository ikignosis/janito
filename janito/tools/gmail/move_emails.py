#!/usr/bin/env python3
"""
Move Emails Tool - A class-based tool for moving emails between folders in Gmail via IMAP.

This tool copies emails to a target folder and removes them from the source.
It's useful for organizing emails (e.g., archiving, filing, labeling).
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
class MoveEmails(BaseTool):
    """
    Tool for moving emails between folders in Gmail via IMAP.

    This tool copies emails to a target folder and removes them from the source.
    It's useful for organizing emails (e.g., archiving, filing, labeling).

    Requires the following secrets to be configured:
    - gmail_username: Your Gmail address
    - gmail_password: Your Gmail app password (for 2FA accounts, use an app password)

    Usage:
        janito --set-secret gmail_username=your-email@gmail.com
        janito --set-secret gmail_password=your-app-password
    """

    IMAP_SERVER = "imap.gmail.com"
    IMAP_PORT = 993

    def _select_folder(
        self, mail, folder: str, target_folder: str
    ) -> dict[str, Any] | None:
        """Select the source folder; returns an error result dict or None."""
        status, messages = mail.select(folder)
        if status != "OK":
            mail.logout()
            self.report_error(f"Failed to select source folder: {folder}")
            return {
                "success": False,
                "error": f"Failed to select source folder '{folder}'",
                "source_folder": folder,
                "target_folder": target_folder,
            }
        return None

    def _move_one(self, mail, msg_id, target_folder: str) -> tuple[bool, str | None]:
        """Move a single message; returns (moved, failed_id or None)."""
        try:
            # Try MOVE command first (Gmail-specific)
            status, response = mail.move(msg_id, target_folder)
            if status == "OK":
                return True, None
            return False, safe_decode(msg_id)
        except imaplib.IMAP4.error:
            # Fallback: COPY then DELETE
            try:
                copy_status, _ = mail.copy(msg_id, target_folder)
                if copy_status == "OK":
                    # Mark original for deletion
                    mail.store(msg_id, "+FLAGS", "\\Deleted")
                    return True, None
                return False, safe_decode(msg_id)
            except Exception:
                return False, safe_decode(msg_id)
        except Exception:
            return False, safe_decode(msg_id)

    def _move_messages(
        self, mail, ids_to_move, target_folder: str
    ) -> tuple[int, list[str]]:
        """Move all messages; returns (moved_count, failed_ids)."""
        moved_count = 0
        failed_ids = []
        for msg_id in ids_to_move:
            moved, failed_id = self._move_one(mail, msg_id, target_folder)
            if moved:
                moved_count += 1
            else:
                failed_ids.append(failed_id)
        return moved_count, failed_ids

    def _do_move(
        self,
        source_folder: str,
        target_folder: str,
        message_ids: list[str] | None,
        search_query: str | None,
        from_address: str | None,
        subject_contains: str | None,
        older_than_days: int | None,
        dry_run: bool,
    ) -> dict[str, Any]:
        """Perform the move (or dry-run count); returns the result dict."""
        action = "Counting (dry run)" if dry_run else "Moving"
        self.report_start(
            f"\ud83d\udce6 {action} emails from {source_folder} to {target_folder}"
        )

        username, password = get_gmail_credentials()

        if not username:
            self.report_error("Gmail username not found in secrets")
            return missing_username_result(
                source_folder=source_folder, target_folder=target_folder
            )

        if not password:
            self.report_error("Gmail password not found in secrets")
            return missing_password_result(
                source_folder=source_folder, target_folder=target_folder
            )

        # Connect to Gmail IMAP server
        self.report_progress(" Connecting to imap.gmail.com...")

        mail = connect_gmail(username, password, self.IMAP_SERVER, self.IMAP_PORT)

        # Select the source folder
        select_error = self._select_folder(mail, source_folder, target_folder)
        if select_error:
            return select_error

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
            self.report_error("No search criteria specified")
            return {
                "success": False,
                "error": (
                    "Must specify at least one criteria:"
                    " message_ids, search_query, from_address,"
                    " subject_contains, or older_than_days"
                ),
                "source_folder": source_folder,
                "target_folder": target_folder,
            }

        self.report_progress("\ud83d\udd0d Searching for emails to move...")

        # Search for emails
        status, message_ids_list = mail.search(None, search_criteria)

        if status != "OK":
            mail.logout()
            self.report_error("Failed to search emails")
            return {
                "success": False,
                "error": "Failed to search emails",
                "source_folder": source_folder,
                "target_folder": target_folder,
            }

        # Get list of message IDs
        ids_to_move = message_ids_list[0].split()
        found_count = len(ids_to_move)

        if found_count == 0:
            mail.logout()
            self.report_result("No emails found matching criteria")
            return {
                "success": True,
                "source_folder": source_folder,
                "target_folder": target_folder,
                "found_count": 0,
                "moved_count": 0,
                "message_ids": [],
                "dry_run": dry_run,
            }

        id_strings = [safe_decode(mid) for mid in ids_to_move]

        if dry_run:
            mail.logout()
            self.report_result(
                f"DRY RUN: Would move {found_count} emails from "
                f"{source_folder} to {target_folder}"
            )
            return {
                "success": True,
                "source_folder": source_folder,
                "target_folder": target_folder,
                "found_count": found_count,
                "moved_count": 0,
                "message_ids": id_strings,
                "dry_run": True,
            }

        # Copy emails to target folder
        self.report_progress(f" Copying {found_count} emails to {target_folder}...")

        moved_count, failed_ids = self._move_messages(mail, ids_to_move, target_folder)

        # Expunge deleted messages from source
        if moved_count > 0:
            self.report_progress(" Expunging moved emails from source...")
            mail.expunge()

        # Logout
        mail.logout()

        self.report_result(
            f"Moved {moved_count} emails from {source_folder} to {target_folder}"
        )

        result = {
            "success": True,
            "source_folder": source_folder,
            "target_folder": target_folder,
            "found_count": found_count,
            "moved_count": moved_count,
            "message_ids": id_strings,
            "dry_run": False,
        }

        if failed_ids:
            result["failed_ids"] = failed_ids
            result["warning"] = f"Failed to move {len(failed_ids)} emails"

        return result

    def run(
        self,
        source_folder: str = "INBOX",
        target_folder: str = "[Gmail]/All Mail",
        message_ids: list[str] | None = None,
        search_query: str | None = None,
        from_address: str | None = None,
        subject_contains: str | None = None,
        older_than_days: int | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """
        Move emails from one folder to another.

        Args:
            source_folder (str): Source folder to move from (default: INBOX)
            target_folder (str): Target folder to move to (default: [Gmail]/All Mail)
            message_ids (Optional[List[str]]): List of specific message IDs to move
            search_query (Optional[str]): Custom IMAP search query
            from_address (Optional[str]): Move emails from specific sender
            subject_contains (Optional[str]): Move emails with subject containing text
            older_than_days (Optional[int]): Move emails older than N days
            dry_run (bool): If True, only count emails without moving (default: False)

        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if operation succeeded
                - 'source_folder': the source folder
                - 'target_folder': the target folder
                - 'moved_count': number of emails moved (0 if dry_run=True)
                - 'found_count': number of emails matching criteria
                - 'message_ids': list of message IDs that were/would be moved
                - 'dry_run': whether this was a dry run
                - 'error': error message if operation failed
        """
        try:
            return self._do_move(
                source_folder,
                target_folder,
                message_ids,
                search_query,
                from_address,
                subject_contains,
                older_than_days,
                dry_run,
            )
        except imaplib.IMAP4.error as e:
            error_msg = safe_decode(e.args[0]) if e.args else str(e)
            self.report_error(f"IMAP error: {error_msg}")
            return {
                "success": False,
                "error": f"IMAP connection error: {error_msg}",
                "source_folder": source_folder,
                "target_folder": target_folder,
            }

        except Exception as e:
            self.report_error(f"Error moving emails: {e!s}")
            return {
                "success": False,
                "error": f"Failed to move emails: {e!s}",
                "source_folder": source_folder,
                "target_folder": target_folder,
            }
