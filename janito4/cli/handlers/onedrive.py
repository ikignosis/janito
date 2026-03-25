"""
OneDrive authentication command handlers.
"""

import sys
import time

from ...secrets_config import get_secret


def handle_onedrive_auth():
    """Handle OneDrive device code authentication flow."""
    from ...tools.onedrive.device_code_auth import DeviceCodeAuth, store_token_data
    
    client_id = get_secret("azure_client_id")
    
    if not client_id:
        print("Error: azure_client_id not configured.", file=sys.stderr)
        print("\nPlease set your Azure client ID first:", file=sys.stderr)
        print("  janito4 --set-secret azure_client_id=your-client-id", file=sys.stderr)
        print("\nTo get a client ID:", file=sys.stderr)
        print("1. Go to https://portal.azure.com → Azure Active Directory → App registrations", file=sys.stderr)
        print("2. Click 'New registration'", file=sys.stderr)
        print("3. Enter name: 'Janito4 OneDrive'", file=sys.stderr)
        print("4. For personal accounts: Select 'Accounts in any personal Microsoft account'", file=sys.stderr)
        print("5. Click 'Register'", file=sys.stderr)
        print("6. Copy the 'Application (client) ID'", file=sys.stderr)
        return 1
    
    print("\n" + "=" * 60)
    print("  MICROSOFT ONEDRIVE AUTHENTICATION")
    print("=" * 60 + "\n")
    
    try:
        # Get device code
        auth = DeviceCodeAuth(client_id)
        user_code, verification_url = auth.get_device_code()
        
        print(f"  Step 1: Open this URL in your browser:")
        print(f"     {verification_url}")
        print(f"\n  Step 2: Enter this code:")
        print(f"     {user_code}")
        print(f"\n  Step 3: Sign in with your Microsoft account")
        print(f"  Step 4: Click 'Continue' to grant permissions")
        print("\n  Waiting for authentication...")
        
        # Poll for token
        token_data = auth.poll_for_token()
        
        # Store tokens
        store_token_data(token_data)
        
        print("\n  [OK] Authentication successful!")
        print("\nYour tokens have been saved and will be automatically refreshed.")
        print("\nYou can now use OneDrive tools:")
        print("  janito4 --onedrive \"List my files\"")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\nAuthentication cancelled.")
        return 130
    except Exception as e:
        print(f"\n\n[ERROR] Authentication failed: {e}", file=sys.stderr)
        return 1


def handle_onedrive_logout():
    """Handle OneDrive logout - clear authentication tokens."""
    from ...tools.onedrive.device_code_auth import clear_tokens
    
    print("Clearing OneDrive authentication tokens...")
    clear_tokens()
    print("[OK] Logged out successfully.")
    print("\nTo log in again, run:")
    print("  janito4 --onedrive-auth")
    return 0


def handle_onedrive_status():
    """Handle OneDrive status check - show authentication status."""
    client_id = get_secret("azure_client_id")
    access_token = get_secret("azure_access_token")
    refresh_token = get_secret("azure_refresh_token")
    
    print("OneDrive Authentication Status")
    print("=" * 40)
    
    if not client_id:
        print("Client ID: Not configured")
        print("\nSet your client ID with:")
        print("  janito4 --set-secret azure_client_id=your-client-id")
        return 1
    
    print(f"Client ID: {client_id[:8]}...{client_id[-8:]}")
    
    if access_token and refresh_token:
        expires_at_str = get_secret("azure_token_expires_at")
        if expires_at_str:
            expires_at = float(expires_at_str)
            remaining = expires_at - time.time()
            if remaining > 0:
                print(f"Access Token: [OK] Valid (expires in {int(remaining)}s)")
            else:
                print("Access Token: [EXPIRED] Will refresh automatically")
        else:
            print("Access Token: [OK] Stored")
        print("Refresh Token: [OK] Stored")
        print("\n[OK] Authenticated and ready to use!")
    else:
        print("Access Token: [MISSING] Not found")
        print("Refresh Token: [MISSING] Not found")
        print("\nRun authentication with:")
        print("  janito4 --onedrive-auth")
        return 1
    
    return 0
