#!/usr/bin/env python3
"""
Base OneDrive Client - Authentication and base functionality for Microsoft Graph API.

This module provides the base client class for OneDrive operations using
Microsoft Graph API with device code flow authentication.

Supports both personal Microsoft accounts and work/school accounts.
"""

import json
import re
import requests
from typing import Dict, Any, Optional

from .device_code_auth import (
    DeviceCodeAuth,
    store_token_data,
    get_stored_token,
    clear_tokens
)


class OneDriveBaseClient:
    """
    Base client for OneDrive operations via Microsoft Graph API.
    
    Uses Microsoft identity platform device code flow for authentication.
    
    Authentication:
        1. First time: Run `janito --onedrive-auth` to authenticate
        2. The tool will display a code and URL
        3. Visit the URL, enter the code, and sign in
        4. Tokens are stored and automatically refreshed
    
    Required Secrets:
        - azure_client_id: Azure AD application client ID
        - azure_access_token: (auto-stored) Current access token
        - azure_refresh_token: (auto-stored) Refresh token
        - azure_token_expires_at: (auto-stored) Token expiration timestamp
    
    API documentation: https://docs.microsoft.com/en-us/graph/api/overview
    """
    
    GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
    
    def __init__(self, user_id: Optional[str] = None):
        """
        Initialize the OneDrive client.
        
        Args:
            user_id: Optional user identifier (for future multi-user support).
                    Currently only single-user mode is supported.
        """
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[float] = None
    
    def _get_required_secrets(self) -> str:
        """
        Get the required Azure client ID.
        
        Returns:
            str: The Azure AD client ID
            
        Raises:
            ValueError: If required secrets are not configured
        """
        from ...secrets_config import get_secret
        
        client_id = get_secret("azure_client_id")
        
        if not client_id:
            raise ValueError(
                "Secret 'azure_client_id' not configured. "
                "You need to register an app in Azure AD first.\n\n"
                "Setup instructions:\n"
                "1. Go to https://portal.azure.com → Azure Active Directory → App registrations\n"
                "2. Click 'New registration'\n"
                "3. Set name: 'janito OneDrive'\n"
                "4. Set 'Accounts in any organizational directory' (for work accounts)\n"
                "   Or 'Accounts in any personal Microsoft account' (for personal accounts)\n"
                "5. Click 'Register'\n"
                "6. Copy the 'Application (client) ID'\n"
                "7. Run: janito --set-secret azure_client_id=your-client-id\n"
                "8. Run: janito --onedrive-auth\n"
            )
        
        return client_id
    
    def _ensure_authenticated(self) -> None:
        """
        Ensure we have a valid access token.
        
        Checks for stored token and refreshes if needed.
        Raises ValueError if no credentials configured.
        """
        from ...secrets_config import get_secret
        
        # Check for existing valid token
        token_data = get_stored_token()
        
        if token_data:
            self._access_token = token_data["access_token"]
            self._token_expires_at = token_data["expires_at"]
            return
        
        # Try to refresh if we have a refresh token
        refresh_token = get_secret("azure_refresh_token")
        client_id = get_secret("azure_client_id")
        
        if refresh_token and client_id:
            print(" Access token expired, refreshing...", file=__import__('sys').stderr, flush=True)
            
            auth = DeviceCodeAuth(client_id)
            new_token_data = auth.refresh_access_token(refresh_token)
            store_token_data(new_token_data)
            
            self._access_token = new_token_data["access_token"]
            self._token_expires_at = new_token_data["expires_at"]
            return
        
        # No token available
        raise ValueError(
            "Not authenticated. Please run:\n"
            "  janito --onedrive-auth\n"
            "to authenticate with your Microsoft account."
        )
    
    def _get_access_token(self) -> str:
        """
        Get a valid access token.
        
        Returns:
            str: The access token
            
        Raises:
            ValueError: If not authenticated
        """
        import time
        
        # Check if we have a valid cached token
        if self._access_token and self._token_expires_at:
            if time.time() < self._token_expires_at - 60:  # 60 second buffer
                return self._access_token
        
        # Need to refresh
        self._ensure_authenticated()
        
        return self._access_token
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Make an authenticated request to Microsoft Graph API.
        
        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            endpoint: API endpoint (e.g., "/me/drive/root/children")
            params: Query parameters
            json_data: JSON body for POST/PUT/PATCH requests
            headers: Additional headers
            timeout: Request timeout in seconds
            
        Returns:
            Dict: API response JSON
            
        Raises:
            Exception: If the request fails
        """
        import time
        
        access_token = self._get_access_token()
        
        url = f"{self.GRAPH_BASE_URL}{endpoint}"
        
        request_headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        if headers:
            request_headers.update(headers)
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    headers=request_headers,
                    timeout=timeout
                )
                
                # Handle token expiration
                if response.status_code == 401:
                    # Token might be expired, try to refresh
                    from ...secrets_config import get_secret
                    refresh_token = get_secret("azure_refresh_token")
                    client_id = get_secret("azure_client_id")
                    
                    if refresh_token and client_id and retry_count < max_retries - 1:
                        print(" Access token expired, refreshing...", file=__import__('sys').stderr, flush=True)
                        
                        auth = DeviceCodeAuth(client_id)
                        new_token_data = auth.refresh_access_token(refresh_token)
                        store_token_data(new_token_data)
                        
                        self._access_token = new_token_data["access_token"]
                        self._token_expires_at = new_token_data["expires_at"]
                        request_headers["Authorization"] = f"Bearer {self._access_token}"
                        retry_count += 1
                        continue
                    else:
                        # No refresh token or failed, need re-auth
                        raise Exception(
                            "Authentication expired. Please run:\n"
                            "  janito --onedrive-auth"
                        )
                
                # Check for other errors
                if response.status_code >= 400:
                    try:
                        error_data = response.json()
                        error_message = error_data.get("error", {}).get("message", response.text)
                    except json.JSONDecodeError:
                        error_message = response.text
                    
                    raise Exception(
                        f"Graph API error (status {response.status_code}): {error_message}"
                    )
                
                # Return JSON for successful responses
                if response.text:
                    return response.json()
                return {}
                
            except requests.exceptions.Timeout:
                retry_count += 1
                if retry_count >= max_retries:
                    raise Exception(f"Request timed out after {max_retries} attempts")
                print(f" Request timed out, retrying ({retry_count}/{max_retries})...", file=__import__('sys').stderr, flush=True)
                time.sleep(1)
                
            except requests.exceptions.RequestException as e:
                raise Exception(f"Request failed: {str(e)}")
        
        raise Exception("Max retries exceeded")
    
    def _get_drive_endpoint(self, path: str = "") -> str:
        """
        Get a drive item endpoint for the specified path.
        
        Uses /me/drive/... because device code flow authenticates as a specific user.
        
        Args:
            path: The path to the item (e.g., "Documents/file.txt")
            
        Returns:
            str: The API endpoint path for the item (not children)
        """
        path = path.lstrip("/")
        
        if not path:
            return "/me/drive/root"
        
        return f"/me/drive/root:/{path}"
    
    def _get_drive_children_endpoint(self, path: str = "") -> str:
        """
        Get a drive children endpoint for listing children.
        
        Args:
            path: The folder path (e.g., "Documents" or "" for root)
            
        Returns:
            str: The API endpoint path for listing children
        """
        path = path.lstrip("/")
        
        if not path:
            return "/me/drive/root/children"
        
        return f"/me/drive/root:/{path}:/children"
    
    def _get_drive_path(self, path: str) -> str:
        """
        Convert a path to the Graph API endpoint format.
        
        Args:
            path: The path (e.g., "/Documents/file.txt" or "Documents/file.txt")
            
        Returns:
            str: The API endpoint path
        """
        path = path.lstrip("/")
        
        if not path:
            return "/me/drive/root/children"
        
        return f"/me/drive/root:/{path}:/children"
    
    def _format_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format a drive item for cleaner output.
        
        Args:
            item: The raw item from Graph API
            
        Returns:
            Dict: Formatted item
        """
        formatted = {
            "id": item.get("id"),
            "name": item.get("name"),
            "type": "folder" if item.get("folder") else "file",
            "created_date_time": item.get("createdDateTime"),
            "last_modified_date_time": item.get("lastModifiedDateTime"),
            "web_url": item.get("webUrl"),
            "size": item.get("size"),
        }
        
        # Add parent reference
        if "parentReference" in item:
            parent = item["parentReference"]
            parent_path = parent.get("path", "")
            # Handle both /me/drive/root: and /users/{userId}/drive/root: formats
            parent_path = parent_path.replace("/me/drive/root:", "")
            parent_path = re.sub(r"^/users/[^/]+/drive/root:", "", parent_path)
            formatted["parent_path"] = parent_path
            formatted["parent_id"] = parent.get("id")
        
        # Add file-specific info
        if "file" in item:
            formatted["mime_type"] = item.get("file", {}).get("mimeType")
        
        # Add folder-specific info
        if "folder" in item:
            formatted["child_count"] = item.get("folder", {}).get("childCount")
        
        return formatted
