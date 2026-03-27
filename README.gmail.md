# Gmail Tools

This document explains how to set up and use Gmail tools with janito.

## Setup

### 1. Configure Gmail Credentials

Gmail tools require two secrets to be stored securely:

```bash
# Set your Gmail address
janito --set-secret gmail_username=your-email@gmail.com

# Set your Gmail app password
janito --set-secret gmail_password=your-app-password
```

### 2. Generate an App Password (Required for Gmail)

If your Gmail account has **2-Step Verification** enabled (which is recommended), you cannot use your regular password with IMAP. You must generate an **App Password**:

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Under "2-Step Verification", make sure it's turned on
3. Go to "App passwords"
4. Select "Mail" and "Other (Custom name)" 
5. Enter a name like "janito" and click "Generate"
6. Copy the 16-character password that appears
7. Use this app password for `gmail_password`

**Note:** App passwords are only shown once, so save it immediately.

### 3. Enable IMAP in Gmail

Make sure IMAP is enabled in your Gmail settings:

1. Open Gmail
2. Click Settings (⚙️) → See all settings
3. Go to the "Forwarding and POP/IMAP" tab
4. Under "IMAP access", select "Enable IMAP"
5. Click "Save Changes"

## Usage

### Interactive Chat Mode

```bash
# Start interactive chat with Gmail tools enabled
janito --gmail
```

Example conversation:
```
You: How many unread emails do I have?
AI: Let me check your inbox...
[Uses CountEmails tool]
You have 12 unread emails in your INBOX.

You: Show me the latest ones
AI: Let me fetch your recent emails...
[Uses ReadEmails tool]
Here are your 5 most recent emails:
1. Subject: Meeting Tomorrow, From: colleague@company.com
2. Subject: Project Update, From: manager@company.com
...
```

### Single Prompt Mode

```bash
# Count unread emails
janito --gmail "How many unread emails do I have?"

# Read recent emails
janito --gmail "Show me my last 5 emails"

# Search for specific emails
janito --gmail "Find emails from last week about the project"
```

### List Available Gmail Tools

```bash
janito --gmail --list-tools
```

Output:
```
Email Operations:
  CountEmails [r] (folder, unread_only, search_query)
  ReadEmails [r] (folder, limit, unread_only, search_query, max_body_length)
```

## Available Tools

### CountEmails

Quickly check email counts without downloading content.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `folder` | string | "INBOX" | Mailbox folder to count from |
| `unread_only` | bool | false | Count only unread emails |
| `search_query` | string | null | Custom IMAP search query |

**Returns:**
- `total_count`: Total emails in folder
- `unread_count`: Unread emails in folder
- `matching_count`: Emails matching search criteria

### ReadEmails

Fetch email content from your inbox.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `folder` | string | "INBOX" | Mailbox folder to read from |
| `limit` | int | 10 | Maximum emails to fetch |
| `unread_only` | bool | false | Fetch only unread emails |
| `search_query` | string | null | Custom IMAP search query |
| `max_body_length` | int | 1000 | Max characters per email body |

## IMAP Search Examples

Use `search_query` parameter with IMAP syntax for advanced searches:

| Query | Description |
|-------|-------------|
| `SINCE 01-Jan-2024` | Emails since January 1, 2024 |
| `BEFORE 31-Dec-2023` | Emails before December 31, 2023 |
| `FROM sender@example.com` | Emails from specific sender |
| `SUBJECT "invoice"` | Emails with "invoice" in subject |
| `BODY "keyword"` | Emails containing keyword in body |
| `SEEN` | Read emails only |
| `UNSEEN` | Unread emails only |
| `FLAGGED` | Starred emails |
| `LARGER 1000000` | Emails larger than 1MB |

### Examples

```bash
# Count emails from a specific sender
janito --gmail "How many emails did John send me?"

# Read emails from this week
janito --gmail -- "Read emails from the last 7 days"

# Find all unread invoices
janito --gmail "Find any unread emails about invoices"
```

## Troubleshooting

### "IMAP connection error: AUTHENTICATIONFAILED"

**Cause:** Wrong password or app password not set up correctly.

**Solution:** 
1. Make sure you created an App Password (not your regular password)
2. Re-set the secret: `janito --set-secret gmail_password=your-new-app-password`

### "Failed to select folder"

**Cause:** Folder name doesn't exist.

**Solution:** Check your folder names. Common folders:
- INBOX
- "[Gmail]/Sent Mail"
- "[Gmail]/Trash"
- "[Gmail]/Spam"

### "Secret 'gmail_username' not configured"

**Cause:** Credentials not set up.

**Solution:** 
```bash
janito --set-secret gmail_username=your-email@gmail.com
janito --set-secret gmail_password=your-app-password
```

### Connection Timeout

**Cause:** Network issues or IMAP not enabled.

**Solution:**
1. Check your internet connection
2. Verify IMAP is enabled in Gmail settings
3. Try again - Gmail sometimes has temporary issues

## Security Notes

- Your credentials are stored in `~/.janito/secrets.json` with restricted permissions (600)
- App passwords should be treated like regular passwords
- Consider enabling 2-Step Verification on your Google account
- Revoke app passwords if you no longer need them (via Google Account Security)
