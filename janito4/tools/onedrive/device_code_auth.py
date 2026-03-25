#!/usr/bin/env python3
"""
Device Code Authentication for Microsoft Graph API.

This module provides device code flow authentication for personal Microsoft
accounts and work/school accounts. This is the recommended auth method for
non-interactive scenarios.
"""

import json
import time
import requests
from typing import Dict, Tuple, Optional

try:
    from ...secrets_config import (
        set_secret as _set_secret,
        get_secret as _get_secret,
        delete_secret as _delete_secret
    )
except ImportError:
    from janito4.secrets_config import (
        set_secret as _set_secret,
        get_secret as _get_secret,
        delete_secret as _delete_secret
    )


# Microsoft identity platform endpoints for personal Microsoft accounts
AUTH_URL = "https://login.microsoftonline.com/consumers/oauth2/v2.0/devicecode"
TOKEN_URL = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"

# Redirect URI for device code flow (public client)
# Using the standard Microsoft redirect for native/desktop applications
REDIRECT_URI = "https://login.microsoftonline.com/common/oauth2/nativeclient"

# Scopes for OneDrive access
SCOPES = [
    "https://graph.microsoft.com/Files.ReadWrite.All",
    "offline_access"  # Required for refresh tokens
]


class DeviceCodeAuth:
    """
    Handles device code flow authentication for Microsoft Graph API.
    
    This auth method:
    - Works with personal Microsoft accounts (outlook.com, live.com, etc.)
    - Works with work/school Azure AD accounts
    - Requires one-time interactive user consent
    - Provides refresh tokens for long-running automation
    
    Usage:
        auth = DeviceCodeAuth(client_id)
        
        # First time: get device code and user code
        user_code, verification_url = auth.get_device_code()
        print(f"Visit {verification_url} and enter code: {user_code}")
        
        # Poll for token (user enters code in browser)
        token_data = auth.poll_for_token()
        
        # Subsequent runs: use cached refresh token
        token_data = auth.refresh_access_token()
    """
    
    def __init__(self, client_id: str):
        """
        Initialize device code auth.
        
        Args:
            client_id: Azure AD application client ID
        """
        self.client_id = client_id
    
    def get_device_code(self) -> Tuple[str, str]:
        """
        Get device code and verification URL.
        
        Returns the device code that the user must enter at the verification URL.
        This is shown to the user once at the start.
        
        Returns:
            Tuple[str, str]: (user_code, verification_url)
            
        Raises:
            Exception: If the request fails
        """
        data = {
            "client_id": self.client_id,
            "scope": " ".join(SCOPES)
        }
        
        print(" Requesting device code from Microsoft...", file=__import__('sys').stderr, flush=True)
        
        response = requests.post(AUTH_URL, data=data, timeout=30)
        
        if response.status_code != 200:
            error_info = response.json() if response.text else {}
            error_description = error_info.get("error_description", response.text)
            raise Exception(f"Failed to get device code: {error_description}")
        
        result = response.json()
        
        user_code = result.get("user_code")
        # Microsoft uses "verification_uri" not "verification_url"
        verification_url = result.get("verification_url") or result.get("verification_uri")
        device_code = result.get("device_code")
        interval = result.get("interval", 5)
        expires_in = result.get("expires_in", 900)
        
        # Store for polling
        self._device_code = device_code
        self._poll_interval = interval
        self._poll_expires_at = time.time() + expires_in
        
        return user_code, verification_url
    
    def poll_for_token(self, print_status: bool = True) -> Dict:
        """
        Poll for token after user enters code in browser.
        
        Continues polling until user completes authentication or timeout.
        
        Args:
            print_status: Whether to print status messages
            
        Returns:
            Dict containing:
                - access_token: Bearer token for API calls
                - refresh_token: Token for refreshing access
                - expires_in: Seconds until access token expires
                - expires_at: Unix timestamp when access token expires
                
        Raises:
            Exception: If polling fails or times out
        """
        if not hasattr(self, "_device_code"):
            raise Exception("Must call get_device_code() before poll_for_token()")
        
        data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "client_id": self.client_id,
            "device_code": self._device_code,
            "redirect_uri": REDIRECT_URI,
            "scope": " ".join(SCOPES)
        }
        
        if print_status:
            print(" Waiting for authentication...", file=__import__('sys').stderr, flush=True)
        
        while time.time() < self._poll_expires_at:
            time.sleep(self._poll_interval)
            
            response = requests.post(
                TOKEN_URL,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30
            )
            result = response.json()
            
            if response.status_code == 200:
                # Success!
                expires_in = result.get("expires_in", 3600)
                expires_at = time.time() + expires_in
                
                return {
                    "access_token": result.get("access_token"),
                    "refresh_token": result.get("refresh_token"),
                    "token_type": result.get("token_type", "Bearer"),
                    "expires_in": expires_in,
                    "expires_at": expires_at,
                    "scope": result.get("scope", " ".join(SCOPES))
                }
            
            error = result.get("error", "")
            error_description = result.get("error_description", "")
            
            if error == "authorization_pending":
                if print_status:
                    print(".", end="", file=__import__('sys').stderr, flush=True)
                continue
            
            elif error == "authorization_declined":
                raise Exception("Authentication declined by user. Please run the auth command again.")
            
            elif error == "bad_verification_code":
                raise Exception("Invalid device code. Please run the auth command again.")
            
            elif error == "expired_token":
                raise Exception("Device code expired. Please run the auth command again.")
            
            else:
                raise Exception(f"Authentication failed: {error_description}")
        
        raise Exception("Authentication timed out. Please run the auth command again.")
    
    def refresh_access_token(self, refresh_token: str) -> Dict:
        """
        Refresh an expired access token using refresh token.
        
        Args:
            refresh_token: The refresh token from previous authentication
            
        Returns:
            Dict containing new token data
            
        Raises:
            Exception: If refresh fails
        """
        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "refresh_token": refresh_token,
            "redirect_uri": REDIRECT_URI,
            "scope": " ".join(SCOPES)
        }
        
        print(" Refreshing access token...", file=__import__('sys').stderr, flush=True)
        
        response = requests.post(
            TOKEN_URL,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30
        )
        
        if response.status_code != 200:
            error_info = response.json() if response.text else {}
            error_description = error_info.get("error_description", response.text)
            error = error_info.get("error", "unknown_error")
            
            if error in ("invalid_grant", "refresh_token_expired"):
                raise Exception(
                    "Refresh token expired or invalid. Please re-authenticate:\n"
                    "  janito4 --onedrive-auth"
                )
            
            raise Exception(f"Failed to refresh token: {error_description}")
        
        result = response.json()
        
        expires_in = result.get("expires_in", 3600)
        expires_at = time.time() + expires_in
        
        # Use the new refresh token if provided, otherwise keep the old one
        new_refresh_token = result.get("refresh_token") or refresh_token
        
        return {
            "access_token": result.get("access_token"),
            "refresh_token": new_refresh_token,
            "token_type": result.get("token_type", "Bearer"),
            "expires_in": expires_in,
            "expires_at": expires_at,
            "scope": result.get("scope", " ".join(SCOPES))
        }
    
    @staticmethod
    def authenticate(client_id: str) -> Dict:
        """
        Complete authentication flow (get code + poll + return tokens).
        
        This is a convenience method that handles the full flow:
        1. Get device code
        2. Display instructions to user
        3. Poll until authenticated
        4. Return token data
        
        Args:
            client_id: Azure AD application client ID
            
        Returns:
            Dict containing token data
        """
        auth = DeviceCodeAuth(client_id)
        
        # Step 1: Get device code
        user_code, verification_url = auth.get_device_code()
        
        print("\n" + "=" * 60, file=__import__('sys').stderr)
        print("  MICROSOFT ONEDRIVE AUTHENTICATION", file=__import__('sys').stderr)
        print("=" * 60, file=__import__('sys').stderr)
        print(f"\n  1. Open this URL in your browser:", file=__import__('sys').stderr)
        print(f"     {verification_url}", file=__import__('sys').stderr)
        print(f"\n  2. Enter this code:", file=__import__('sys').stderr)
        print(f"     {user_code}", file=__import__('sys').stderr)
        print(f"\n  3. Sign in with your Microsoft account", file=__import__('sys').stderr)
        print(f"  4. Click 'Continue' to grant permissions", file=__import__('sys').stderr)
        print("\n  Waiting for authentication...\n", file=__import__('sys').stderr)
        
        # Step 2: Poll for token
        token_data = auth.poll_for_token()
        
        print("\n  ✓ Authentication successful!", file=__import__('sys').stderr)
        
        return token_data


def store_token_data(token_data: Dict) -> None:
    """
    Store token data in secrets.
    
    Args:
        token_data: Dict from authenticate() or refresh_access_token()
    """
    _set_secret("azure_access_token", token_data["access_token"])
    _set_secret("azure_refresh_token", token_data["refresh_token"])
    _set_secret("azure_token_expires_at", str(token_data["expires_at"]))


def get_stored_token() -> Optional[Dict]:
    """
    Retrieve stored token data from secrets.
    
    Returns:
        Dict with token data or None if not stored/expired
    """
    access_token = _get_secret("azure_access_token")
    refresh_token = _get_secret("azure_refresh_token")
    expires_at_str = _get_secret("azure_token_expires_at")
    
    if not access_token or not refresh_token:
        return None
    
    if expires_at_str:
        expires_at = float(expires_at_str)
        # Check if token is still valid (with 60 second buffer)
        if time.time() < expires_at - 60:
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": expires_at
            }
    
    return None


def clear_tokens() -> None:
    """Clear all stored token data."""
    _delete_secret("azure_access_token")
    _delete_secret("azure_refresh_token")
    _delete_secret("azure_token_expires_at")
