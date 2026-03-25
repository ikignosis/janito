#!/usr/bin/env python3
"""
CLI entry point for OneDrive tools.

This module provides the command-line interface for the OneDrive tools package.
Run with: python -m janito4.tools.onedrive [command] [options]

Examples:
    python -m janito4.tools.onedrive list-files
    python -m janito4.tools.onedrive list-files --path Documents
    python -m janito4.tools.onedrive search-files --query report
    python -m janito4.tools.onedrive read-file --path "Documents/readme.txt"
    python -m janito4.tools.onedrive authenticate
"""

import argparse
import json
import sys

from .list_files import ListOneDriveFiles
from .search_files import SearchOneDriveFiles
from .read_file import ReadOneDriveFile
from .device_code_auth import DeviceCodeAuth, store_token_data, get_stored_token, clear_tokens


def authenticate_command(args) -> int:
    """
    Handle the authenticate command.
    
    Performs device code flow authentication.
    """
    from ...secrets_config import get_secret, set_secret
    
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
        print("5. For work accounts: Select 'Accounts in any organizational directory'", file=sys.stderr)
        print("6. Click 'Register'", file=sys.stderr)
        print("7. Copy the 'Application (client) ID'", file=sys.stderr)
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
        
        print("\n  ✓ Authentication successful!")
        print("\nYour tokens have been saved and will be automatically refreshed.")
        print("\nYou can now use OneDrive tools:")
        print("  janito4 --onedrive \"List my files\"")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\nAuthentication cancelled.")
        return 130
    except Exception as e:
        print(f"\n\n✗ Authentication failed: {e}", file=sys.stderr)
        return 1


def logout_command(args) -> int:
    """
    Handle the logout command.
    
    Clears stored tokens.
    """
    print("Clearing authentication tokens...")
    clear_tokens()
    print("✓ Logged out successfully.")
    print("\nTo log in again, run:")
    print("  janito4 --onedrive-auth")
    return 0


def status_command(args) -> int:
    """
    Handle the status command.
    
    Shows current authentication status.
    """
    from ...secrets_config import get_secret
    
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
            import time
            expires_at = float(expires_at_str)
            remaining = expires_at - time.time()
            if remaining > 0:
                print(f"Access Token: ✓ Valid (expires in {int(remaining)}s)")
            else:
                print("Access Token: ✗ Expired (will refresh automatically)")
        else:
            print("Access Token: ✓ Stored")
        print("Refresh Token: ✓ Stored")
        print("\n✓ Authenticated and ready to use!")
    else:
        print("Access Token: ✗ Not found")
        print("Refresh Token: ✗ Not found")
        print("\nRun authentication with:")
        print("  janito4 --onedrive-auth")
        return 1
    
    return 0


