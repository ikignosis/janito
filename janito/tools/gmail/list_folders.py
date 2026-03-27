#!/usr/bin/env python3
"""
List Folders Tool - A class-based tool for listing all Gmail folders/labels via IMAP.

This tool connects to Gmail using IMAP and retrieves all available folders
and labels. Credentials are securely retrieved from the secrets module.
"""

import imaplib
from typing import Dict, Any, List, Optional
from ...tooling import BaseTool
from ..decorator import tool


@tool(permissions="r")
class ListFolders(BaseTool):
    """
    Tool for listing all Gmail folders and labels via IMAP.
    
    This tool retrieves all available mailbox folders and Gmail labels
    from your Gmail account, including system folders like INBOX and
    custom labels you've created.
    
    Requires the following secrets to be configured:
    - gmail_username: Your Gmail address
    - gmail_password: Your Gmail app password (for 2FA accounts, use an app password)
    
    Usage:
        janito --set-secret gmail_username=your-email@gmail.com
        janito --set-secret gmail_password=your-app-password
    """
    
    IMAP_SERVER = "imap.gmail.com"
    IMAP_PORT = 993
    
    # Common Gmail folders/labels mapping
    GMAIL_LABELS = {
        "[Gmail]/All Mail": "Contains all your messages regardless of other labels",
        "[Gmail]/Drafts": "Your draft messages",
        "[Gmail]/Important": "Messages marked as important by Gmail",
        "[Gmail]/Sent Mail": "Messages you've sent",
        "[Gmail]/Spam": "Messages marked as spam by Gmail",
        "[Gmail]/Starred": "Messages you've starred",
        "[Gmail]/Trash": "Messages you've deleted",
        "INBOX": "Primary inbox folder for incoming messages",
    }
    
    def run(
        self,
        include_counts: bool = False
    ) -> Dict[str, Any]:
        """
        List all Gmail folders and labels.
        
        Args:
            include_counts (bool): If True, include email counts for each folder (default: False)
                                    Note: This makes the operation slightly slower as it needs
                                    to query each folder separately.
        
        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if operation succeeded
                - 'folders': list of folder dictionaries with name and info
                - 'total_count': total number of folders/labels
                - 'error': error message if operation failed (only present if success=False)
        """
        try:
            # Import secrets here to allow module to load without secrets dependency
            try:
                from janito.secrets_config import get_secret
            except ImportError:
                self.report_error("Secrets module not available")
                return {
                    "success": False,
                    "error": "Could not import secrets module. Ensure janito is properly installed."
                }
            
            # Fetch credentials from secrets
            self.report_start("Connecting to Gmail to list folders")
            
            username = get_secret("gmail_username")
            password = get_secret("gmail_password")
            
            if not username:
                self.report_error("Gmail username not found in secrets")
                return {
                    "success": False,
                    "error": "Secret 'gmail_username' not configured. Use: janito --set-secret gmail_username=your-email@gmail.com"
                }
            
            if not password:
                self.report_error("Gmail password not found in secrets")
                return {
                    "success": False,
                    "error": "Secret 'gmail_password' not configured. Use: janito --set-secret gmail_password=your-app-password"
                }
            
            # Connect to Gmail IMAP server
            self.report_progress(" Connecting to imap.gmail.com...")
            
            mail = imaplib.IMAP4_SSL(self.IMAP_SERVER, self.IMAP_PORT)
            mail.login(username, password)
            
            # List all folders using LIST command
            self.report_progress(" Retrieving folder list...")
            status, folder_list = mail.list()
            
            if status != "OK":
                mail.logout()
                self.report_error("Failed to retrieve folder list")
                return {
                    "success": False,
                    "error": "Failed to retrieve folder list from Gmail"
                }
            
            folders = []
            for folder_data in folder_list:
                if not folder_data:
                    continue
                    
                # Parse folder data - format is: b'(\\HasNoChildren) "/" "Folder Name"'
                folder_info = self._parse_folder_entry(folder_data)
                if folder_info:
                    folders.append(folder_info)
            
            # Sort folders alphabetically
            folders.sort(key=lambda x: x["name"].lower())
            
            # Get email counts for each folder if requested
            if include_counts and folders:
                self.report_progress(f" Getting email counts for {len(folders)} folders...")
                folders = self._add_folder_counts(mail, folders)
            
            # Logout
            mail.logout()
            
            # Format output
            folder_names = [f["name"] for f in folders]
            folder_summary = ", ".join(folder_names[:10])
            if len(folder_names) > 10:
                folder_summary += f" ... and {len(folder_names) - 10} more"
            
            self.report_result(f"Found {len(folders)} folders: {folder_summary}")
            
            return {
                "success": True,
                "folders": folders,
                "total_count": len(folders),
                "gmail_labels_info": self.GMAIL_LABELS
            }
            
        except imaplib.IMAP4.error as e:
            error_msg = e.args[0].decode() if e.args and isinstance(e.args[0], bytes) else str(e.args[0] if e.args else e)
            self.report_error(f"IMAP error: {error_msg}")
            return {
                "success": False,
                "error": f"IMAP connection error: {error_msg}"
            }
            
        except Exception as e:
            self.report_error(f"Error listing folders: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to list folders: {str(e)}"
            }
    
    def _parse_folder_entry(self, folder_data: bytes) -> Optional[Dict[str, Any]]:
        """
        Parse a single folder entry from IMAP LIST response.
        
        Args:
            folder_data (bytes): Raw folder data from IMAP response
        
        Returns:
            Optional[Dict[str, Any]]: Parsed folder information or None if parsing fails
        """
        try:
            # Decode bytes to string
            if isinstance(folder_data, bytes):
                folder_str = folder_data.decode('utf-8', errors='replace')
            else:
                folder_str = str(folder_data)
            
            # IMAP LIST response format: (\Flags) "/" "Folder Name"
            # or: (\Flags) "/" "Parent/Child"
            
            # Find all quoted strings - the last one is the folder name
            import re
            quotes = re.findall(r'"([^"]*)"', folder_str)
            if not quotes:
                return None
            
            # The last quoted string is the folder name
            folder_name = quotes[-1]
            
            # Parse flags from parentheses
            flags_match = re.search(r'\(([^)]*)\)', folder_str)
            flags = []
            if flags_match:
                flags = [f.strip() for f in flags_match.group(1).split() if f.strip()]
            
            # Determine if it's a Gmail special label
            is_gmail_label = folder_name.startswith("[Gmail]/")
            
            return {
                "name": folder_name,
                "flags": flags,
                "is_gmail_label": is_gmail_label,
                "description": self.GMAIL_LABELS.get(folder_name, "")
            }
            
        except Exception:
            return None
    
    def _add_folder_counts(self, mail: imaplib.IMAP4_SSL, folders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Add email counts to each folder.
        
        Args:
            mail (imaplib.IMAP4_SSL): Active IMAP connection
            folders (List[Dict[str, Any]]): List of folder dictionaries
        
        Returns:
            List[Dict[str, Any]]: Folders with counts added
        """
        for folder in folders:
            try:
                # Select folder to get count
                folder_encoded = folder["name"].encode('ascii', 'strict')
                status, _ = mail.select(folder_encoded)
                
                if status == "OK":
                    # Search for all messages
                    status, data = mail.search(None, "ALL")
                    if status == "OK" and data[0]:
                        folder["total_count"] = len(data[0].split())
                    else:
                        folder["total_count"] = 0
                    
                    # Search for unread messages
                    status, data = mail.search(None, "UNSEEN")
                    if status == "OK" and data[0]:
                        folder["unread_count"] = len(data[0].split())
                    else:
                        folder["unread_count"] = 0
                else:
                    folder["total_count"] = 0
                    folder["unread_count"] = 0
                    
            except Exception:
                folder["total_count"] = 0
                folder["unread_count"] = 0
        
        return folders


if __name__ == "__main__":
    # Allow running the tool directly for testing
    import json
    
    tool = ListFolders()
    result = tool.run(include_counts=True)
    print(json.dumps(result, indent=2))
