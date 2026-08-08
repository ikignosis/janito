#!/usr/bin/env python3
"""
CLI entry point for Gmail tools.

This module provides the command-line interface for the Gmail tools package.
Run with: python -m janito.tools.gmail [args]
"""

import argparse
import json
import sys

from .list_folders import ListFolders
from .read_emails import ReadEmails


def _print_list_folders(result: dict, json_output: bool) -> None:
    """Print a ListFolders result (human-readable or JSON)."""
    if json_output:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    if result["success"]:
        print(f"\u2713 Found {result['total_count']} folders/labels:\n")

        for folder in result["folders"]:
            desc = f" - {folder['description']}" if folder["description"] else ""
            if "total_count" in folder:
                unread_info = (
                    f" ({folder['unread_count']} unread)"
                    if folder["unread_count"]
                    else ""
                )
                print(f"  \u2022 {folder['name']}{unread_info}{desc}")
            else:
                print(f"  \u2022 {folder['name']}{desc}")
    else:
        print(f"\u2717 Failed to list folders: {result['error']}")


def _print_read_emails(result: dict, json_output: bool) -> None:
    """Print a ReadEmails result (human-readable or JSON)."""
    if json_output:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    if result["success"]:
        print(
            f"\u2713 Successfully fetched {result['emails_returned']} emails "
            f"from {result['folder']}"
        )
        print(f"  Total emails matching criteria: {result['total_found']}")
        print()

        for i, email_info in enumerate(result["emails"], 1):
            print("=" * 60)
            print(f"Email {i}/{result['emails_returned']}")
            print(f"  Subject: {email_info['subject']}")
            print(f"  From: {email_info['from']}")
            print(f"  Date: {email_info['date']}")
            print("  Body preview:")
            for line in email_info["body"].split("\n")[:5]:
                print(f"    {line}")
            print()
    else:
        print(f"\u2717 Failed to read emails: {result['error']}")


def _handle_list_folders(args) -> int:
    """Handle the list-folders subcommand."""
    tool_instance = ListFolders()
    result = tool_instance.run(include_counts=getattr(args, "counts", False))
    _print_list_folders(result, getattr(args, "json", False))
    return 0 if result["success"] else 1


def _handle_read_emails(args) -> int:
    """Handle the read-emails subcommand (also the default)."""
    tool_instance = ReadEmails()
    result = tool_instance.run(
        folder=args.folder,
        limit=args.limit,
        unread_only=args.unread,
        search_query=args.query,
        max_body_length=args.max_body,
    )
    _print_read_emails(result, getattr(args, "json", False))
    return 0 if result["success"] else 1


def main():
    """Command line interface for Gmail tools."""
    parser = argparse.ArgumentParser(
        description="Gmail tools for reading emails via IMAP"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List folders subcommand
    list_parser = subparsers.add_parser(
        "list-folders",
        help="List all Gmail folders/labels",
        description="List all available Gmail folders and labels via IMAP",
    )
    list_parser.add_argument(
        "--counts",
        "-c",
        action="store_true",
        help="Include email counts for each folder (slower)",
    )
    list_parser.add_argument(
        "--json", "-j", action="store_true", help="Output in JSON format"
    )

    # Read emails subcommand
    read_parser = subparsers.add_parser(
        "read-emails",
        help="Read emails from Gmail",
        description="Read emails from a Gmail mailbox folder via IMAP",
    )
    read_parser.add_argument(
        "--folder",
        "-f",
        default="INBOX",
        help="Mailbox folder to read from (default: INBOX)",
    )
    read_parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=10,
        help="Maximum number of emails to fetch (default: 10)",
    )
    read_parser.add_argument(
        "--unread", "-u", action="store_true", help="Fetch only unread emails"
    )
    read_parser.add_argument(
        "--query", "-q", help="Custom IMAP search query (e.g., 'SINCE 01-Jan-2024')"
    )
    read_parser.add_argument(
        "--max-body",
        "-m",
        type=int,
        default=1000,
        help="Maximum length of email body to include (default: 1000)",
    )
    read_parser.add_argument(
        "--json", "-j", action="store_true", help="Output in JSON format"
    )

    args = parser.parse_args()

    if args.command == "list-folders":
        return _handle_list_folders(args)

    if args.command == "read-emails" or args.command is None:
        # Default to read-emails if no subcommand specified
        return _handle_read_emails(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
