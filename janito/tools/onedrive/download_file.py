#!/usr/bin/env python3
"""
Download OneDrive File Tool - A class-based tool for downloading files from OneDrive.

This tool uses Microsoft Graph API to download file content from OneDrive.
"""

import base64
import os
from typing import Dict, Any, Optional
from ...tooling import BaseTool
from ..decorator import tool


@tool(permissions="r")
class DownloadOneDriveFile(BaseTool):
    """
    Tool for downloading file content from OneDrive.
    
    Downloads file content as base64-encoded data.
    Use ReadOneDriveFile for text-based files that need to be previewed.
    
    Required Secrets:
        - azure_client_id: Your Azure AD application client ID
        - azure_access_token: (auto-managed) Current access token
        - azure_refresh_token: (auto-managed) Refresh token
    
    Graph API Reference:
        https://docs.microsoft.com/en-us/graph/api/driveitem-get-content
    """
    
    def run(
        self,
        path: str,
        output_path: Optional[str] = None,
        as_base64: bool = False
    ) -> Dict[str, Any]:
        """
        Download a file from OneDrive.
        
        Args:
            path (str): Full path to the file (e.g., "Documents/report.pdf")
            output_path (Optional[str]): Local path to save the file. 
                                        If not provided, returns base64 encoded content
            as_base64 (bool): If True and output_path not provided, return base64 content (default: False)
        
        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if operation succeeded
                - 'path': the OneDrive file path
                - 'local_path': local path where file was saved (if output_path was provided)
                - 'content': base64 encoded content (if as_base64=True or no output_path)
                - 'size': file size in bytes
                - 'error': error message if operation failed (only present if success=False)
        """
        try:
            from .base_client import OneDriveBaseClient
            
            self.report_start(f"Downloading file: {path}")
            
            client = OneDriveBaseClient()
            
            # Build the endpoint for downloading content
            encoded_path = path.replace(" ", "%20").lstrip("/")
            endpoint = f"/me/drive/root:/{encoded_path}:/content"
            
            self.report_progress(" Downloading from Microsoft Graph...")
            
            # Make request without automatic JSON parsing (binary content)
            access_token = client._get_access_token()
            url = f"{client.GRAPH_BASE_URL}{endpoint}"
            
            import requests
            
            response = requests.get(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=60
            )
            
            if response.status_code == 404:
                self.report_error(f"File not found: {path}")
                return {
                    "success": False,
                    "error": f"File not found: {path}",
                    "path": path
                }
            
            if response.status_code >= 400:
                try:
                    error_data = response.json()
                    error_message = error_data.get("error", {}).get("message", response.text)
                except:
                    error_message = response.text
                self.report_error(f"Download failed: {error_message}")
                return {
                    "success": False,
                    "error": f"Download failed: {error_message}",
                    "path": path
                }
            
            content = response.content
            file_size = len(content)
            
            self.report_progress(f" Downloaded {file_size} bytes")
            
            result = {
                "success": True,
                "path": path,
                "size": file_size
            }
            
            # Save to file or return content
            if output_path:
                # Ensure directory exists
                output_dir = os.path.dirname(output_path)
                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)
                
                with open(output_path, "wb") as f:
                    f.write(content)
                
                self.report_result(f"Saved to: {output_path}")
                result["local_path"] = output_path
                
            elif as_base64:
                # Return base64 encoded content
                b64_content = base64.b64encode(content).decode("utf-8")
                result["content"] = b64_content
                result["content_type"] = "base64"
                self.report_result(f"Returned base64 content ({file_size} bytes)")
            else:
                # Try to decode as text for small files
                try:
                    text_content = content.decode("utf-8")
                    if len(text_content) > 5000:
                        text_content = text_content[:5000] + f"\n... [truncated, total {len(text_content)} chars]"
                    result["content"] = text_content
                    result["content_type"] = "text"
                    self.report_result(f"Returned text content ({file_size} bytes)")
                except UnicodeDecodeError:
                    # Binary file - return base64
                    b64_content = base64.b64encode(content).decode("utf-8")
                    result["content"] = b64_content
                    result["content_type"] = "base64"
                    self.report_result(f"Binary file - returned base64 content ({file_size} bytes)")
            
            return result
            
        except ValueError as e:
            self.report_error(str(e))
            return {
                "success": False,
                "error": str(e),
                "path": path
            }
        except Exception as e:
            self.report_error(f"Failed to download file: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to download file: {str(e)}",
                "path": path
            }
