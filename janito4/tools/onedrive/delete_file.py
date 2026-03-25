#!/usr/bin/env python3
"""
Delete OneDrive File Tool - A class-based tool for deleting files and folders from OneDrive.

This tool uses Microsoft Graph API to delete files and folders from OneDrive.
"""

from typing import Dict, Any, Optional
from ...tooling import BaseTool
from ..decorator import tool


@tool(permissions="rw")
class DeleteOneDriveFile(BaseTool):
    """
    Tool for deleting files and folders from OneDrive.
    
    WARNING: This operation is destructive. Deleted items are moved to the
    recycle bin and can be recovered within the retention period.
    
    Required Secrets:
        - azure_client_id: Your Azure AD application client ID
        - azure_access_token: (auto-managed) Current access token
        - azure_refresh_token: (auto-managed) Refresh token
    
    Graph API Reference:
        https://docs.microsoft.com/en-us/graph/api/driveitem-delete
    """
    
    def run(
        self,
        path: str,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Delete a file or folder from OneDrive.
        
        Args:
            path (str): Full path to the file or folder to delete
            dry_run (bool): If True, only check if item exists without deleting (default: False)
        
        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if operation succeeded
                - 'path': the item path
                - 'deleted': True if item was deleted (False if dry_run)
                - 'item_info': metadata of the item if dry_run=True
                - 'error': error message if operation failed (only present if success=False)
        """
        try:
            from .base_client import OneDriveBaseClient
            
            action = "Checking (dry run)" if dry_run else "Deleting"
            self.report_start(f"{action}: {path}")
            
            client = OneDriveBaseClient()
            
            # First, get the item to confirm it exists and get info
            endpoint = client._get_drive_endpoint(path)
            
            self.report_progress(" Checking item exists...")
            
            try:
                item_info = client._make_request(
                    method="GET",
                    endpoint=endpoint,
                    params={"$select": "id,name,file,folder,size"},
                    timeout=30
                )
            except Exception as e:
                if "ItemNotFound" in str(e) or "not found" in str(e).lower():
                    self.report_error(f"Item not found: {path}")
                    return {
                        "success": False,
                        "error": f"Item not found: {path}",
                        "path": path
                    }
                raise
            
            item_type = "folder" if item_info.get("folder") else "file"
            item_name = item_info.get("name")
            item_size = item_info.get("size")
            
            item_summary = {
                "id": item_info.get("id"),
                "name": item_name,
                "type": item_type,
                "size": item_size
            }
            
            if dry_run:
                self.report_result(f"DRY RUN: Would delete {item_type}: {item_name}")
                return {
                    "success": True,
                    "path": path,
                    "deleted": False,
                    "dry_run": True,
                    "item_info": item_summary
                }
            
            # Perform deletion
            self.report_progress(f" Deleting {item_type}: {item_name}...")
            
            client._make_request(
                method="DELETE",
                endpoint=endpoint,
                timeout=30
            )
            
            self.report_result(f"Successfully deleted: {path}")
            
            return {
                "success": True,
                "path": path,
                "deleted": True,
                "dry_run": False,
                "deleted_item": item_summary
            }
            
        except ValueError as e:
            self.report_error(str(e))
            return {
                "success": False,
                "error": str(e),
                "path": path
            }
        except Exception as e:
            error_msg = str(e)
            if "ItemNotFound" in error_msg or "not found" in error_msg.lower():
                self.report_error(f"Item not found: {path}")
                return {
                    "success": False,
                    "error": f"Item not found: {path}",
                    "path": path
                }
            self.report_error(f"Failed to delete: {error_msg}")
            return {
                "success": False,
                "error": f"Failed to delete: {error_msg}",
                "path": path
            }
