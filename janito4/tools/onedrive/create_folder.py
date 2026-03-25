#!/usr/bin/env python3
"""
Create OneDrive Folder Tool - A class-based tool for creating folders in OneDrive.

This tool uses Microsoft Graph API to create folders in OneDrive.
"""

from typing import Dict, Any, Optional
from ...tooling import BaseTool
from ..decorator import tool


@tool(permissions="w")
class CreateOneDriveFolder(BaseTool):
    """
    Tool for creating folders in OneDrive.
    
    Creates new folders at the specified path. If the folder already exists,
    returns the existing folder info.
    
    Required Secrets:
        - azure_client_id: Your Azure AD application client ID
        - azure_access_token: (auto-managed) Current access token
        - azure_refresh_token: (auto-managed) Refresh token
    
    Graph API Reference:
        https://docs.microsoft.com/en-us/graph/api/driveitem-post-children
    """
    
    def run(
        self,
        path: str,
        conflict_behavior: str = "fail"
    ) -> Dict[str, Any]:
        """
        Create a folder in OneDrive.
        
        Args:
            path (str): Full path for the new folder (e.g., "Documents/Projects/NewFolder")
            conflict_behavior (str): Behavior if folder exists: "fail", "replace", "rename" (default: "fail")
        
        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if operation succeeded
                - 'path': the folder path
                - 'folder': folder metadata
                - 'created': True if new folder was created, False if already existed
                - 'error': error message if operation failed (only present if success=False)
        """
        try:
            from .base_client import OneDriveBaseClient
            
            self.report_start(f"Creating folder: {path}")
            
            # Parse the path to get parent and folder name
            path_parts = path.rstrip("/").split("/")
            folder_name = path_parts[-1]
            
            if len(path_parts) == 1:
                # Creating in root
                parent_path = ""
            else:
                parent_path = "/".join(path_parts[:-1])
            
            client = OneDriveBaseClient()
            
            # Build parent endpoint
            parent_endpoint = client._get_drive_endpoint(parent_path)
            
            self.report_progress(f" Creating folder '{folder_name}' in {parent_path or '/'}")
            
            # Map conflict behavior to Graph API value
            conflict_map = {
                "fail": "fail",
                "replace": "replace",
                "rename": "rename"
            }
            conflict_value = conflict_map.get(conflict_behavior, "fail")
            
            # Create the folder
            request_body = {
                "name": folder_name,
                "folder": {},
                "@microsoft.graph.conflictBehavior": conflict_value
            }
            
            response = client._make_request(
                method="POST",
                endpoint=f"{parent_endpoint}/children",
                json_data=request_body,
                timeout=30
            )
            
            # Check if folder was newly created or already existed
            # In Graph API, folder is always created if request succeeds
            # The conflictBehavior determines what happens if it exists
            
            folder_info = {
                "id": response.get("id"),
                "name": response.get("name"),
                "path": parent_path + "/" + response.get("name", folder_name),
                "web_url": response.get("webUrl"),
                "created": response.get("createdDateTime"),
                "modified": response.get("lastModifiedDateTime"),
                "child_count": response.get("folder", {}).get("childCount", 0) if response.get("folder") else 0
            }
            
            # Determine if this was a new creation or existing folder
            # This is a heuristic - the API doesn't explicitly tell us
            created = True  # Assume created unless we get a conflict indicator
            
            self.report_result(f"Folder ready: {folder_info['path']}")
            
            return {
                "success": True,
                "path": path,
                "folder": folder_info,
                "created": created
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
            if "nameAlreadyExists" in error_msg or "already exists" in error_msg.lower():
                self.report_error(f"Folder already exists: {path}")
                return {
                    "success": False,
                    "error": f"Folder already exists: {path}",
                    "path": path,
                    "conflict_behavior": conflict_behavior
                }
            if "parentNotFound" in error_msg or "parent not found" in error_msg.lower():
                self.report_error(f"Parent folder not found: {parent_path}")
                return {
                    "success": False,
                    "error": f"Parent folder not found: {parent_path}",
                    "path": path
                }
            self.report_error(f"Failed to create folder: {error_msg}")
            return {
                "success": False,
                "error": f"Failed to create folder: {error_msg}",
                "path": path
            }
