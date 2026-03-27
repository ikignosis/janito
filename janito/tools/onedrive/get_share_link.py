#!/usr/bin/env python3
"""
Get OneDrive Share Link Tool - A class-based tool for creating share links in OneDrive.

This tool uses Microsoft Graph API to create share links for files and folders in OneDrive.
"""

from typing import Dict, Any, Optional
from ...tooling import BaseTool
from ..decorator import tool


@tool(permissions="r")
class GetOneDriveShareLink(BaseTool):
    """
    Tool for creating share links for OneDrive files and folders.
    
    Creates anonymous or organization-only sharing links.
    
    Required Secrets:
        - azure_client_id: Your Azure AD application client ID
        - azure_access_token: (auto-managed) Current access token
        - azure_refresh_token: (auto-managed) Refresh token
    
    Graph API Reference:
        https://docs.microsoft.com/en-us/graph/api/driveitem-createlink
    """
    
    def run(
        self,
        path: str,
        link_type: str = "view",
        scope: str = "anonymous"
    ) -> Dict[str, Any]:
        """
        Create a sharing link for a file or folder.
        
        Args:
            path (str): Full path to the file or folder (e.g., "Documents/report.pdf")
            link_type (str): Type of link - "view" (read-only) or "edit" (read-write) (default: "view")
            scope (str): Who can access - "anonymous" (anyone with link) or "organization" (same tenant) (default: "anonymous")
        
        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if operation succeeded
                - 'path': the item path
                - 'share_link': the generated share URL
                - 'link_type': type of link created
                - 'scope': scope of the link
                - 'expiration': expiration datetime if set (None for anonymous links)
                - 'error': error message if operation failed (only present if success=False)
        """
        try:
            from .base_client import OneDriveBaseClient
            
            self.report_start(f"Creating share link for: {path}")
            
            # Validate link_type
            if link_type not in ("view", "edit"):
                self.report_error("link_type must be 'view' or 'edit'")
                return {
                    "success": False,
                    "error": "link_type must be 'view' or 'edit'",
                    "path": path
                }
            
            # Validate scope
            if scope not in ("anonymous", "organization"):
                self.report_error("scope must be 'anonymous' or 'organization'")
                return {
                    "success": False,
                    "error": "scope must be 'anonymous' or 'organization'",
                    "path": path
                }
            
            client = OneDriveBaseClient()
            
            # Build the endpoint
            encoded_path = path.replace(" ", "%20").lstrip("/")
            endpoint = f"/me/drive/root:/{encoded_path}:/createLink"
            
            # Build the request body
            request_body = {
                "type": link_type,
                "scope": scope
            }
            
            self.report_progress(f" Creating {link_type} link with {scope} scope...")
            
            response = client._make_request(
                method="POST",
                endpoint=endpoint,
                json_data=request_body,
                timeout=30
            )
            
            # Extract share link info
            share_link = response.get("link", {})
            
            result = {
                "success": True,
                "path": path,
                "share_link": share_link.get("webUrl"),
                "link_type": link_type,
                "scope": scope,
                "expiration": share_link.get("expirationDateTime")
            }
            
            if share_link.get("type"):
                result["link_kind"] = share_link.get("type")
            
            self.report_result(f"Share link created: {result['share_link']}")
            
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
                self.report_error(f"Item not found: {path}")
                return {
                    "success": False,
                    "error": f"Item not found: {path}",
                    "path": path
                }
            self.report_error(f"Failed to create share link: {error_msg}")
            return {
                "success": False,
                "error": f"Failed to create share link: {error_msg}",
                "path": path
            }
