"""
OneDrive tools package for interacting with Microsoft OneDrive via Microsoft Graph API.

This package provides tools for listing, reading, downloading, uploading, deleting,
and searching files in OneDrive using device code flow authentication.

Authentication:
    Device code flow supports both personal Microsoft accounts and work/school accounts.
    
    1. First configure your client ID:
       janito4 --set-secret azure_client_id=your-client-id
       
    2. Authenticate (one-time only):
       janito4 --onedrive-auth
       
    3. Use the tools:
       janito4 --onedrive "List my files"

CLI Usage:
    python -m janito4.tools.onedrive list-files [options]
    python -m janito4.tools.onedrive read-file [options]
    python -m janito4.tools.onedrive search-files [options]
    python -m janito4.tools.onedrive authenticate

For AI function calling, use through the tool registry.

Required Secrets:
    - azure_client_id: Your Azure AD application (client) ID

Auto-managed Secrets (created during authentication):
    - azure_access_token: Current access token
    - azure_refresh_token: Refresh token for long-lived sessions
    - azure_token_expires_at: Token expiration timestamp

Usage:
    janito4 --set-secret azure_client_id=your-client-id
    janito4 --onedrive-auth
"""

from .list_files import ListOneDriveFiles
from .read_file import ReadOneDriveFile
from .download_file import DownloadOneDriveFile
from .upload_file import UploadOneDriveFile
from .delete_file import DeleteOneDriveFile
from .create_folder import CreateOneDriveFolder
from .search_files import SearchOneDriveFiles
from .get_share_link import GetOneDriveShareLink

__all__ = [
    "ListOneDriveFiles",
    "ReadOneDriveFile",
    "DownloadOneDriveFile",
    "UploadOneDriveFile",
    "DeleteOneDriveFile",
    "CreateOneDriveFolder",
    "SearchOneDriveFiles",
    "GetOneDriveShareLink",
]