def main():
    """Command line interface for OneDrive tools."""
    parser = argparse.ArgumentParser(
        description="OneDrive tools for Microsoft Graph API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m janito4.tools.onedrive list-files
  python -m janito4.tools.onedrive list-files --path Documents
  python -m janito4.tools.onedrive search-files --query report
  python -m janito4.tools.onedrive read-file --path "Documents/readme.txt"
  python -m janito4.tools.onedrive authenticate
  python -m janito4.tools.onedrive status

Required secret:
  janito4 --set-secret azure_client_id=your-client-id
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Authenticate subcommand
    auth_parser = subparsers.add_parser(
        "authenticate",
        help="Authenticate with Microsoft account",
        description="Authenticate using device code flow"
    )
    
    # Logout subcommand
    logout_parser = subparsers.add_parser(
        "logout",
        help="Clear authentication tokens",
        description="Clear stored tokens and log out"
    )
    
    # Status subcommand
    status_parser = subparsers.add_parser(
        "status",
        help="Show authentication status",
        description="Check if authenticated"
    )
    
    # List files subcommand
    list_parser = subparsers.add_parser(
        "list-files",
        help="List files and folders",
        description="List files and folders in OneDrive"
    )
    list_parser.add_argument(
        "--path", "-p",
        default="",
        help="Folder path to list (default: root)"
    )
    list_parser.add_argument(
        "--limit", "-l",
        type=int,
        default=50,
        help="Maximum items to return (default: 50)"
    )
    list_parser.add_argument(
        "--order-by", "-o",
        default="name",
        choices=["name", "name desc", "lastModifiedDateTime", "lastModifiedDateTime desc", "size", "size desc"],
        help="Sort order (default: name)"
    )
    list_parser.add_argument(
        "--folders-only", "-f",
        action="store_true",
        help="List only folders"
    )
    list_parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output in JSON format"
    )
    
    # Search files subcommand
    search_parser = subparsers.add_parser(
        "search-files",
        help="Search for files",
        description="Search for files in OneDrive"
    )
    search_parser.add_argument(
        "query",
        help="Search query"
    )
    search_parser.add_argument(
        "--folder", "-f",
        help="Limit search to specific folder"
    )
    search_parser.add_argument(
        "--type", "-t",
        help="Filter by file extension (e.g., docx, pdf)"
    )
    search_parser.add_argument(
        "--limit", "-l",
        type=int,
        default=20,
        help="Maximum results (default: 20)"
    )
    search_parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output in JSON format"
    )
    
    # Read file subcommand
    read_parser = subparsers.add_parser(
        "read-file",
        help="Read file metadata",
        description="Read file metadata from OneDrive"
    )
    read_parser.add_argument(
        "path",
        help="File path"
    )
    read_parser.add_argument(
        "--content", "-c",
        action="store_true",
        help="Include text content (for text files)"
    )
    read_parser.add_argument(
        "--max-content", "-m",
        type=int,
        default=10000,
        help="Maximum content length (default: 10000)"
    )
    read_parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output in JSON format"
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Handle special commands
    if args.command == "authenticate":
        return authenticate_command(args)
    elif args.command == "logout":
        return logout_command(args)
    elif args.command == "status":
        return status_command(args)
    
    output_json = getattr(args, 'json', False)
    
    try:
        if args.command == "list-files":
            tool = ListOneDriveFiles()
            result = tool.run(
                path=args.path,
                limit=args.limit,
                order_by=args.order_by,
                folder_only=args.folders_only
            )
            
        elif args.command == "search-files":
            tool = SearchOneDriveFiles()
            result = tool.run(
                query=args.query,
                folder_path=args.folder,
                file_type_filter=args.type,
                limit=args.limit
            )
            
        elif args.command == "read-file":
            tool = ReadOneDriveFile()
            result = tool.run(
                path=args.path,
                include_content=args.content,
                max_content_length=args.max_content
            )
        
        else:
            parser.print_help()
            return 1
        
        # Output result
        if output_json:
            print(json.dumps(result, indent=2, default=str, ensure_ascii=False))
        else:
            if result["success"]:
                if args.command == "list-files":
                    print(f"\u2713 Found {result['total_count']} items in {result['path']}")
                    print()
                    for item in result.get("items", []):
                        item_type = "\U0001F4C1" if item["type"] == "folder" else "\U0001F4C4"
                        size_str = f" ({_format_size(item.get('size'))})" if item.get('size') else ""
                        print(f"  {item_type} {item['name']}{size_str}")
                        
                elif args.command == "search-files":
                    print(f"\u2713 Found {result['total_count']} matches for '{result['query']}'")
                    print()
                    for item in result.get("items", []):
                        item_type = "\U0001F4C1" if item["type"] == "folder" else "\U0001F4C4"
                        path_str = f" in {item.get('parent_path', '/')}" if item.get('parent_path') else ""
                        print(f"  {item_type} {item['name']}{path_str}")
                        
                elif args.command == "read-file":
                    print(f"\u2713 File: {result['path']}")
                    print(f"  ID: {result['file']['id']}")
                    print(f"  Size: {_format_size(result['file'].get('size'))}")
                    print(f"  Modified: {result['file'].get('modified')}")
                    print(f"  URL: {result['file'].get('web_url')}")
                    if result.get('content'):
                        print()
                        print("Content:")
                        print("-" * 40)
                        print(result['content'])
            else:
                print(f"\u2717 Error: {result.get('error', 'Unknown error')}")
        
        return 0 if result["success"] else 1
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return 130
    except Exception as e:
        if output_json:
            print(json.dumps({"success": False, "error": str(e)}, indent=2))
        else:
            print(f"\u2717 Error: {str(e)}", file=sys.stderr)
        return 1


def _format_size(size_bytes: int) -> str:
    """Format byte size to human-readable string."""
    if size_bytes is None:
        return "Unknown"
    
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


if __name__ == "__main__":
    sys.exit(main())
