#!/usr/bin/env python3
"""
Upload OneDrive File Tool - A class-based tool for uploading files to OneDrive.

This tool uses Microsoft Graph API to upload file content to OneDrive.
"""

import os
from typing import Dict, Any, Optional
from ...tooling import BaseTool
from ..decorator import tool


@tool(permissions="w")
class UploadOneDriveFile(BaseTool):
    """
    Tool for uploading files to OneDrive.
    
    Creates or updates files in OneDrive. For large files (>4MB), uses
    resumable upload sessions.
    
    Required Secrets:
        - azure_client_id: Your Azure AD application client ID
        - azure_access_token: (auto-managed) Current access token
        - azure_refresh_token: (auto-managed) Refresh token
    
    Graph API Reference:
        https://docs.microsoft.com/en-us/graph/api/driveitem-put-content
    """
    
    # Threshold for using resumable upload (4MB)
    LARGE_FILE_THRESHOLD = 4 * 1024 * 1024
    
    def run(
        self,
        path: str,
        content: Optional[str] = None,
        local_path: Optional[str] = None,
        overwrite: bool = True
    ) -> Dict[str, Any]:
        """
        Upload a file to OneDrive.
        
        Provide either content (text) or local_path (file path to upload).
        
        Args:
            path (str): Full path where file will be saved (e.g., "Documents/report.txt")
            content (Optional[str]): Text content to upload
            local_path (Optional[str]): Local file path to upload (alternative to content)
            overwrite (bool): If True, overwrite existing file (default: True)
        
        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if operation succeeded
                - 'path': the OneDrive file path
                - 'file': uploaded file metadata
                - 'error': error message if operation failed (only present if success=False)
        """
        try:
            from .base_client import OneDriveBaseClient
            
            self.report_start(f"Uploading file to: {path}")
            
            # Validate input
            if not content and not local_path:
                self.report_error("Must provide either content or local_path")
                return {
                    "success": False,
                    "error": "Must provide either 'content' (text) or 'local_path' (file path)",
                    "path": path
                }
            
            if content and local_path:
                self.report_error("Cannot provide both content and local_path")
                return {
                    "success": False,
                    "error": "Provide either 'content' or 'local_path', not both",
                    "path": path
                }
            
            # Read content from local file if provided
            if local_path:
                if not os.path.exists(local_path):
                    self.report_error(f"Local file not found: {local_path}")
                    return {
                        "success": False,
                        "error": f"Local file not found: {local_path}",
                        "path": path
                    }
                
                with open(local_path, "rb") as f:
                    file_bytes = f.read()
                    file_name = os.path.basename(local_path)
                
                # Use file name from local path if path is just a folder
                if path.endswith("/") or not path:
                    path = path + file_name
            else:
                # Convert text content to bytes
                file_bytes = content.encode("utf-8")
            
            client = OneDriveBaseClient()
            
            # Build the endpoint
            encoded_path = path.replace(" ", "%20").lstrip("/")
            endpoint = f"/me/drive/root:/{encoded_path}:/content"
            
            file_size = len(file_bytes)
            self.report_progress(f" Uploading {file_size} bytes...")
            
            # Choose upload method based on file size
            if file_size > self.LARGE_FILE_THRESHOLD:
                result = self._upload_large_file(client, endpoint, file_bytes, overwrite)
            else:
                result = self._upload_simple(client, endpoint, file_bytes, overwrite)
            
            if result.get("success"):
                self.report_result(f"Successfully uploaded: {path}")
            else:
                self.report_error(result.get("error", "Upload failed"))
            
            return result
            
        except ValueError as e:
            self.report_error(str(e))
            return {
                "success": False,
                "error": str(e),
                "path": path
            }
        except Exception as e:
            self.report_error(f"Failed to upload file: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to upload file: {str(e)}",
                "path": path
            }
    
    def _upload_simple(
        self,
        client: "OneDriveBaseClient",
        endpoint: str,
        content: bytes,
        overwrite: bool
    ) -> Dict[str, Any]:
        """Simple upload for files under 4MB."""
        import requests
        
        access_token = client._get_access_token()
        url = f"{client.GRAPH_BASE_URL}{endpoint}"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/octet-stream"
        }
        
        if overwrite:
            headers["If-Match"] = "*"
        
        response = requests.put(
            url,
            headers=headers,
            data=content,
            timeout=60
        )
        
        if response.status_code >= 400:
            try:
                error_data = response.json()
                error_message = error_data.get("error", {}).get("message", response.text)
            except:
                error_message = response.text
            return {
                "success": False,
                "error": f"Upload failed: {error_message}"
            }
        
        result = response.json()
        
        return {
            "success": True,
            "file": {
                "id": result.get("id"),
                "name": result.get("name"),
                "size": result.get("size"),
                "web_url": result.get("webUrl"),
                "created": result.get("createdDateTime"),
                "modified": result.get("lastModifiedDateTime")
            }
        }
    
    def _upload_large_file(
        self,
        client: "OneDriveBaseClient",
        endpoint: str,
        content: bytes,
        overwrite: bool
    ) -> Dict[str, Any]:
        """Resumable upload for large files using upload session."""
        import requests
        
        access_token = client._get_access_token()
        base_url = client.GRAPH_BASE_URL
        
        # Create upload session
        session_url = f"{base_url}{endpoint}"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        session_response = requests.post(
            session_url,
            headers=headers,
            json={"item": {"@microsoft.graph.conflictBehavior": "replace" if overwrite else "fail"}},
            timeout=30
        )
        
        if session_response.status_code != 200:
            try:
                error_data = session_response.json()
                error_message = error_data.get("error", {}).get("message", session_response.text)
            except:
                error_message = session_response.text
            return {
                "success": False,
                "error": f"Failed to create upload session: {error_message}"
            }
        
        session_data = session_response.json()
        upload_url = session_data.get("uploadUrl")
        
        if not upload_url:
            return {
                "success": False,
                "error": "Invalid upload session response"
            }
        
        # Upload in chunks (minimum 5MB chunks except final)
        chunk_size = 5 * 1024 * 1024  # 5MB
        total_size = len(content)
        
        offset = 0
        chunk_num = 0
        
        while offset < total_size:
            chunk_num += 1
            chunk_end = min(offset + chunk_size, total_size)
            chunk = content[offset:chunk_end]
            
            is_last = chunk_end == total_size
            
            chunk_headers = {
                "Content-Length": str(len(chunk)),
                "Content-Range": f"bytes {offset}-{chunk_end - 1}/{total_size}"
            }
            
            self.report_progress(f" Uploading chunk {chunk_num} ({len(chunk)} bytes)...")
            
            chunk_response = requests.put(
                upload_url,
                headers=chunk_headers,
                data=chunk,
                timeout=120
            )
            
            if chunk_response.status_code not in (200, 201, 202):
                try:
                    error_data = chunk_response.json()
                    error_message = error_data.get("error", {}).get("message", chunk_response.text)
                except:
                    error_message = chunk_response.text
                return {
                    "success": False,
                    "error": f"Chunk upload failed: {error_message}"
                }
            
            offset = chunk_end
        
        result = chunk_response.json() if chunk_response.text else {}
        
        return {
            "success": True,
            "file": {
                "id": result.get("id"),
                "name": result.get("name"),
                "size": result.get("size"),
                "web_url": result.get("webUrl")
            }
        }
