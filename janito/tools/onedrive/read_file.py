#!/usr/bin/env python3
"""
Read OneDrive File Tool - A class-based tool for reading file metadata and content.

This tool uses Microsoft Graph API to read file metadata from OneDrive.
For large files or binary content, use DownloadOneDriveFile instead.
"""

import re
from typing import Dict, Any, Optional
from ...tooling import BaseTool
from ..decorator import tool


@tool(permissions="r")
class ReadOneDriveFile(BaseTool):
    """
    Tool for reading file metadata from OneDrive.
    
    Returns file metadata including name, size, dates, and web URL.
    For file content, use DownloadOneDriveFile or read specific text file types.
    
    Required Secrets:
        - azure_client_id: Your Azure AD application client ID
        - azure_access_token: (auto-managed) Current access token
        - azure_refresh_token: (auto-managed) Refresh token
    
    Graph API Reference:
        https://docs.microsoft.com/en-us/graph/api/driveitem-get
    """
    
    # Supported text-based file types for content reading
    TEXT_TYPES = {
        "text/plain", "text/csv", "text/html", "text/css", "text/javascript",
        "text/xml", "text/markdown", "text/x-python", "application/json",
        "application/xml", "application/javascript", "application/x-python"
    }
    
    def run(
        self,
        path: str,
        include_content: bool = False,
        max_content_length: int = 10000
    ) -> Dict[str, Any]:
        """
        Read file metadata from OneDrive.
        
        Args:
            path (str): Full path to the file (e.g., "Documents/report.pdf")
            include_content (bool): If True, attempt to read text file content (default: False)
            max_content_length (int): Maximum content length to read in characters (default: 10000)
        
        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if operation succeeded
                - 'path': the file path
                - 'file': file metadata dictionary
                - 'content': file content if include_content=True and file is text-based
                - 'error': error message if operation failed (only present if success=False)
        """
        try:
            from .base_client import OneDriveBaseClient
            
            self.report_start(f"Reading file: {path}")
            
            client = OneDriveBaseClient()
            
            # Build the endpoint for getting item by path
            endpoint = client._get_drive_endpoint(path)
            
            self.report_progress(" Fetching file metadata from Microsoft Graph...")
            
            # Get file metadata
            metadata = client._make_request(
                method="GET",
                endpoint=endpoint,
                params={
                    "$select": "id,name,file,folder,size,createdDateTime,lastModifiedDateTime,webUrl,parentReference,content"
                },
                timeout=30
            )
            
            # Format the response
            file_info = {
                "id": metadata.get("id"),
                "name": metadata.get("name"),
                "type": "folder" if metadata.get("folder") else "file",
                "size": metadata.get("size"),
                "created": metadata.get("createdDateTime"),
                "modified": metadata.get("lastModifiedDateTime"),
                "web_url": metadata.get("webUrl"),
            }
            
            if metadata.get("folder"):
                file_info["child_count"] = metadata.get("folder", {}).get("childCount")
            
            if metadata.get("file"):
                file_info["mime_type"] = metadata.get("file", {}).get("mimeType")
            
            if metadata.get("parentReference"):
                parent_path = metadata["parentReference"].get("path", "")
                # Handle both /me/drive/root: and /users/{userId}/drive/root: formats
                parent_path = parent_path.replace("/me/drive/root:", "")
                parent_path = re.sub(r"^/users/[^/]+/drive/root:", "", parent_path)
                file_info["parent_path"] = parent_path or "/"
            
            result = {
                "success": True,
                "path": path,
                "file": file_info
            }
            
            # Try to read content if requested
            if include_content:
                mime_type = file_info.get("mime_type", "")
                
                if mime_type in self.TEXT_TYPES or mime_type.startswith("text/"):
                    self.report_progress(" Reading text content...")
                    try:
                        # Get content directly from the content property
                        content = metadata.get("content", "")
                        
                        if isinstance(content, str):
                            if len(content) > max_content_length:
                                content = content[:max_content_length] + f"\n... [truncated, total {len(content)} chars]"
                        elif isinstance(content, bytes):
                            content = content.decode("utf-8", errors="replace")
                            if len(content) > max_content_length:
                                content = content[:max_content_length] + f"\n... [truncated, total {len(content)} chars]"
                        
                        result["content"] = content
                    except Exception as e:
                        result["content_error"] = f"Could not read content: {str(e)}"
                else:
                    result["content_skipped"] = f"Binary files not readable. Use DownloadOneDriveFile for: {mime_type}"
            
            self.report_result(f"Successfully read: {path}")
            
            return result
            
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
                self.report_error(f"File not found: {path}")
                return {
                    "success": False,
                    "error": f"File not found: {path}",
                    "path": path
                }
            self.report_error(f"Failed to read file: {error_msg}")
            return {
                "success": False,
                "error": f"Failed to read file: {error_msg}",
                "path": path
            }
