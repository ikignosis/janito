#!/usr/bin/env python3
"""
Shared IMAP helpers for the Gmail tools.

Consolidates utilities that were previously duplicated across the
``delete_emails``, ``move_emails`` and ``trash_emails`` modules
(``_safe_decode`` and ``_build_search_criteria``), plus the credential
fetching, connection and error-decode boilerplate every tool repeats.
"""

import datetime
import imaplib


def safe_decode(data: bytes | str) -> str:
    """Safely decode bytes to string, or return string as-is.

    Args:
        data: The bytes or string to decode.

    Returns:
        A UTF-8 decoded string (invalid bytes are replaced), or the
        string itself when a ``str`` is passed.
    """
    if isinstance(data, bytes):
        return data.decode("utf-8", errors="replace")
    return str(data)


def decode_imap_error(e: imaplib.IMAP4.error) -> str:
    """Decode an ``imaplib.IMAP4.error`` argument to a readable string."""
    if e.args and isinstance(e.args[0], bytes):
        return e.args[0].decode()
    return str(e.args[0] if e.args else e)


def get_gmail_credentials() -> tuple[str, str]:
    """Fetch the Gmail username/password from the secrets store."""
    from ..secrets_config import get_secret

    return get_secret("gmail_username"), get_secret("gmail_password")


def missing_username_result(**extra) -> dict:
    """Return the failure dict for a missing ``gmail_username`` secret."""
    result = {
        "success": False,
        "error": (
            "Secret 'gmail_username' not configured."
            " Use: janito --set-secret gmail_username=your-email@gmail.com"
        ),
    }
    result.update(extra)
    return result


def missing_password_result(**extra) -> dict:
    """Return the failure dict for a missing ``gmail_password`` secret."""
    result = {
        "success": False,
        "error": (
            "Secret 'gmail_password' not configured."
            " Use: janito --set-secret gmail_password=your-app-password"
        ),
    }
    result.update(extra)
    return result


def connect_gmail(username: str, password: str, server: str, port: int):
    """Connect and log in to the Gmail IMAP server."""
    mail = imaplib.IMAP4_SSL(server, port)
    mail.login(username, password)
    return mail


def resolve_search_criteria(search_query: str | None, unread_only: bool) -> str:
    """Pick the IMAP search criteria from the CLI options."""
    if search_query:
        return search_query
    if unread_only:
        return "UNSEEN"
    return "ALL"


def build_search_criteria(
    message_ids: list[str] | None = None,
    search_query: str | None = None,
    from_address: str | None = None,
    subject_contains: str | None = None,
    older_than_days: int | None = None,
    older_than_date: str | None = None,
) -> str | None:
    """
    Build an IMAP search criteria string from filter parameters.

    Multiple ``message_ids`` are emitted as space-separated ``UID`` tokens,
    which IMAP combines with an implicit OR. When both ``older_than_days``
    and ``older_than_date`` are provided, ``older_than_days`` wins.

    Args:
        message_ids: Specific message UIDs to match.
        search_query: Custom IMAP search query; returned as-is when set.
        from_address: Filter by sender address.
        subject_contains: Filter by subject substring.
        older_than_days: Filter messages older than N days.
        older_than_date: Filter messages older than a date (e.g. "01-Jan-2024").

    Returns:
        IMAP search criteria string, or None if no criteria provided.
    """
    if search_query:
        return search_query

    criteria_parts = []

    # Handle specific message IDs (space-separated UIDs = implicit OR)
    if message_ids:
        for mid in message_ids:
            criteria_parts.append(f"UID {mid}")

    # Handle date-based filtering
    if older_than_days is not None:
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=older_than_days)
        date_str = cutoff_date.strftime("%d-%b-%Y")
        criteria_parts.append(f"BEFORE {date_str}")
    elif older_than_date:
        criteria_parts.append(f"BEFORE {older_than_date}")

    # Handle sender filter
    if from_address:
        criteria_parts.append(f"FROM {from_address}")

    # Handle subject filter
    if subject_contains:
        criteria_parts.append(f"SUBJECT {subject_contains}")

    if not criteria_parts:
        return None

    return " ".join(criteria_parts)
