#!/usr/bin/env python3
"""
Delete Emails Tool - A class-based tool for deleting emails from Gmail via IMAP.

This tool connects to Gmail using IMAP and deletes emails from the inbox
or other folders. Credentials are securely retrieved from the secrets module.

WARNING: This operation is destructive and cannot be undone.
Emails are permanently deleted after the expunge operation.
"""

import imaplib
from typing import Dict, Any, Optional, List, Union
from ...tooling import BaseTool
from ..decorator import tool


def _safe_decode(data: Union[bytes, str]) -> str:
    """Safely decode bytes to string, or return string as-is."""
    if isinstance(data, bytes):
        return data.decode('utf-8', errors='replace')
    return str(data)


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
    
    def run(
        self,
        folder: str = "INBOX",
        message_ids: Optional[List[str]] = None,
        search_query: Optional[str] = None,
        older_than_days: Optional[int] = None,
        older_than_date: Optional[str] = None,
        from_address: Optional[str] = None,
        subject_contains: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
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
            from janito.secrets_config import get_secret
            
            # Fetch credentials from secrets
            action = "Counting (dry run)" if dry_run else "Deleting"
            self.report_start(f"{action} emails in {folder}")
            
            username = get_secret("gmail_username")
            password = get_secret("gmail_password")
            
            if not username:
                self.report_error("Gmail username not found in secrets")
                return {
                    "success": False,
                    "error": "Secret 'gmail_username' not configured. Use: janito --set-secret gmail_username=your-email@gmail.com",
                    "folder": folder
                }
            
            if not password:
                self.report_error("Gmail password not found in secrets")
                return {
                    "success": False,
                    "error": "Secret 'gmail_password' not configured. Use: janito --set-secret gmail_password=your-app-password",
                    "folder": folder
                }
            
            # Connect to Gmail IMAP server
            self.report_progress(" Connecting to imap.gmail.com...")
            
            mail = imaplib.IMAP4_SSL(self.IMAP_SERVER, self.IMAP_PORT)
            mail.login(username, password)
            
            # Select the mailbox
            status, messages = mail.select(folder)
            if status != "OK":
                mail.logout()
                self.report_error(f"Failed to select folder: {folder}")
                return {
                    "success": False,
                    "error": f"Failed to select folder '{folder}': {_safe_decode(messages[0]) if messages else 'Unknown error'}",
                    "folder": folder
                }
            
            # Build search criteria
            search_criteria = self._build_search_criteria(
                message_ids=message_ids,
                search_query=search_query,
                older_than_days=older_than_days,
                older_than_date=older_than_date,
                from_address=from_address,
                subject_contains=subject_contains
            )
            
            if not search_criteria:
                mail.logout()
                self.report_error("No deletion criteria specified")
                return {
                    "success": False,
                    "error": "Must specify at least one deletion criteria: message_ids, search_query, older_than_days, older_than_date, from_address, or subject_contains",
                    "folder": folder
                }
            
            self.report_progress(f" Searching for emails to delete...")
            
            # Search for emails matching criteria
            status, message_ids_list = mail.search(None, search_criteria)
            
            if status != "OK":
                mail.logout()
                self.report_error("Failed to search emails")
                return {
                    "success": False,
                    "error": "Failed to search emails",
                    "folder": folder
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
                    "dry_run": dry_run
                }
            
            # Convert bytes to strings for display
            id_strings = [_safe_decode(mid) for mid in ids_to_delete]
            
            if dry_run:
                self.report_progress(f" Found {found_count} emails matching criteria (dry run - no deletion)")
                mail.logout()
                self.report_result(f"DRY RUN: Would delete {found_count} emails: {id_strings[:10]}{'...' if found_count > 10 else ''}")
                return {
                    "success": True,
                    "folder": folder,
                    "found_count": found_count,
                    "deleted_count": 0,
                    "message_ids": id_strings,
                    "dry_run": True
                }
            
            # Confirm deletion with Gmail
            self.report_progress(f" Found {found_count} emails, marking as deleted...")
            
            # Mark emails as deleted using STORE command
            deleted_count = 0
            for msg_id in ids_to_delete:
                try:
                    status, response = mail.store(msg_id, "+FLAGS", "\\Deleted")
                    if status == "OK":
                        deleted_count += 1
                except Exception:
                    continue
            
            self.report_progress(f" Marked {deleted_count} emails as deleted, expunging...")
            
            # Permanently delete marked emails
            status, expunge_result = mail.expunge()
            
            # Logout
            mail.logout()
            
            if status == "OK":
                self.report_result(f"Successfully deleted {deleted_count} emails from {folder}")
                return {
                    "success": True,
                    "folder": folder,
                    "found_count": found_count,
                    "deleted_count": deleted_count,
                    "message_ids": id_strings,
                    "dry_run": False
                }
            else:
                self.report_error(f"Expunge returned status: {status}")
                return {
                    "success": False,
                    "error": f"Expunge failed with status: {status}",
                    "folder": folder
                }
            
        except imaplib.IMAP4.error as e:
            error_msg = _safe_decode(e.args[0]) if e.args else str(e)
            self.report_error(f"IMAP error: {error_msg}")
            return {
                "success": False,
                "error": f"IMAP connection error: {error_msg}",
                "folder": folder
            }
            
        except Exception as e:
            self.report_error(f"Error deleting emails: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to delete emails: {str(e)}",
                "folder": folder
            }
    
    def _build_search_criteria(
        self,
        message_ids: Optional[List[str]] = None,
        search_query: Optional[str] = None,
        older_than_days: Optional[int] = None,
        older_than_date: Optional[str] = None,
        from_address: Optional[str] = None,
        subject_contains: Optional[str] = None
    ) -> Optional[str]:
        """
        Build IMAP search criteria from provided parameters.
        
        Args:
            Various filter parameters
            
        Returns:
            IMAP search criteria string, or None if no criteria provided
        """
        import datetime
        
        if search_query:
            return search_query
        
        criteria_parts = []
        
        # Handle specific message IDs
        if message_ids:
            id_criteria = " OR ".join([f"UID {mid}" for mid in message_ids])
            criteria_parts.append(id_criteria)
        
        # Handle date-based deletion
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
