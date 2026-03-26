# Gmail Tools

Janito4 provides comprehensive tools for interacting with Gmail via IMAP.

## Setup

### Prerequisites

1. **Enable IMAP in Gmail:**
   - Open Gmail → Settings → See all settings → IMAP Access
   - Enable IMAP Access

2. **Generate an App Password:**
   - Go to [Google Account Security](https://myaccount.google.com/security)
   - Enable 2-Factor Authentication if not already enabled
   - Go to App Passwords → Create a new app password
   - Use a name like "Janito4" to generate a 16-character password

3. **Configure Secrets:**

   ```bash
   janito4 --set-secret gmail_username=your-email@gmail.com
   janito4 --set-secret gmail_password=your-app-password
   ```

## Available Tools

| Tool | Description |
|------|-------------|
| `ReadEmails` | Read emails from Gmail folders |
| `CountEmails` | Count emails in folders |
| `DeleteEmails` | Permanently delete emails |
| `TrashEmail` | Move emails to Trash (recoverable) |
| `MoveEmails` | Move emails between folders |
| `ListFolders` | List all Gmail folders/labels |

## Usage

### Enable Gmail Tools

```bash
# Interactive chat with Gmail
janito4 --gmail

# Single prompt with Gmail
janito4 --gmail "Show my unread emails from today"
```

### Example Prompts

```bash
# Check unread emails
janito4 --gmail "Show my unread emails from today"

# Find emails from a sender
janito4 --gmail "Find emails from newsletter@example.com"

# Search by subject
janito4 --gmail "Search for emails with 'invoice' in subject"

# Count emails older than 30 days
janito4 --gmail "How many emails in inbox are older than 30 days?"

# Delete old spam (always safe to ask first!)
janito4 --gmail "Show me spam emails older than 90 days"
```

## Gmail Labels/Folders

| Folder | Description |
|--------|-------------|
| `INBOX` | Primary inbox |
| `[Gmail]/All Mail` | All messages |
| `[Gmail]/Drafts` | Draft messages |
| `[Gmail]/Sent Mail` | Sent messages |
| `[Gmail]/Spam` | Spam folder |
| `[Gmail]/Trash` | Deleted messages |

## Common IMAP Queries

| Query | Description |
|-------|-------------|
| `ALL` | All messages |
| `UNSEEN` | Unread messages |
| `FROM "user@example.com"` | From specific sender |
| `SUBJECT "keyword"` | Subject contains keyword |
| `SINCE 01-Jan-2024` | After specific date |
| `LARGER 1000000` | Larger than 1MB |

## Tips

1. **Always use `dry_run=True` first** when deleting or moving emails
2. **Use `CountEmails`** before `ReadEmails` to check how many emails match
3. **Trash is safer than Delete** - emails in Trash can be recovered for 30 days

## Troubleshooting

### Authentication Errors

```
IMAP connection error: [AUTHENTICATIONFAILED]
```

- Verify you generated an **App Password**, not your regular Gmail password
- Check that IMAP is enabled in Gmail settings

### Folder Not Found

```
Failed to select folder: folder-name
```

- Use `ListFolders` to get exact folder names
- Gmail labels are case-sensitive
