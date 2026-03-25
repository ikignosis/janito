#!/usr/bin/env python3
"""
Count Emails Tool - A class-based tool for counting emails in Gmail folders via IMAP.

This tool connects to Gmail using IMAP and counts emails in folders
without fetching the full email content. Credentials are securely retrieved
from the secrets module.
"""

import imaplib
from typing import Dict, Any, Optional
from ...tooling import BaseTool
from ..decorator import tool


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
        janito4 --set-secret gmail_username=your-email@gmail.com
        janito4 --set-secret gmail_password=your-app-password
    """
    
    IMAP_SERVER = "imap.gmail.com"
    IMAP_PORT = 993
    
    def run(
        self,
        folder: str = "INBOX",
        unread_only: bool = False,
        search_query: Optional[str] = None
    ) -> Dict[str, Any]:
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
            # Import secrets here to allow module to load without secrets dependency
            try:
                from janito4.secrets_config import get_secret
            except ImportError:
                self.report_error("Secrets module not available")
                return {
                    "success": False,
                    "error": "Could not import secrets module. Ensure janito4 is properly installed.",
                    "folder": folder
                }
            
            # Fetch credentials from secrets
            self.report_start(f"Connecting to Gmail to count emails in {folder}")
            
            username = get_secret("gmail_username")
            password = get_secret("gmail_password")
            
            if not username:
                self.report_error("Gmail username not found in secrets")
                return {
                    "success": False,
                    "error": "Secret 'gmail_username' not configured. Use: janito4 --set-secret gmail_username=your-email@gmail.com",
                    "folder": folder
                }
            
            if not password:
                self.report_error("Gmail password not found in secrets")
                return {
                    "success": False,
                    "error": "Secret 'gmail_password' not configured. Use: janito4 --set-secret gmail_password=your-app-password",
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
                    "error": f"Failed to select folder '{folder}': {messages[0].decode() if messages else 'Unknown error'}",
                    "folder": folder
                }
            
            # Count total emails
            self.report_progress(" Counting total emails...")
            status, total_data = mail.search(None, "ALL")
            if status != "OK":
                mail.logout()
                self.report_error("Failed to count total emails")
                return {
                    "success": False,
                    "error": "Failed to count total emails",
                    "folder": folder
                }
            total_count = len(total_data[0].split()) if total_data[0] else 0
            
            # Count unread emails
            self.report_progress(" Counting unread emails...")
            status, unread_data = mail.search(None, "UNSEEN")
            if status != "OK":
                mail.logout()
                self.report_error("Failed to count unread emails")
                return {
                    "success": False,
                    "error": "Failed to count unread emails",
                    "folder": folder
                }
            unread_count = len(unread_data[0].split()) if unread_data[0] else 0
            
            # Count emails matching search criteria
            if search_query:
                search_criteria = search_query
            elif unread_only:
                search_criteria = "UNSEEN"
            else:
                search_criteria = "ALL"
            
            self.report_progress(f" Counting emails matching: {search_criteria}...")
            status, matching_data = mail.search(None, search_criteria)
            if status != "OK":
                mail.logout()
                self.report_error("Failed to count matching emails")
                return {
                    "success": False,
                    "error": "Failed to count matching emails",
                    "folder": folder
                }
            matching_count = len(matching_data[0].split()) if matching_data[0] else 0
            
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
                "search_criteria": search_criteria
            }
            
        except imaplib.IMAP4.error as e:
            error_msg = e.args[0].decode() if e.args else str(e)
            self.report_error(f"IMAP error: {error_msg}")
            return {
                "success": False,
                "error": f"IMAP connection error: {error_msg}",
                "folder": folder
            }
            
        except Exception as e:
            self.report_error(f"Error counting emails: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to count emails: {str(e)}",
                "folder": folder
            }
