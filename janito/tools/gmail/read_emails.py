#!/usr/bin/env python3
"""
Read Emails Tool - A class-based tool for reading emails from Gmail via IMAP.

This tool connects to Gmail using IMAP and fetches emails from the inbox
or other folders. Credentials are securely retrieved from the secrets module.

Note: This tool requires the progress reporting system from the tooling package.
For direct execution, use: python -m janito.tools.gmail.read_emails [args]
For AI function calling, use through the tool registry (tooling.tools_registry).
"""

import email
import imaplib
from email.header import decode_header
from typing import Any

from ...tooling import BaseTool
from ...tooling.decorator import tool
from .imap_utils import (
    connect_gmail,
    get_gmail_credentials,
    missing_password_result,
    missing_username_result,
    resolve_search_criteria,
    safe_decode,
)


def decode_email_header(header_str: str) -> str:
    """
    Decode an email header string that may contain encoded words.

    Args:
        header_str: The encoded header string

    Returns:
        str: Decoded header string
    """
    decoded_parts = decode_header(header_str)
    result = []
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            try:
                result.append(part.decode(encoding or "utf-8", errors="replace"))
            except (LookupError, TypeError):
                result.append(part.decode("utf-8", errors="replace"))
        else:
            result.append(part)
    return "".join(result)


def parse_email_body(msg: email.message.EmailMessage) -> dict[str, Any]:
    """
    Parse the body of an email message.

    Args:
        msg: The email message object

    Returns:
        Dict containing 'text' and 'html' body parts
    """
    body = {"text": "", "html": ""}

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))

            if content_type == "text/plain" and "attachment" not in content_disposition:
                try:
                    charset = part.get_content_charset() or "utf-8"
                    body["text"] = part.get_payload(decode=True).decode(
                        charset, errors="replace"
                    )
                except Exception:
                    pass
            elif (
                content_type == "text/html" and "attachment" not in content_disposition
            ):
                try:
                    charset = part.get_content_charset() or "utf-8"
                    body["html"] = part.get_payload(decode=True).decode(
                        charset, errors="replace"
                    )
                except Exception:
                    pass
    else:
        content_type = msg.get_content_type()
        try:
            charset = msg.get_content_charset() or "utf-8"
            payload = msg.get_payload(decode=True)
            if payload:
                decoded = payload.decode(charset, errors="replace")
                if content_type == "text/html":
                    body["html"] = decoded
                else:
                    body["text"] = decoded
        except Exception:
            pass

    return body


def _parse_fetched_email(msg_id, msg_data, max_body_length: int) -> dict[str, Any]:
    """Parse a raw RFC822 message into an email info dict."""
    raw_email = msg_data[0][1]
    msg = email.message_from_bytes(raw_email)

    # Parse email headers
    subject = decode_email_header(msg.get("Subject", "(No Subject)"))
    sender = decode_email_header(msg.get("From", "Unknown"))
    date = msg.get("Date", "Unknown")
    message_id = msg.get("Message-ID", msg_id.decode())

    # Parse body
    body_dict = parse_email_body(msg)
    body = body_dict["text"] or body_dict["html"]

    # Truncate body if too long
    if len(body) > max_body_length:
        body = body[:max_body_length] + f"... [truncated, total {len(body)} chars]"

    return {
        "id": msg_id.decode(),
        "message_id": message_id,
        "subject": subject,
        "from": sender,
        "date": date,
        "body": body,
        "has_html": bool(body_dict["html"]),
    }


@tool(permissions="r")
class ReadEmails(BaseTool):
    """
    Tool for reading emails from Gmail via IMAP.

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
                    f" {messages[0].decode() if messages else 'Unknown error'}"
                ),
                "folder": folder,
            }
        return None

    def _fetch_emails(
        self, mail, email_ids_to_fetch, max_body_length: int
    ) -> list[dict[str, Any]]:
        """Fetch and parse the given email IDs."""
        emails = []
        for msg_id in email_ids_to_fetch:
            try:
                status, msg_data = mail.fetch(msg_id, "(RFC822)")
                if status != "OK":
                    continue

                emails.append(_parse_fetched_email(msg_id, msg_data, max_body_length))
            except Exception:
                # Skip individual email errors
                continue
        return emails

    def _do_read(
        self,
        folder: str,
        limit: int,
        unread_only: bool,
        search_query: str | None,
        max_body_length: int,
    ) -> dict[str, Any]:
        """Perform the read operation; returns the result dict."""
        # Fetch credentials from secrets
        self.report_start(f"\ud83d\udcec Connecting to Gmail to read {folder}")

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
        search_criteria = resolve_search_criteria(search_query, unread_only)

        # Search for emails
        self.report_progress(
            f"\ud83d\udd0d Searching for emails with criteria: {search_criteria}..."
        )
        status, message_ids = mail.search(None, search_criteria)

        if status != "OK":
            mail.logout()
            self.report_error("Failed to search emails")
            return {
                "success": False,
                "error": (
                    f"Failed to search emails:"
                    f" {message_ids[0].decode() if message_ids else 'Unknown error'}"
                ),
                "folder": folder,
            }

        # Get list of message IDs
        id_list = message_ids[0].split()
        total_found = len(id_list)

        if total_found == 0:
            mail.logout()
            self.report_result("No emails found matching criteria")
            return {
                "success": True,
                "folder": folder,
                "emails": [],
                "total_found": 0,
            }

        # Limit the number of emails to fetch
        email_ids_to_fetch = id_list[-limit:] if limit < total_found else id_list

        self.report_progress(
            f" Found {total_found} emails, fetching {len(email_ids_to_fetch)}..."
        )

        emails = self._fetch_emails(mail, email_ids_to_fetch, max_body_length)

        # Logout
        mail.logout()

        self.report_result(f"Fetched {len(emails)} emails from {folder}")

        return {
            "success": True,
            "folder": folder,
            "emails": emails,
            "total_found": total_found,
            "emails_returned": len(emails),
        }

    def run(
        self,
        folder: str = "INBOX",
        limit: int = 10,
        unread_only: bool = False,
        search_query: str | None = None,
        max_body_length: int = 1000,
    ) -> dict[str, Any]:
        """
        Read emails from Gmail.

        Args:
            folder (str): Mailbox folder to read from (default: INBOX)
            limit (int): Maximum number of emails to fetch (default: 10)
            unread_only (bool): If True, fetch only unread emails (default: False)
            search_query (Optional[str]): Custom IMAP search query (e.g., "SINCE 01-Jan-2024")
            max_body_length (int): Maximum length of email body to include (default: 1000)

        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if operation succeeded
                - 'folder': the folder that was accessed
                - 'emails': list of email dictionaries with 'subject', 'from', 'date', 'body'
                - 'total_found': number of emails matching the criteria
                - 'error': error message if operation failed (only present if success=False)
        """
        try:
            return self._do_read(
                folder, limit, unread_only, search_query, max_body_length
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
            self.report_error(f"Error reading emails: {e!s}")
            return {
                "success": False,
                "error": f"Failed to read emails: {e!s}",
                "folder": folder,
            }
