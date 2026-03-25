#!/usr/bin/env python3
"""
Move Emails Tool - A class-based tool for moving emails between folders in Gmail via IMAP.

This tool copies emails to a target folder and removes them from the source.
It's useful for organizing emails (e.g., archiving, filing, labeling).
"""

import imaplib
import datetime
from typing import Dict, Any, Optional, List, Union
from ...tooling import BaseTool
from ..decorator import tool


def _safe_decode(data: Union[bytes, str]) -> str:
    """Safely decode bytes to string, or return string as-is."""
    if isinstance(data, bytes):
        return data.decode('utf-8', errors='replace')
    return str(data)


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
        janito4 --set-secret gmail_username=your-email@gmail.com
        janito4 --set-secret gmail_password=your-app-password
    """
    
    IMAP_SERVER = "imap.gmail.com"
    IMAP_PORT = 993
    
    def run(
        self,
        source_folder: str = "INBOX",
        target_folder: str = "[Gmail]/All Mail",
        message_ids: Optional[List[str]] = None,
        search_query: Optional[str] = None,
        from_address: Optional[str] = None,
        subject_contains: Optional[str] = None,
        older_than_days: Optional[int] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
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
            from janito4.secrets_config import get_secret
            
            action = "Counting (dry run)" if dry_run else "Moving"
            self.report_start(f"{action} emails from {source_folder} to {target_folder}")
            
            username = get_secret("gmail_username")
            password = get_secret("gmail_password")
            
            if not username:
                self.report_error("Gmail username not found in secrets")
                return {
                    "success": False,
                    "error": "Secret 'gmail_username' not configured. Use: janito4 --set-secret gmail_username=your-email@gmail.com",
                    "source_folder": source_folder,
                    "target_folder": target_folder
                }
            
            if not password:
                self.report_error("Gmail password not found in secrets")
                return {
                    "success": False,
                    "error": "Secret 'gmail_password' not configured. Use: janito4 --set-secret gmail_password=your-app-password",
                    "source_folder": source_folder,
                    "target_folder": target_folder
                }
            
            # Connect to Gmail IMAP server
            self.report_progress(" Connecting to imap.gmail.com...")
            
            mail = imaplib.IMAP4_SSL(self.IMAP_SERVER, self.IMAP_PORT)
            mail.login(username, password)
            
            # Select the source folder
            status, messages = mail.select(source_folder)
            if status != "OK":
                mail.logout()
                self.report_error(f"Failed to select source folder: {source_folder}")
                return {
                    "success": False,
                    "error": f"Failed to select source folder '{source_folder}'",
                    "source_folder": source_folder,
                    "target_folder": target_folder
                }
            
            # Build search criteria
            search_criteria = self._build_search_criteria(
                message_ids=message_ids,
                search_query=search_query,
                from_address=from_address,
                subject_contains=subject_contains,
                older_than_days=older_than_days
            )
            
            if not search_criteria:
                mail.logout()
                self.report_error("No search criteria specified")
                return {
                    "success": False,
                    "error": "Must specify at least one criteria: message_ids, search_query, from_address, subject_contains, or older_than_days",
                    "source_folder": source_folder,
                    "target_folder": target_folder
                }
            
            self.report_progress(f" Searching for emails to move...")
            
            # Search for emails
            status, message_ids_list = mail.search(None, search_criteria)
            
            if status != "OK":
                mail.logout()
                self.report_error("Failed to search emails")
                return {
                    "success": False,
                    "error": "Failed to search emails",
                    "source_folder": source_folder,
                    "target_folder": target_folder
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
                    "dry_run": dry_run
                }
            
            id_strings = [_safe_decode(mid) for mid in ids_to_move]
            
            if dry_run:
                mail.logout()
                self.report_result(f"DRY RUN: Would move {found_count} emails from {source_folder} to {target_folder}")
                return {
                    "success": True,
                    "source_folder": source_folder,
                    "target_folder": target_folder,
                    "found_count": found_count,
                    "moved_count": 0,
                    "message_ids": id_strings,
                    "dry_run": True
                }
            
            # Copy emails to target folder
            self.report_progress(f" Copying {found_count} emails to {target_folder}...")
            
            moved_count = 0
            failed_ids = []
            
            for msg_id in ids_to_move:
                try:
                    # Try MOVE command first (Gmail-specific)
                    status, response = mail.move(msg_id, target_folder)
                    if status == "OK":
                        moved_count += 1
                    else:
                        failed_ids.append(_safe_decode(msg_id))
                except imaplib.IMAP4.error:
                    # Fallback: COPY then DELETE
                    try:
                        copy_status, _ = mail.copy(msg_id, target_folder)
                        if copy_status == "OK":
                            # Mark original for deletion
                            mail.store(msg_id, "+FLAGS", "\\Deleted")
                            moved_count += 1
                        else:
                            failed_ids.append(_safe_decode(msg_id))
                    except Exception:
                        failed_ids.append(_safe_decode(msg_id))
                except Exception:
                    failed_ids.append(_safe_decode(msg_id))
            
            # Expunge deleted messages from source
            if moved_count > 0:
                self.report_progress(f" Expunging moved emails from source...")
                mail.expunge()
            
            # Logout
            mail.logout()
            
            self.report_result(f"Moved {moved_count} emails from {source_folder} to {target_folder}")
            
            result = {
                "success": True,
                "source_folder": source_folder,
                "target_folder": target_folder,
                "found_count": found_count,
                "moved_count": moved_count,
                "message_ids": id_strings,
                "dry_run": False
            }
            
            if failed_ids:
                result["failed_ids"] = failed_ids
                result["warning"] = f"Failed to move {len(failed_ids)} emails"
            
            return result
            
        except imaplib.IMAP4.error as e:
            error_msg = _safe_decode(e.args[0]) if e.args else str(e)
            self.report_error(f"IMAP error: {error_msg}")
            return {
                "success": False,
                "error": f"IMAP connection error: {error_msg}",
                "source_folder": source_folder,
                "target_folder": target_folder
            }
            
        except Exception as e:
            self.report_error(f"Error moving emails: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to move emails: {str(e)}",
                "source_folder": source_folder,
                "target_folder": target_folder
            }
    
    def _build_search_criteria(
        self,
        message_ids: Optional[List[str]] = None,
        search_query: Optional[str] = None,
        from_address: Optional[str] = None,
        subject_contains: Optional[str] = None,
        older_than_days: Optional[int] = None
    ) -> Optional[str]:
        """
        Build IMAP search criteria for move operation.
        """
        if search_query:
            return search_query
        
        criteria_parts = []
        
        if message_ids:
            for mid in message_ids:
                criteria_parts.append(f"UID {mid}")
        
        if older_than_days is not None:
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=older_than_days)
            date_str = cutoff_date.strftime("%d-%b-%Y")
            criteria_parts.append(f"BEFORE {date_str}")
        
        if from_address:
            criteria_parts.append(f"FROM {from_address}")
        
        if subject_contains:
            criteria_parts.append(f"SUBJECT {subject_contains}")
        
        if not criteria_parts:
            return None
        
        return " ".join(criteria_parts)
