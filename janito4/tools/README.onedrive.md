# OneDrive Tools

This directory contains tools for interacting with Microsoft OneDrive using the Microsoft Graph API.

## Authentication

This tool uses **device code flow** for authentication, which supports:
- ✅ **Personal Microsoft accounts** (outlook.com, hotlook.com, live.com, etc.)
- ✅ **Work/School accounts** (Azure AD / Microsoft 365)

This is the recommended authentication method as it:
- Works with all Microsoft account types
- Provides persistent refresh tokens
- Requires only **one-time interactive login**
- All subsequent uses are fully automated

## Setup

### 1. Register an Azure AD Application

1. Go to [Azure Portal](https://portal.azure.com) → **Azure Active Directory** → **App registrations**
2. Click **"New registration"**
3. Set a name (e.g., "Janito4 OneDrive")
4. Choose supported account types:
   - **For personal Microsoft accounts only**: Select "Accounts in any personal Microsoft account (e.g. hotmail.com, outlook.com, live.com)"
     - **Important**: This uses the `/consumers` endpoint
   - **For work/school accounts only**: Select "Accounts in any organizational directory"
     - **Important**: This uses the `/organizations` endpoint
   - **For both**: Select both options and contact support
5. Click **"Register"**
6. Copy the **"Application (client) ID"**

### 2. Configure Secrets

```bash
# Set your client ID
janito4 --set-secret azure_client_id=your-client-id
```

### 3. Authenticate (One-Time Only)

```bash
# Start authentication
janito4 --onedrive-auth
```

You'll see instructions like:

```
============================================================
  MICROSOFT ONEDRIVE AUTHENTICATION
============================================================

  Step 1: Open this URL in your browser:
     https://microsoft.com/devicelogin

  Step 2: Enter this code:
     ABC123XYZ

  Step 3: Sign in with your Microsoft account
  Step 4: Click 'Continue' to grant permissions

  Waiting for authentication...
  ✓ Authentication successful!
```

### 4. Verify Authentication

```bash
# Check auth status
janito4 --onedrive status

# Or just try listing files
janito4 --onedrive "List my files"
```

### Authentication Commands

| Command | Description |
|---------|-------------|
| `janito4 --onedrive-auth` | Authenticate with Microsoft account |
| `janito4 --onedrive status` | Check authentication status |
| `janito4 --onedrive logout` | Clear tokens and log out |

## Usage

### Enable OneDrive Tools

```bash
# Interactive chat mode with OneDrive
janito4 --onedrive

# Single prompt with OneDrive
janito4 --onedrive "List my files in Documents folder"
```

### Available Tools

| Tool | Description | Permissions |
|------|-------------|-------------|
| `ListOneDriveFiles` | List files and folders | `r` |
| `SearchOneDriveFiles` | Search for files | `r` |
| `ReadOneDriveFile` | Get file metadata | `r` |
| `DownloadOneDriveFile` | Download file content | `r` |
| `UploadOneDriveFile` | Upload files | `w` |
| `DeleteOneDriveFile` | Delete files/folders | `rw` |
| `CreateOneDriveFolder` | Create folders | `w` |
| `GetOneDriveShareLink` | Create share links | `r` |

### CLI Commands

```bash
# List files
python -m janito4.tools.onedrive list-files
python -m janito4.tools.onedrive list-files --path Documents --folders-only

# Search files
python -m janito4.tools.onedrive search-files "report"
python -m janito4.tools.onedrive search-files "report" --type docx --folder Projects

# Read file metadata
python -m janito4.tools.onedrive read-file "Documents/readme.txt"
python -m janito4.tools.onedrive read-file "Documents/readme.txt" --content

# Authenticate
python -m janito4.tools.onedrive authenticate
python -m janito4.tools.onedrive status
python -m janito4.tools.onedrive logout
```

## Common Use Cases

### Browse OneDrive Files

```python
ListOneDriveFiles(path="", limit=50)
# Lists files in root folder

ListOneDriveFiles(path="Documents/Projects", limit=100)
# Lists files in specific folder
```

### Search for Documents

```python
SearchOneDriveFiles(query="quarterly report", file_type_filter="pdf")
# Finds PDF files containing "quarterly report"

SearchOneDriveFiles(query="presentation", folder_path="Documents")
# Searches only in Documents folder
```

### Download a File

```python
DownloadOneDriveFile(
    path="Documents/report.pdf",
    output_path="/tmp/local_report.pdf"
)
# Downloads to local file
```

### Upload a File

```python
UploadOneDriveFile(
    path="Documents/uploaded_notes.txt",
    content="These are my notes..."
)
# Uploads text content

UploadOneDriveFile(
    path="Documents/backup.zip",
    local_path="/tmp/backup.zip"
)
# Uploads local file
```

### Create a Share Link

```python
GetOneDriveShareLink(
    path="Documents/report.pdf",
    link_type="view",
    scope="anonymous"
)
# Creates read-only share link for anyone
```

## Troubleshooting

### Authentication Errors

**Error: "azure_client_id not configured"**
- Run: `janito4 --set-secret azure_client_id=your-client-id`
- See Setup section above

**Error: "Not authenticated"**
- Run: `janito4 --onedrive-auth`

**Error: "Authentication expired"**
- Run: `janito4 --onedrive-auth` to re-authenticate

**Error: "Refresh token expired"**
- Run: `janito4 --onedrive-auth` to re-authenticate

### Token Expiration

Access tokens typically expire after 1 hour. The tool automatically refreshes tokens using the stored refresh token, so you shouldn't need to re-authenticate frequently.

If you see "Refresh token expired", run:
```bash
janito4 --onedrive-auth
```

### File Size Limits

- Simple upload: Up to 4MB
- Resumable upload: Supports large files (automatically used for files >4MB)

### Need to Use a Different Account?

```bash
# Log out first
janito4 --onedrive logout

# Then authenticate with the new account
janito4 --onedrive-auth
```

## Graph API Reference

For more details on the Microsoft Graph API:
- [DriveItem documentation](https://docs.microsoft.com/en-us/graph/api/resources/driveitem)
- [Graph API overview](https://docs.microsoft.com/en-us/graph/api/overview)
