# OneDrive Tools

Janito4 provides tools for interacting with Microsoft OneDrive using the Microsoft Graph API.

## Setup

### 1. Register an Azure AD Application

1. Go to [Azure Portal](https://portal.azure.com) → **Azure Active Directory** → **App registrations**
2. Click **"New registration"**
3. Set a name (e.g., "Janito4 OneDrive")
4. Choose supported account types:
   - **Personal accounts**: Select "Accounts in any personal Microsoft account"
   - **Work/School accounts**: Select "Accounts in any organizational directory"
5. Click **"Register"**
6. Copy the **"Application (client) ID"**

### 2. Configure Secrets

```bash
# Set your client ID
janito4 --set-secret azure_client_id=your-client-id
```

### 3. Authenticate (One-Time)

```bash
janito4 --onedrive-auth
```

You'll see instructions:

```
Step 1: Open this URL in your browser:
   https://microsoft.com/devicelogin

Step 2: Enter this code:
   ABC123XYZ

Step 3: Sign in with your Microsoft account
Step 4: Click 'Continue' to grant permissions

Waiting for authentication...
✓ Authentication successful!
```

## Available Tools

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

## Usage

### Enable OneDrive Tools

```bash
# Interactive chat with OneDrive
janito4 --onedrive

# Single prompt with OneDrive
janito4 --onedrive "List my files in Documents folder"
```

### Example Prompts

```bash
# List files in a folder
janito4 --onedrive "List my files in Documents"

# Search for files
janito4 --onedrive "Find all PDF files in my OneDrive"

# Download a file
janito4 --onedrive "Download the quarterly report from the Finance folder"

# Upload a file
janito4 --onedrive "Upload notes.txt to Documents"

# Create a share link
janito4 --onedrive "Create a share link for report.pdf"
```

## Authentication Commands

| Command | Description |
|---------|-------------|
| `janito4 --onedrive-auth` | Authenticate with Microsoft |
| `janito4 --onedrive status` | Check auth status |
| `janito4 --onedrive logout` | Clear tokens and logout |

## Troubleshooting

### "azure_client_id not configured"

Run: `janito4 --set-secret azure_client_id=your-client-id`

### "Not authenticated"

Run: `janito4 --onedrive-auth`

### "Refresh token expired"

Run: `janito4 --onedrive-auth` to re-authenticate

### File Size Limits

- Simple upload: Up to 4MB
- Resumable upload: Supports large files (automatic)

## More Info

For CLI access, see [janito4/tools/README.onedrive.md](https://github.com/ikignosis/janito4/blob/main/janito4/tools/README.onedrive.md)
