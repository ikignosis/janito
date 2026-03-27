#!/usr/bin/env python3
"""
Search OneDrive Files Tool - A class-based tool for searching files in OneDrive.

This tool uses Microsoft Graph API to search for files and folders in OneDrive.
"""

import re
from typing import Dict, Any, Optional, List
from ...tooling import BaseTool
from ..decorator import tool


@tool(permissions="r")
class SearchOneDriveFiles(BaseTool):
    """
    Tool for searching files and folders in OneDrive.
    
    Uses Microsoft Graph API to find items by name or content.
    
    Required Secrets:
        - azure_client_id: Your Azure AD application client ID
        - azure_access_token: (auto-managed) Current access token
        - azure_refresh_token: (auto-managed) Refresh token
    
    Graph API Reference:
        https://docs.microsoft.com/en-us/graph/api/driveitem-search
    """
    
    def run(
        self,
        query: str,
        folder_path: Optional[str] = None,
        file_type_filter: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Search for files and folders in OneDrive.
        
        Args:
            query (str): Search query (searches in file names by default)
            folder_path (Optional[str]): Limit search to specific folder (default: entire drive)
            file_type_filter (Optional[str]): Filter by file extension (e.g., "docx", "pdf", "xlsx")
            limit (int): Maximum number of results to return (default: 20)
        
        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if operation succeeded
                - 'query': the search query
                - 'items': list of matching file/folder dictionaries
                - 'total_count': number of matches found
                - 'error': error message if operation failed (only present if success=False)
        """
        try:
            from .base_client import OneDriveBaseClient
            
            self.report_start(f"Searching OneDrive for: {query}")
            
            client = OneDriveBaseClient()
            
            # Build search query
            search_query = query
            
            # Apply folder constraint if specified
            if folder_path:
                # For folder-specific search, we list and filter
                self.report_progress(f" Searching in folder: {folder_path}")
                
                endpoint = client._get_drive_children_endpoint(folder_path)
                
                params = {
                    "$top": 999,  # Get all items from folder for client-side filtering
                    "$orderby": "name",
                    "$select": "id,name,file,folder,size,createdDateTime,lastModifiedDateTime,webUrl,parentReference"
                }
                
                response = client._make_request(
                    method="GET",
                    endpoint=endpoint,
                    params=params,
                    timeout=30
                )
                
                all_items = response.get("value", [])
                
                # Filter items by search query (case-insensitive name match)
                query_lower = query.lower()
                matching_items = [
                    item for item in all_items
                    if query_lower in item.get("name", "").lower()
                ]
                
            else:
                # Use Microsoft Search API for global search
                self.report_progress(" Searching entire OneDrive...")
                
                endpoint = "/me/drive/root/search(q='" + query.replace("'", "''") + "')"
                
                params = {
                    "$top": limit,
                    "$select": "id,name,file,folder,size,createdDateTime,lastModifiedDateTime,webUrl,parentReference"
                }
                
                response = client._make_request(
                    method="GET",
                    endpoint=endpoint,
                    params=params,
                    timeout=30
                )
                
                matching_items = response.get("value", [])
            
            # Apply file type filter if specified
            if file_type_filter:
                ext = file_type_filter.lower().lstrip(".")
                matching_items = [
                    item for item in matching_items
                    if item.get("name", "").lower().endswith(f".{ext}")
                ]
            
            # Limit results
            if len(matching_items) > limit:
                matching_items = matching_items[:limit]
            
            # Format items for cleaner output
            formatted_items = []
            for item in matching_items:
                formatted = {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "type": "folder" if item.get("folder") else "file",
                    "size": item.get("size"),
                    "created": item.get("createdDateTime"),
                    "modified": item.get("lastModifiedDateTime"),
                    "web_url": item.get("webUrl"),
                }
                
                if item.get("folder"):
                    formatted["child_count"] = item.get("folder", {}).get("childCount")
                
                if item.get("file"):
                    formatted["mime_type"] = item.get("file", {}).get("mimeType")
                
                if item.get("parentReference"):
                    parent_path = item["parentReference"].get("path", "")
                    # Handle both /me/drive/root: and /users/{userId}/drive/root: formats
                    parent_path = parent_path.replace("/me/drive/root:", "")
                    parent_path = re.sub(r"^/users/[^/]+/drive/root:", "", parent_path)
                    formatted["parent_path"] = parent_path or "/"
                
                formatted_items.append(formatted)
            
            self.report_result(f"Found {len(formatted_items)} matches for '{query}'")
            
            return {
                "success": True,
                "query": query,
                "folder_path": folder_path,
                "file_type_filter": file_type_filter,
                "items": formatted_items,
                "total_count": len(formatted_items)
            }
            
        except ValueError as e:
            self.report_error(str(e))
            return {
                "success": False,
                "error": str(e),
                "query": query
            }
        except Exception as e:
            self.report_error(f"Search failed: {str(e)}")
            return {
                "success": False,
                "error": f"Search failed: {str(e)}",
                "query": query
            }
