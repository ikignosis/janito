"""
OneDrive tools package for interacting with Microsoft OneDrive via Microsoft Graph API.

This package provides tools for listing, reading, downloading, uploading, deleting,
and searching files in OneDrive using device code flow authentication.

Authentication:
    Device code flow supports both personal Microsoft accounts and work/school accounts.

    1. First configure your client ID:
       janito --set-secret azure_client_id=your-client-id

    2. Authenticate (one-time only):
       janito --onedrive-auth

    3. Use the tools:
       janito --onedrive "List my files"

CLI Usage:
    python -m janito.tools.onedrive list-files [options]
    python -m janito.tools.onedrive read-file [options]
    python -m janito.tools.onedrive search-files [options]
    python -m janito.tools.onedrive authenticate

For AI function calling, use through the tool registry.

Required Secrets:
    - azure_client_id: Your Azure AD application (client) ID

Auto-managed Secrets (created during authentication):
    - azure_access_token: Current access token
    - azure_refresh_token: Refresh token for long-lived sessions
    - azure_token_expires_at: Token expiration timestamp

Usage:
    janito --set-secret azure_client_id=your-client-id
    janito --onedrive-auth
"""

from .create_folder import CreateOneDriveFolder
from .delete_file import DeleteOneDriveFile
from .download_file import DownloadOneDriveFile
from .get_share_link import GetOneDriveShareLink
from .list_files import ListOneDriveFiles
from .read_file import ReadOneDriveFile
from .search_files import SearchOneDriveFiles
from .upload_file import UploadOneDriveFile

ONEDRIVE_SYSTEM_PROMPT = """
- You are an AI assistant with access to Microsoft OneDrive tools for file management
- Use the ListOneDriveFiles tool to browse folders and list files
- Use the SearchOneDriveFiles tool to find files by name or content
- Use the ReadOneDriveFile tool to get file metadata
- Use the DownloadOneDriveFile tool to download file content
- Use the UploadOneDriveFile tool to upload files to OneDrive
- Use the DeleteOneDriveFile tool to delete files
- Use the CreateOneDriveFolder tool to create new folders
- Use the GetOneDriveShareLink tool to create sharing links
- Explore the current directory for potential content related to the question
- When users ask about files in OneDrive, use ListOneDriveFiles first
- When users ask about searching for files, use SearchOneDriveFiles
- When users want to find specific documents, use SearchOneDriveFiles with appropriate query
"""

__all__ = [
    "ONEDRIVE_SYSTEM_PROMPT",
    "CreateOneDriveFolder",
    "DeleteOneDriveFile",
    "DownloadOneDriveFile",
    "GetOneDriveShareLink",
    "ListOneDriveFiles",
    "ReadOneDriveFile",
    "SearchOneDriveFiles",
    "UploadOneDriveFile",
]
