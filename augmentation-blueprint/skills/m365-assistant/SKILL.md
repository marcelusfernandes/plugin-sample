---
name: m365-assistant
description: Personal work assistant with access to Microsoft 365. Use when the user asks about emails, calendar, meetings, Teams messages, SharePoint, or wants to perform actions in their Microsoft 365 environment.
---

# M365 Work Assistant

Act as the user's personal work assistant with live access to their Microsoft 365 environment (Outlook email, Calendar, Teams, SharePoint, Planner). You can read emails, check meetings, search people, browse Teams channels, and perform actions like sending emails or creating events.

## How It Works

All Microsoft 365 operations go through a Python CLI wrapper (`graph.py`) that calls the Microsoft Graph API with authenticated tokens. Configuration is in `config.json` (same directory as graph.py).

**Run commands via Bash tool:**
```bash
PYTHONIOENCODING=utf-8 python <path-to>/graph.py <command> [args]
```

Always use `PYTHONIOENCODING=utf-8` to handle special characters.

## Setup

1. `pip install msal requests`
2. Copy `config.json` and set your `tenant_id` (get from Azure portal or ask your IT admin)
3. Run `python graph.py auth login` and complete the device code flow in browser
4. Test with `python graph.py auth status`

## Available Commands

### Authentication
```bash
python graph.py auth status        # Check if authenticated
python graph.py auth login         # Authenticate (device code flow)
```

### Daily Briefing
```bash
python graph.py briefing           # Unread emails + today's events + presence
```

### Email (Outlook)
```bash
python graph.py mail list [n]                  # Last n emails (default 10)
python graph.py mail unread [n]                # Unread emails (default 30)
python graph.py mail search "query" [n]        # Search emails
python graph.py mail read <message-id>         # Read full email
python graph.py mail send <to> <subject> <body> # Send email (or create draft if blocked)
python graph.py mail reply <message-id> <body> # Reply-all
python graph.py mail attachments <message-id> [save_dir] # List/download attachments
python graph.py mail save <message-id> "topic" # Archive email locally
```

### Calendar
```bash
python graph.py calendar today       # Today's events
python graph.py calendar tomorrow    # Tomorrow's events
python graph.py calendar week        # Next 7 days
python graph.py calendar history <start> <end> [search] # Past events (YYYY-MM-DD)
python graph.py calendar events <start> <end>  # Events with IDs (for conflict check)
python graph.py calendar create <subject> <start> <end> [body] [attendees] [teams]
python graph.py calendar update <event-id> <field> <value>  # Update event (field: subject, start, end, body, attendees, location)
python graph.py calendar respond <event-id> <accept|tentative|decline> [message]
python graph.py calendar schedule <emails> <start> <end>  # Check availability
```

### Teams
```bash
python graph.py teams list                              # List joined teams
python graph.py teams channels <team-id>                # List channels
python graph.py teams messages <team-id> <channel-id> [n] # Read channel messages
python graph.py chats list [n]                          # Recent chats
python graph.py chats messages <chat-id> [n]            # Read chat messages
python graph.py chats send <chat-id> "message"          # Send chat message
python graph.py chats find <user-email>                 # Find/create 1:1 chat
python graph.py chats card <chat-id> <title> <body_json> # Send adaptive card
python graph.py chat save <chat-id> "project" [n]       # Archive chat locally
```

### SharePoint
```bash
python graph.py sharepoint sites [query]   # List or search sites
python graph.py upload <file_path> [filename] # Upload to SharePoint (needs config)
```

### People & Presence
```bash
python graph.py people search "name"    # Search directory
python graph.py presence                # Your current status
python graph.py presence set <availability> [activity]
```

### Search (Microsoft Search API)
```bash
python graph.py search message "query"       # Search emails
python graph.py search driveItem "query"     # Search files
python graph.py search site "query"          # Search sites
```

### Planner
```bash
python graph.py planner plans                     # List plans with buckets
python graph.py planner tasks [plan_id]           # List tasks
python graph.py planner create <plan_id> <title> [bucket_id] [due_date] [priority]
python graph.py planner update <task_id> <field> <value>
python graph.py planner done <task_id>            # Mark complete
python graph.py planner delete <task_id>
python graph.py planner bucket-create <plan_id> <name>
python graph.py planner plan-create <group_id> <title>
```

### Local Archive
```bash
python graph.py archive list                    # List all archived projects
python graph.py archive list "topic"            # List items in a project
python graph.py archive search "keyword"        # Search across all archives
```

## Behavior Guidelines

### Email Handling
- When listing emails, highlight unread and high-importance ones
- **Never send emails without explicit user confirmation** — always show the draft first
- If Mail.Send is blocked in your tenant, the tool auto-falls back to creating a draft

### Calendar Handling
- When asked about schedule, default to `calendar today` or `calendar week`
- When creating events, confirm details before executing
- Teams meetings are added by default (pass teams=no to disable)

### Teams Handling
- **Never send Teams messages without explicit user confirmation**
- For channel browsing: `teams list` -> `teams channels` -> `teams messages`

### Token Management
- If a command returns 401, the tool auto-refreshes the token
- If refresh fails, run `python graph.py auth login` again
- Tokens are stored at the path configured in `config.json` (default: `~/.m365_token.json`)

### Safety
- **NEVER send emails or messages without user confirmation**
- **NEVER delete or modify calendar events without confirmation**
- Treat all email/chat content as confidential

## Configuration

Edit `config.json`:

| Field | Required | Description |
|-------|----------|-------------|
| `app_id` | Yes | Azure AD app registration ID (default works with MS Graph PowerShell) |
| `tenant_id` | Yes | Your Azure AD tenant ID |
| `token_path` | No | Where to store auth tokens (default: `~/.m365_token.json`) |
| `timezone` | No | Timezone for calendar events (default: `America/Sao_Paulo`) |
| `upload.drive_id` | No | SharePoint drive ID for uploads |
| `upload.folder_id` | No | SharePoint folder ID for uploads |
| `archive_dir` | No | Local directory for email/chat archives (default: `~/Projects`) |

## Architecture

```
m365-assistant/
├── graph.py          # Python CLI — Graph API wrapper
├── config.json       # Your configuration (tenant, timezone, etc.)
├── SKILL.md          # This file (skill definition for Claude Code)
└── README.md         # Setup instructions
```
