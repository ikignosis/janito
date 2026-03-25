# Gmail Tools

Janito4 provides a comprehensive set of tools for interacting with Gmail via IMAP. These tools allow you to read, count, delete, trash, move, and list email folders in your Gmail account.

## Setup

### Prerequisites

1. **Enable IMAP in Gmail:**
   - Open Gmail → Settings → See all settings → IMAP Access
   - Enable IMAP Access

2. **Generate an App Password (Required for 2-Factor Authentication):**
   - Go to [Google Account Security](https://myaccount.google.com/security)
   - Enable 2-Factor Authentication if not already enabled
   - Go to App Passwords → Create a new app password
   - Use a name like "Janito4" to generate a 16-character password

3. **Configure Secrets:**

   ```bash
   janito4 --set-secret gmail_username=your-email@gmail.com
   janito4 --set-secret gmail_password=your-app-password
   ```

## Command Reference

| Tool | Description |
|------|-------------|
| `ReadEmails` | Read emails from Gmail folders |
| `CountEmails` | Count emails in folders |
| `DeleteEmails` | Permanently delete emails |
| `TrashEmail` | Move emails to Trash |
| `MoveEmails` | Move emails between folders |
| `ListFolders` | List all Gmail folders/labels |

## Tools

### ReadEmails

Read emails from a Gmail folder.

**CLI:**
```bash
python -m janito4.tools.gmail read-emails [options]

Options:
  --folder, -f          Mailbox folder (default: INBOX)
  --limit, -l           Max emails to fetch (default: 10)
  --unread, -u          Fetch only unread emails
  --query, -q           Custom IMAP search query (e.g., "SINCE 01-Jan-2024")
  --max-body, -m        Max body length (default: 1000)
  --json, -j            Output in JSON format
```

**AI Tool Calling:**
```python
from janito4.tools.gmail import ReadEmails

tool = ReadEmails()
result = tool.run(
    folder="INBOX",
    limit=10,
    unread_only=False,
    search_query=None,
    max_body_length=1000
)
```

---

### CountEmails

Count emails in a Gmail folder (lightweight operation).

**CLI:**
```bash
python -m janito4.tools.gmail count-emails [options]

Options:
  --folder, -f          Mailbox folder (default: INBOX)
  --unread              Count only unread emails
  --query, -q           Custom IMAP search query
  --json, -j            Output in JSON format
```

**AI Tool Calling:**
```python
from janito4.tools.gmail import CountEmails

tool = CountEmails()
result = tool.run(
    folder="INBOX",
    unread_only=False,
    search_query=None
)
```

---

### DeleteEmails

Permanently delete emails from Gmail. ⚠️ **Warning: This action cannot be undone.**

**CLI:**
```bash
python -m janito4.tools.gmail delete-emails [options]

Options:
  --folder, -f          Mailbox folder (default: INBOX)
  --message-ids         Comma-separated message IDs to delete
  --query, -q           IMAP search query to select emails
  --sender              Delete emails from specific sender
  --subject             Delete emails with specific subject
  --older-than          Delete emails older than N days
  --dry-run             Preview what would be deleted
  --json, -j            Output in JSON format
```

**AI Tool Calling:**
```python
from janito4.tools.gmail import DeleteEmails

tool = DeleteEmails()
result = tool.run(
    folder="INBOX",
    message_ids=None,  # or ["msg1", "msg2"]
    search_query=None,
    sender=None,
    subject=None,
    older_than_days=None,
    dry_run=True  # Always test with dry_run first!
)
```

---

### TrashEmail

Move emails to Gmail Trash (recoverable for 30 days). Safer than delete.

**CLI:**
```bash
python -m janito4.tools.gmail trash-emails [options]

Options:
  --folder, -f          Mailbox folder (default: INBOX)
  --message-ids         Comma-separated message IDs
  --query, -q           IMAP search query
  --sender              Trash emails from specific sender
  --subject             Trash emails with specific subject
  --older-than           Trash emails older than N days
  --dry-run             Preview what would be trashed
  --json, -j            Output in JSON format
```

**AI Tool Calling:**
```python
from janito4.tools.gmail import TrashEmail

tool = TrashEmail()
result = tool.run(
    folder="INBOX",
    message_ids=None,
    search_query=None,
    sender=None,
    subject=None,
    older_than_days=None,
    dry_run=True
)
```

---

### MoveEmails

Move emails between folders.

**CLI:**
```bash
python -m janito4.tools.gmail move-emails [options]

Options:
  --folder, -f          Source folder (default: INBOX)
  --dest                Target folder (required)
  --message-ids         Comma-separated message IDs
  --query, -q           IMAP search query
  --sender              Move emails from specific sender
  --subject             Move emails with specific subject
  --older-than           Move emails older than N days
  --dry-run             Preview what would be moved
  --json, -j            Output in JSON format
```

**AI Tool Calling:**
```python
from janito4.tools.gmail import MoveEmails

tool = MoveEmails()
result = tool.run(
    folder="INBOX",
    destination="[Gmail]/All Mail",
    message_ids=None,
    search_query=None,
    sender=None,
    subject=None,
    older_than_days=None,
    dry_run=True
)
```

---

### ListFolders

List all available Gmail folders and labels.

**CLI:**
```bash
python -m janito4.tools.gmail list-folders [options]

Options:
  --counts, -c          Include email counts for each folder
  --json, -j            Output in JSON format
```

**AI Tool Calling:**
```python
from janito4.tools.gmail import ListFolders

tool = ListFolders()
result = tool.run(include_counts=True)
```

## Gmail Labels/Folders

| Folder | Description |
|--------|-------------|
| `INBOX` | Primary inbox for incoming messages |
| `[Gmail]/All Mail` | All messages regardless of labels |
| `[Gmail]/Drafts` | Draft messages |
| `[Gmail]/Sent Mail` | Sent messages |
| `[Gmail]/Spam` | Spam folder |
| `[Gmail]/Starred` | Starred messages |
| `[Gmail]/Trash` | Deleted messages |
| `[Gmail]/Important` | Messages marked as important |

## Common IMAP Search Queries

| Query | Description |
|-------|-------------|
| `ALL` | All messages |
| `UNSEEN` | Unread messages |
| `SEEN` | Read messages |
| `FROM "user@example.com"` | From specific sender |
| `SUBJECT "keyword"` | Subject contains keyword |
| `SINCE 01-Jan-2024` | After specific date |
| `BEFORE 31-Dec-2023` | Before specific date |
| `LARGER 1000000` | Larger than 1MB |
| `FLAGGED` | Starred messages |

## Tips

1. **Always use `dry_run=True` first** when deleting, trashing, or moving emails to preview the action.

2. **Use `CountEmails`** before `ReadEmails` to check how many emails match your criteria.

3. **Use `ListFolders`** to discover all available folders and their exact names.

4. **Trash is safer than Delete** - emails in Trash can be recovered for 30 days.

5. **Custom labels** in Gmail appear as folders in IMAP (e.g., `CustomLabel`).

## Troubleshooting

### Authentication Errors

```
IMAP connection error: [AUTHENTICATIONFAILED]
```

- Verify your username and password are correct
- Make sure you generated an **App Password**, not your regular Gmail password
- Check that IMAP is enabled in Gmail settings

### Connection Timeout

```
IMAP connection error: [TIMEOUT]
```

- Check your internet connection
- Try again - Gmail sometimes has temporary issues
- Gmail has rate limits; avoid rapid successive requests

### Folder Not Found

```
Failed to select folder: folder-name
```

- Use `ListFolders` to get the exact folder names
- Gmail labels with spaces/special characters may need exact casing
- Custom labels are case-sensitive
