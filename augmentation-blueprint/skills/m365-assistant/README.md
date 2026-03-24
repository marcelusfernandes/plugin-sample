# M365 Assistant

Integration with Microsoft 365 via Microsoft Graph API. Provides access to Outlook email, Calendar, Teams, SharePoint, Planner, and more.

## Setup

1. Install dependencies:
   ```bash
   pip install msal requests
   ```

2. Copy the config template and fill in your tenant details:
   ```bash
   cp config.template.json config.json
   ```

3. Edit `config.json`:
   - Set `tenant_id` to your Azure AD tenant ID (get from Azure portal or IT admin)
   - Adjust `timezone` if needed
   - Configure SharePoint `upload` section if you need file uploads

4. Authenticate:
   ```bash
   python graph.py auth login
   ```
   Follow the device code flow in your browser.

5. Verify:
   ```bash
   python graph.py auth status
   ```

## Configuration

| Field | Required | Description |
|-------|----------|-------------|
| `app_id` | Yes | Azure AD app registration ID (default uses MS Graph PowerShell) |
| `tenant_id` | Yes | Your Azure AD tenant ID |
| `token_path` | No | Where to store auth tokens (default: `~/.m365_token.json`) |
| `timezone` | No | Timezone for calendar events (default: `America/Sao_Paulo`) |
| `upload.*` | No | SharePoint drive/folder for uploads |
| `archive_dir` | No | Local directory for email/chat archives (default: `~/Projects`) |

## Usage

See `SKILL.md` for the complete command reference.

## Security Notes

- `config.json` contains your tenant ID — do NOT commit it to version control
- Auth tokens are stored locally at `token_path` — keep them secure
- The tool never sends emails or messages without explicit user confirmation
