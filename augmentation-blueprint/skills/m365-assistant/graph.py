"""
Microsoft Graph API client for Claude Code agent.
Handles authentication, token refresh, and API calls.

Usage from Claude Code (via Bash tool):
    PYTHONIOENCODING=utf-8 python graph.py mail list
    PYTHONIOENCODING=utf-8 python graph.py calendar today
    PYTHONIOENCODING=utf-8 python graph.py teams list

Setup:
    1. pip install msal requests
    2. Edit config.json with your tenant_id (and optionally upload drive/folder IDs)
    3. python graph.py auth login
"""

import sys
import os
import io
import json

# Fix encoding for Windows cp1252 console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
import re
import base64
import datetime
import requests
from pathlib import Path

# === CONFIG (loaded from config.json) ===
_SCRIPT_DIR = Path(__file__).parent
_CONFIG_PATH = _SCRIPT_DIR / "config.json"

def _load_config():
    if not _CONFIG_PATH.exists():
        print(f"ERROR: config.json not found at {_CONFIG_PATH}", file=sys.stderr)
        print("Copy config.json.example to config.json and fill in your values.", file=sys.stderr)
        sys.exit(1)
    with open(_CONFIG_PATH) as f:
        return json.load(f)

_CFG = _load_config()

TOKEN_PATH = Path(os.path.expanduser(_CFG.get("token_path", "~/.m365_token.json")))
APP_ID = _CFG["app_id"]
TENANT_ID = _CFG["tenant_id"]
TIMEZONE = _CFG.get("timezone", "America/Sao_Paulo")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
GRAPH_BASE = "https://graph.microsoft.com/v1.0"
GRAPH_BETA = "https://graph.microsoft.com/beta"

# Upload config (optional — only needed for `upload` command)
_UPLOAD_CFG = _CFG.get("upload", {})
UPLOAD_DRIVE_ID = _UPLOAD_CFG.get("drive_id", "")
UPLOAD_FOLDER_ID = _UPLOAD_CFG.get("folder_id", "")
UPLOAD_BASE_URL = _UPLOAD_CFG.get("base_url", "")

ARCHIVE_DIR = Path(os.path.expanduser(_CFG.get("archive_dir", "~/Projects")))


# === AUTH ===

def load_token():
    """Load token from disk."""
    if not TOKEN_PATH.exists():
        print("ERROR: Not authenticated. Run: python graph.py auth login", file=sys.stderr)
        sys.exit(1)
    with open(TOKEN_PATH) as f:
        return json.load(f)


def save_token(token_data):
    """Save token to disk. Computes expires_at from expires_in if missing."""
    if "expires_in" in token_data and "expires_at" not in token_data:
        token_data["expires_at"] = datetime.datetime.now().timestamp() + token_data["expires_in"]
    with open(TOKEN_PATH, "w") as f:
        json.dump(token_data, f)


def refresh_token():
    """Refresh access token using refresh_token."""
    from msal import PublicClientApplication
    app = PublicClientApplication(APP_ID, authority=AUTHORITY)
    token = load_token()
    rt = token.get("refresh_token")
    if not rt:
        print("ERROR: No refresh token. Run: python graph.py auth login", file=sys.stderr)
        sys.exit(1)
    result = app.acquire_token_by_refresh_token(rt, scopes=["User.Read"])
    if "access_token" in result:
        save_token(result)
        return result
    else:
        print(f"ERROR refreshing: {result.get('error_description', result)}", file=sys.stderr)
        sys.exit(1)


def get_headers():
    """Get Authorization headers, refreshing token if needed."""
    token = load_token()
    expires_at = token.get("expires_at")
    if expires_at and datetime.datetime.now().timestamp() > expires_at - 300:
        token = refresh_token()
    return {"Authorization": f"Bearer {token['access_token']}"}


def graph_get(endpoint, params=None, beta=False):
    """GET request to Graph API."""
    base = GRAPH_BETA if beta else GRAPH_BASE
    url = f"{base}{endpoint}" if endpoint.startswith("/") else endpoint
    r = requests.get(url, headers=get_headers(), params=params)
    if r.status_code in (401, 403):
        refresh_token()
        r = requests.get(url, headers=get_headers(), params=params)
    if r.status_code != 200:
        err = r.json().get("error", {})
        print(f"ERROR {r.status_code}: {err.get('code', '')} — {err.get('message', '')}", file=sys.stderr)
        sys.exit(1)
    return r.json()


def graph_post(endpoint, data, beta=False, extra_headers=None):
    """POST request to Graph API."""
    base = GRAPH_BETA if beta else GRAPH_BASE
    url = f"{base}{endpoint}" if endpoint.startswith("/") else endpoint
    headers = get_headers()
    headers["Content-Type"] = "application/json"
    if extra_headers:
        headers.update(extra_headers)
    r = requests.post(url, headers=headers, json=data)
    if r.status_code in (401, 403):
        refresh_token()
        headers = get_headers()
        headers["Content-Type"] = "application/json"
        if extra_headers:
            headers.update(extra_headers)
        r = requests.post(url, headers=headers, json=data)
    if r.status_code not in (200, 201, 202):
        err = r.json().get("error", {})
        print(f"ERROR {r.status_code}: {err.get('code', '')} — {err.get('message', '')}", file=sys.stderr)
        sys.exit(1)
    return r.json() if r.text else {}


def _graph_patch(endpoint, data, etag=None):
    """PATCH request to Graph API."""
    headers = get_headers()
    headers["Content-Type"] = "application/json"
    if etag:
        headers["If-Match"] = etag
    url = f"{GRAPH_BASE}{endpoint}" if endpoint.startswith("/") else endpoint
    r = requests.patch(url, headers=headers, json=data)
    if r.status_code in (401, 403):
        refresh_token()
        headers = get_headers()
        headers["Content-Type"] = "application/json"
        if etag:
            headers["If-Match"] = etag
        r = requests.patch(url, headers=headers, json=data)
    if r.status_code not in (200, 204):
        err = r.json().get("error", {}) if r.text else {}
        print(f"ERROR {r.status_code}: {err.get('code', '')} — {err.get('message', '')}", file=sys.stderr)
        sys.exit(1)
    return r.json() if r.text and r.status_code == 200 else {}


def _graph_delete(endpoint, etag=None):
    """DELETE request to Graph API."""
    headers = get_headers()
    if etag:
        headers["If-Match"] = etag
    url = f"{GRAPH_BASE}{endpoint}" if endpoint.startswith("/") else endpoint
    r = requests.delete(url, headers=headers)
    if r.status_code in (401, 403):
        refresh_token()
        headers = get_headers()
        if etag:
            headers["If-Match"] = etag
        r = requests.delete(url, headers=headers)
    if r.status_code not in (200, 204):
        err = r.json().get("error", {}) if r.text else {}
        print(f"ERROR {r.status_code}: {err.get('code', '')} — {err.get('message', '')}", file=sys.stderr)
        sys.exit(1)


# === COMMANDS ===

# --- AUTH ---
def cmd_auth_login():
    """Start device code login flow."""
    import webbrowser
    from msal import PublicClientApplication
    app = PublicClientApplication(APP_ID, authority=AUTHORITY)
    flow = app.initiate_device_flow(scopes=["User.Read", "OnlineMeetings.ReadWrite", "Files.Read.All", "Sites.Read.All"])
    if "user_code" not in flow:
        print(f"ERROR: {flow}", file=sys.stderr)
        sys.exit(1)
    code = flow['user_code']
    url = "https://microsoft.com/devicelogin"
    print(f"\n{'='*50}")
    print(f"  DEVICE CODE:  {code}")
    print(f"  URL:          {url}")
    print(f"{'='*50}")
    print(f"\nOpening browser automatically...")
    print(f"Paste the code above and authenticate.\n")
    sys.stdout.flush()
    sys.stderr.flush()
    webbrowser.open(url)
    result = app.acquire_token_by_device_flow(flow)
    if "access_token" in result:
        save_token(result)
        name = result.get("id_token_claims", {}).get("name", "?")
        email = result.get("id_token_claims", {}).get("preferred_username", "?")
        print(f"\nAuthenticated: {name} ({email})")
    else:
        print(f"ERROR: {result.get('error_description', result)}", file=sys.stderr)
        sys.exit(1)


def cmd_auth_status():
    """Check authentication status."""
    try:
        data = graph_get("/me")
        print(f"Authenticated: {data['displayName']} ({data.get('mail', 'N/A')})")
        print(f"Job: {data.get('jobTitle', 'N/A')}")
        print(f"Office: {data.get('officeLocation', 'N/A')}")
    except SystemExit:
        print("Not authenticated or token expired.")


# --- MAIL ---
def cmd_mail_list(n="10", query=None):
    """List recent emails."""
    params = {
        "$top": n,
        "$select": "id,subject,from,receivedDateTime,isRead,importance,hasAttachments",
        "$orderby": "receivedDateTime desc",
    }
    if query:
        params["$search"] = f'"{query}"'
        del params["$orderby"]
    data = graph_get("/me/messages", params=params)
    for m in data.get("value", []):
        dt = m["receivedDateTime"][:16].replace("T", " ")
        fr = m.get("from", {}).get("emailAddress", {}).get("name", "?")[:28]
        subj = (m.get("subject") or "(no subject)")[:60]
        read = " " if m.get("isRead") else "*"
        att = "[A]" if m.get("hasAttachments") else "   "
        msg_id = m.get("id", "")
        print(f"{read} {dt}  {fr:28s}  {att} {subj}")
        print(f"  ID: {msg_id}")
    print(f"\n({len(data.get('value', []))} messages)")


def cmd_mail_read(message_id):
    """Read a specific email."""
    data = graph_get(f"/me/messages/{message_id}")
    fr = data.get("from", {}).get("emailAddress", {})
    to_list = [r["emailAddress"]["address"] for r in data.get("toRecipients", [])]
    print(f"From:    {fr.get('name', '')} <{fr.get('address', '')}>")
    print(f"To:      {', '.join(to_list)}")
    print(f"Date:    {data['receivedDateTime'][:19].replace('T', ' ')}")
    print(f"Subject: {data.get('subject', '(no subject)')}")
    if data.get("hasAttachments"):
        atts = graph_get(f"/me/messages/{message_id}/attachments")
        for a in atts.get("value", []):
            print(f"Attach:  {a['name']} ({a.get('size', 0) // 1024}KB)")
    print(f"\n{'='*60}\n")
    body = data.get("body", {})
    if body.get("contentType") == "text":
        print(body.get("content", ""))
    else:
        html = body.get("content", "")
        text = re.sub(r'<[^>]+>', '', html)
        text = re.sub(r'\n\s*\n', '\n\n', text).strip()
        print(text[:3000])


def cmd_mail_send(to, subject, body, content_type="Text"):
    """Send an email. Falls back to creating a draft if Mail.Send scope is unavailable."""
    message = {
        "message": {
            "subject": subject,
            "body": {"contentType": content_type, "content": body},
            "toRecipients": [{"emailAddress": {"address": to}}],
        }
    }
    headers = get_headers()
    headers["Content-Type"] = "application/json"
    r = requests.post(f"{GRAPH_BASE}/me/sendMail", headers=headers, json=message)
    if r.status_code == 202:
        print(f"Email sent to {to}")
        return

    # Fallback: create draft + try to send it
    draft = {
        "subject": subject,
        "body": {"contentType": content_type, "content": body},
        "toRecipients": [{"emailAddress": {"address": to}}],
    }
    headers = get_headers()
    headers["Content-Type"] = "application/json"
    r = requests.post(f"{GRAPH_BASE}/me/messages", headers=headers, json=draft)
    if r.status_code != 201:
        err = r.json().get("error", {})
        print(f"ERROR creating draft: {err.get('code')} — {err.get('message', '')}", file=sys.stderr)
        sys.exit(1)
    msg_id = r.json()["id"]

    r2 = requests.post(f"{GRAPH_BASE}/me/messages/{msg_id}/send", headers=headers)
    if r2.status_code == 202:
        print(f"Email sent to {to} (via draft)")
    else:
        print(f"DRAFT created (Mail.Send scope not available)")
        print(f"Subject: {subject}")
        print(f"To: {to}")
        print(f"Status: Saved in Drafts — open Outlook to send manually")


def cmd_mail_reply(message_id, body, content_type="Text"):
    """Reply to an email (reply-all)."""
    payload = {
        "message": {
            "body": {"contentType": content_type, "content": body}
        }
    }
    graph_post(f"/me/messages/{message_id}/replyAll", payload)
    print(f"Reply sent to message {message_id[:30]}...")


def cmd_mail_unread(n="30"):
    """List unread emails."""
    params = {
        "$top": n,
        "$select": "id,subject,from,receivedDateTime,isRead,importance,hasAttachments",
        "$orderby": "receivedDateTime desc",
        "$filter": "isRead eq false",
    }
    data = graph_get("/me/messages", params=params)
    for m in data.get("value", []):
        dt = m["receivedDateTime"][:16].replace("T", " ")
        fr = m.get("from", {}).get("emailAddress", {}).get("name", "?")[:28]
        subj = (m.get("subject") or "(no subject)")[:60]
        att = "[A]" if m.get("hasAttachments") else "   "
        imp = "!" if m.get("importance") == "high" else " "
        msg_id = m.get("id", "")
        print(f"{imp} {dt}  {fr:28s}  {att} {subj}")
        print(f"  ID: {msg_id}")
    print(f"\n({len(data.get('value', []))} unread)")


def cmd_mail_search(query, n="10"):
    """Search emails."""
    cmd_mail_list(n=n, query=query)


# --- SAFE ATTACHMENT HANDLING ---
ALLOWED_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".csv", ".txt", ".rtf", ".odt", ".ods", ".odp",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".webp",
    ".zip", ".7z", ".rar", ".tar", ".gz",
    ".msg", ".eml", ".ics",
    ".json", ".xml", ".html", ".htm",
    ".mp4", ".mp3", ".wav",
}


def _safe_attachment_path(base_dir, raw_name):
    """Sanitize attachment filename: strip traversal, validate extension, confirm path is inside base_dir."""
    clean_name = os.path.basename(raw_name)
    clean_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', clean_name)
    if not clean_name or clean_name.startswith('.'):
        return None, "hidden or empty filename"
    ext = Path(clean_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return None, f"blocked extension: {ext}"
    target = (base_dir / clean_name).resolve()
    if not str(target).startswith(str(base_dir.resolve())):
        return None, "path traversal detected"
    return target, None


# --- MAIL ATTACHMENTS ---
def cmd_mail_attachments(message_id, save_dir=None):
    """List and optionally download attachments from an email."""
    atts = graph_get(f"/me/messages/{message_id}/attachments")
    attachments = atts.get("value", [])
    if not attachments:
        print("No attachments.")
        return

    for a in attachments:
        size_kb = a.get("size", 0) // 1024
        print(f"  {a['name']} ({size_kb}KB) — {a.get('contentType', '?')}")

    if save_dir:
        save_path = Path(save_dir).resolve()
        save_path.mkdir(parents=True, exist_ok=True)
        saved, skipped = 0, 0
        for a in attachments:
            if "contentBytes" not in a:
                print(f"  Skipped (no content): {a['name']}")
                skipped += 1
                continue
            file_path, reason = _safe_attachment_path(save_path, a["name"])
            if file_path is None:
                print(f"  BLOCKED: {a['name']} — {reason}", file=sys.stderr)
                skipped += 1
                continue
            with open(file_path, "wb") as f:
                f.write(base64.b64decode(a["contentBytes"]))
            print(f"  Saved: {file_path}")
            saved += 1
        print(f"\n{saved} saved, {skipped} skipped")
    else:
        print(f"\n({len(attachments)} attachments — add save_dir to download)")


# --- CALENDAR ---
def cmd_calendar_today():
    """Show today's events."""
    now = datetime.datetime.now(datetime.timezone.utc)
    start = now.replace(hour=0, minute=0, second=0).isoformat()
    end = now.replace(hour=23, minute=59, second=59).isoformat()
    _calendar_range(start, end, "Today")


def cmd_calendar_week():
    """Show this week's events."""
    now = datetime.datetime.now(datetime.timezone.utc)
    start = now.replace(hour=0, minute=0, second=0).isoformat()
    end = (now + datetime.timedelta(days=7)).replace(hour=23, minute=59).isoformat()
    _calendar_range(start, end, "Next 7 days")


def cmd_calendar_tomorrow():
    """Show tomorrow's events."""
    now = datetime.datetime.now(datetime.timezone.utc)
    start = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0).isoformat()
    end = (now + datetime.timedelta(days=1)).replace(hour=23, minute=59, second=59).isoformat()
    _calendar_range(start, end, "Tomorrow")


def _calendar_range(start, end, label):
    """Fetch events in a date range."""
    params = {
        "startDateTime": start,
        "endDateTime": end,
        "$top": "50",
        "$select": "subject,start,end,organizer,location,isAllDay,isCancelled,onlineMeeting",
        "$orderby": "start/dateTime",
    }
    data = graph_get("/me/calendarview", params=params)
    events = [e for e in data.get("value", []) if not e.get("isCancelled")]
    print(f"=== {label} ({len(events)} events) ===\n")
    for e in events:
        if e.get("isAllDay"):
            time_str = "ALL DAY   "
        else:
            s = e["start"]["dateTime"][11:16]
            en = e["end"]["dateTime"][11:16]
            time_str = f"{s}-{en}"
        org = e.get("organizer", {}).get("emailAddress", {}).get("name", "")[:25]
        loc = e.get("location", {}).get("displayName", "")
        teams = " [Teams]" if e.get("onlineMeeting") else ""
        subj = (e.get("subject") or "(no title)")[:50]
        print(f"  {time_str}  {subj}{teams}")
        if org:
            print(f"             Organizer: {org}" + (f" | {loc}" if loc else ""))
    if not events:
        print("  No events.")


def cmd_calendar_history(start_date, end_date, search_query=""):
    """Show past calendar events in a date range. Dates: YYYY-MM-DD."""
    start = f"{start_date}T00:00:00Z"
    end = f"{end_date}T23:59:59Z"
    params = {
        "startDateTime": start,
        "endDateTime": end,
        "$top": "200",
        "$select": "subject,start,end,organizer,attendees,location,isAllDay,isCancelled,onlineMeeting",
        "$orderby": "start/dateTime desc",
    }
    data = graph_get("/me/calendarview", params=params)
    events = [e for e in data.get("value", []) if not e.get("isCancelled")]

    if search_query:
        q = search_query.lower()
        events = [e for e in events if q in (e.get("subject") or "").lower()]

    print(f"=== Calendar History: {start_date} -> {end_date} ({len(events)} events) ===\n")
    results = []
    for e in events:
        s_dt = e["start"]["dateTime"][:16]
        e_dt = e["end"]["dateTime"][:16]
        date_str = s_dt[:10]
        time_str = f"{s_dt[11:16]}-{e_dt[11:16]}" if not e.get("isAllDay") else "ALL DAY"
        org = e.get("organizer", {}).get("emailAddress", {}).get("name", "")
        org_email = e.get("organizer", {}).get("emailAddress", {}).get("address", "")
        attendee_list = [a.get("emailAddress", {}).get("name", "") for a in e.get("attendees", [])]
        teams_link = "Teams" if e.get("onlineMeeting") else ""
        subj = e.get("subject") or "(no title)"

        try:
            s_time = datetime.datetime.fromisoformat(s_dt)
            e_time = datetime.datetime.fromisoformat(e_dt)
            dur_min = int((e_time - s_time).total_seconds() / 60)
            duration = f"{dur_min}min"
        except Exception:
            duration = "?"

        results.append({
            "date": date_str, "title": subj, "time": time_str,
            "organizer": org, "organizer_email": org_email,
            "attendees": attendee_list, "teams_link": teams_link, "duration": duration,
        })
        print(f"  {date_str}  {time_str:12s}  {subj[:50]}")
        if org:
            print(f"             {org} | {duration}" + (f" | {teams_link}" if teams_link else ""))

    if not events:
        print("  No events found.")
    print(f"\n---JSON---")
    print(json.dumps(results, ensure_ascii=False, indent=2))


def cmd_calendar_create(subject, start, end, body="", attendees="", teams="yes"):
    """Create a calendar event. Dates in ISO format: 2026-03-10T14:00:00"""
    event = {
        "subject": subject,
        "start": {"dateTime": start, "timeZone": TIMEZONE},
        "end": {"dateTime": end, "timeZone": TIMEZONE},
    }
    if body:
        event["body"] = {"contentType": "Text", "content": body}
    if attendees:
        event["attendees"] = [
            {"emailAddress": {"address": a.strip()}, "type": "required"}
            for a in attendees.split(",")
        ]
    is_teams = teams.lower() != "no"
    if is_teams:
        event["isOnlineMeeting"] = True
        event["onlineMeetingProvider"] = "teamsForBusiness"
    data = graph_post("/me/events", event)
    join_url = data.get("onlineMeeting", {}).get("joinUrl", "")
    print(f"Event created: {data.get('subject')}")
    print(f"When: {start} — {end.split('T')[-1] if 'T' in end else end}")
    if join_url:
        print(f"Teams link: {join_url}")
    print(f"ID: {data.get('id', '')[:30]}...")
    if is_teams and join_url:
        try:
            meetings = graph_get("/me/onlineMeetings",
                                 params={"$filter": f"JoinWebUrl eq '{join_url}'"})
            items = meetings.get("value", [])
            if items:
                meeting_id = items[0]["id"]
                _graph_patch(f"/me/onlineMeetings/{meeting_id}", {"recordAutomatically": True})
                print("Auto-recording + transcription: ENABLED")
            else:
                print("Warning: Could not find onlineMeeting to enable recording")
        except Exception as e:
            print(f"Warning: Could not enable auto-recording: {e}")


def cmd_calendar_update(event_id, field, value):
    """Update a calendar event field. Fields: subject, start, end, body, attendees (comma-sep), location."""
    payload = {}
    if field == "subject":
        payload["subject"] = value
    elif field == "start":
        payload["start"] = {"dateTime": value, "timeZone": TIMEZONE}
    elif field == "end":
        payload["end"] = {"dateTime": value, "timeZone": TIMEZONE}
    elif field == "body":
        payload["body"] = {"contentType": "Text", "content": value}
    elif field == "attendees":
        payload["attendees"] = [
            {"emailAddress": {"address": a.strip()}, "type": "required"}
            for a in value.split(",")
        ]
    elif field == "location":
        payload["location"] = {"displayName": value}
    else:
        print(f"ERROR: Unknown field '{field}'. Use: subject, start, end, body, attendees, location", file=sys.stderr)
        sys.exit(1)
    data = _graph_patch(f"/me/events/{event_id}", payload)
    print(f"Event updated: {field} = {value}")
    if data.get("id"):
        print(f"ID: {data['id'][:30]}...")


def cmd_calendar_respond(event_id, response, message=""):
    """Respond to a calendar invite. response: accept, tentative, decline."""
    valid = {"accept": "accept", "tentative": "tentativelyAccept", "decline": "decline"}
    action = valid.get(response.lower())
    if not action:
        print(f"ERROR: response must be accept, tentative, or decline", file=sys.stderr)
        sys.exit(1)
    payload = {"sendResponse": True}
    if message:
        payload["comment"] = message
    graph_post(f"/me/events/{event_id}/{action}", payload)
    print(f"Event {response}ed: {event_id[:30]}...")


def cmd_calendar_schedule(emails, start, end):
    """Check availability of people. emails: comma-separated. start/end: ISO datetime."""
    schedules = [e.strip() for e in emails.split(",")]
    payload = {
        "schedules": schedules,
        "startTime": {"dateTime": start, "timeZone": TIMEZONE},
        "endTime": {"dateTime": end, "timeZone": TIMEZONE},
        "availabilityViewInterval": 30,
    }
    data = graph_post("/me/calendar/getSchedule", payload)
    for s in data.get("value", []):
        email = s.get("scheduleId", "?")
        avail = s.get("availabilityView", "")
        items = s.get("scheduleItems", [])
        print(f"\n{email}:")
        print(f"  Availability: {avail}  (0=free, 1=tentative, 2=busy, 3=OOO, 4=working-elsewhere)")
        for item in items:
            subj = item.get("subject", "(no subject)")
            st = item.get("start", {}).get("dateTime", "")[:16]
            en = item.get("end", {}).get("dateTime", "")[:16]
            status = item.get("status", "")
            print(f"  {st} — {en}  [{status}] {subj}")


def cmd_calendar_events(start_date, end_date):
    """List calendar events in a date range (for conflict detection)."""
    params = {
        "$select": "id,subject,start,end,organizer,attendees,responseStatus,isAllDay",
        "$orderby": "start/dateTime",
        "$top": 50,
    }
    headers = get_headers()
    headers["Prefer"] = f'outlook.timezone="{TIMEZONE}"'
    url = f"{GRAPH_BASE}/me/calendarView?startDateTime={start_date}T00:00:00&endDateTime={end_date}T23:59:59"
    r = requests.get(url, headers=headers, params=params)
    if r.status_code in (401, 403):
        refresh_token()
        headers = get_headers()
        headers["Prefer"] = f'outlook.timezone="{TIMEZONE}"'
        r = requests.get(url, headers=headers, params=params)
    data = r.json()
    for ev in data.get("value", []):
        if ev.get("isAllDay"):
            continue
        st = ev["start"]["dateTime"][:16].replace("T", " ")
        en = ev["end"]["dateTime"][11:16]
        subj = ev.get("subject", "(no subject)")[:50]
        resp = ev.get("responseStatus", {}).get("response", "?")
        ev_id = ev.get("id", "")
        print(f"  {st}-{en}  [{resp:10s}] {subj}")
        print(f"    ID: {ev_id}")
    print(f"\n({len([e for e in data.get('value', []) if not e.get('isAllDay')])} events)")


# --- TEAMS ---
def cmd_teams_list():
    """List joined Teams."""
    data = graph_get("/me/joinedTeams", params={"$select": "id,displayName,description"})
    for t in data.get("value", []):
        desc = (t.get("description") or "")[:60]
        print(f"  {t['displayName']}")
        if desc:
            print(f"    {desc}")
    print(f"\n({len(data.get('value', []))} teams)")


def cmd_teams_channels(team_id):
    """List channels in a team."""
    data = graph_get(f"/teams/{team_id}/channels", params={"$select": "id,displayName,description"})
    for c in data.get("value", []):
        print(f"  {c['displayName']} — {c['id'][:20]}...")


def cmd_teams_messages(team_id, channel_id, n="10"):
    """Read recent messages from a Teams channel."""
    data = graph_get(f"/teams/{team_id}/channels/{channel_id}/messages",
                     params={"$top": n}, beta=True)
    for m in data.get("value", []):
        dt = (m.get("createdDateTime") or "")[:16].replace("T", " ")
        fr = m.get("from", {}).get("user", {}).get("displayName", "?")
        body = m.get("body", {}).get("content", "")
        body = re.sub(r'<[^>]+>', '', body).strip()[:100]
        if body:
            print(f"  {dt}  {fr[:25]:25s}  {body}")


def cmd_chats_list(n="15", hours="0"):
    """List recent chats. Optional hours filter."""
    params = {
        "$top": n,
        "$select": "id,topic,chatType,lastUpdatedDateTime",
    }
    h = int(hours)
    if h > 0:
        since = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M:%SZ")
        params["$filter"] = f"lastUpdatedDateTime gt {since}"
    data = graph_get("/me/chats", params=params)
    chats = data.get("value", [])
    member_cache = {}
    for c in chats:
        if c.get("chatType") == "oneOnOne":
            try:
                m_data = graph_get(f"/me/chats/{c['id']}/members")
                # Filter out self — uses /me displayName dynamically
                me_data = graph_get("/me", params={"$select": "displayName"})
                my_name = me_data.get("displayName", "").upper()
                others = [m.get("displayName", "?") for m in m_data.get("value", [])
                          if my_name not in (m.get("displayName", "") or "").upper()]
                member_cache[c["id"]] = others[0] if others else "?"
            except Exception:
                member_cache[c["id"]] = "?"
    for c in chats:
        dt = (c.get("lastUpdatedDateTime") or "")[:16].replace("T", " ")
        chat_type = c.get("chatType", "")
        if chat_type == "oneOnOne":
            name = member_cache.get(c["id"], "?")
            topic = f"[1:1] {name}"
        else:
            topic = c.get("topic") or f"({chat_type})"
        print(f"  {dt}  {topic[:60]}  {c['id']}")
    print(f"\n({len(chats)} chats)")


def cmd_chats_messages(chat_id, n="10"):
    """Read recent messages from a chat."""
    data = graph_get(f"/me/chats/{chat_id}/messages", params={"$top": n})
    for m in data.get("value", []):
        dt = (m.get("createdDateTime") or "")[:16].replace("T", " ")
        _from = m.get("from") or {}
        fr = (_from.get("user") or {}).get("displayName", "system")
        body = m.get("body", {}).get("content", "")
        body = re.sub(r'<[^>]+>', '', body).strip()[:120]
        if body:
            print(f"  {dt}  {fr[:25]:25s}  {body}")


def cmd_chats_send(chat_id, message):
    """Send a message to a chat."""
    data = graph_post(f"/me/chats/{chat_id}/messages", {
        "body": {"content": message}
    })
    print(f"Message sent (id: {data.get('id', '?')[:20]}...)")


def cmd_chats_find(user_email):
    """Find or create a 1:1 chat with a user by email."""
    headers = get_headers()
    headers["ConsistencyLevel"] = "eventual"
    r = requests.get(f"{GRAPH_BASE}/users", headers=headers, params={
        "$filter": f"mail eq '{user_email}'",
        "$select": "id,displayName,mail",
    })
    if r.status_code == 401:
        refresh_token()
        headers = get_headers()
        headers["ConsistencyLevel"] = "eventual"
        r = requests.get(f"{GRAPH_BASE}/users", headers=headers, params={
            "$filter": f"mail eq '{user_email}'",
            "$select": "id,displayName,mail",
        })
    users = r.json().get("value", [])
    if not users:
        r = requests.get(f"{GRAPH_BASE}/users", headers=headers, params={
            "$filter": f"startswith(mail,'{user_email.split('@')[0]}')",
            "$select": "id,displayName,mail",
        })
        users = r.json().get("value", [])
    if not users:
        print(f"ERROR: User not found: {user_email}", file=sys.stderr)
        sys.exit(1)

    user_id = users[0]["id"]
    my_data = graph_get("/me", params={"$select": "id"})
    my_id = my_data["id"]

    data = graph_post("/chats", {
        "chatType": "oneOnOne",
        "members": [
            {
                "@odata.type": "#microsoft.graph.aadUserConversationMember",
                "roles": ["owner"],
                "user@odata.bind": f"https://graph.microsoft.com/v1.0/users/{user_id}",
            },
            {
                "@odata.type": "#microsoft.graph.aadUserConversationMember",
                "roles": ["owner"],
                "user@odata.bind": f"https://graph.microsoft.com/v1.0/users/{my_id}",
            },
        ],
    })
    chat_id = data.get("id", "")
    print(f"Chat with {users[0].get('displayName', user_email)}: {chat_id[:40]}...")
    return chat_id


def cmd_chats_card(chat_id, title, body_json):
    """Send an adaptive card to a chat."""
    card = {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": json.loads(body_json),
    }
    data = graph_post(f"/me/chats/{chat_id}/messages", {
        "body": {
            "contentType": "html",
            "content": '<attachment id="card1"></attachment>',
        },
        "attachments": [{
            "id": "card1",
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": json.dumps(card),
        }],
    }, beta=True)
    print(f"Card sent: {title} (id: {data.get('id', '?')[:20]}...)")


# --- SHAREPOINT ---
def cmd_sharepoint_sites(query=None):
    """List or search SharePoint sites."""
    if query:
        data = graph_post("/search/query", {
            "requests": [{
                "entityTypes": ["site"],
                "query": {"queryString": query},
                "from": 0, "size": 10,
            }]
        })
        hits = data.get("value", [{}])[0].get("hitsContainers", [{}])[0].get("hits", [])
        for h in hits:
            res = h.get("resource", {})
            print(f"  {res.get('displayName', '?')}")
            print(f"    {res.get('webUrl', '')}")
        print(f"\n({len(hits)} sites)")
    else:
        data = graph_get("/sites/root", params={"$select": "displayName,webUrl"})
        print(f"  {data.get('displayName', '?')}")
        print(f"    {data.get('webUrl', '')}")
        print("\nTip: use 'sharepoint sites <query>' to search specific sites")


# --- PRESENCE ---
def cmd_presence():
    """Get your current presence status."""
    data = graph_get("/me/presence", beta=True)
    print(f"Status: {data.get('availability', '?')}")
    print(f"Activity: {data.get('activity', '?')}")


def cmd_presence_set(availability, activity=None):
    """Set your presence status."""
    if not activity:
        activity = availability
    graph_post("/me/presence/setUserPreferredPresence", {
        "availability": availability,
        "activity": activity,
        "expirationDuration": "PT8H",
    }, beta=True)
    print(f"Presence set: {availability} ({activity}) — expires in 8h")


# --- PEOPLE / USERS ---
def cmd_people_search(query):
    """Search people in the directory."""
    headers = get_headers()
    headers["ConsistencyLevel"] = "eventual"
    params = {
        "$filter": f"startswith(displayName,'{query}') or startswith(mail,'{query}')",
        "$top": "10",
        "$select": "displayName,mail,jobTitle,department,officeLocation",
        "$count": "true",
    }
    r = requests.get(f"{GRAPH_BASE}/users", headers=headers, params=params)
    if r.status_code == 401:
        refresh_token()
        headers = get_headers()
        headers["ConsistencyLevel"] = "eventual"
        r = requests.get(f"{GRAPH_BASE}/users", headers=headers, params=params)
    if r.status_code != 200:
        err = r.json().get("error", {})
        print(f"ERROR {r.status_code}: {err.get('code', '')} — {err.get('message', '')}", file=sys.stderr)
        sys.exit(1)
    data = r.json()
    for p in data.get("value", []):
        print(f"  {p.get('displayName', '?')}")
        print(f"    {p.get('mail', 'N/A')} — {p.get('jobTitle', '')} | {p.get('department', '')}")
    print(f"\n({len(data.get('value', []))} results)")


# --- FILE UPLOAD ---
def cmd_upload(file_path, filename=None):
    """Upload a file to SharePoint and return the web URL."""
    if not UPLOAD_DRIVE_ID or not UPLOAD_FOLDER_ID:
        print("ERROR: Upload not configured. Set upload.drive_id and upload.folder_id in config.json", file=sys.stderr)
        sys.exit(1)
    path = Path(file_path)
    if not path.exists():
        print(f"ERROR: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)
    fname = filename or path.name
    with open(path, "rb") as f:
        content = f.read()

    headers = get_headers()
    ext = path.suffix.lower()
    ct_map = {".html": "text/html", ".pdf": "application/pdf",
              ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
              ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
              ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
              ".png": "image/png", ".jpg": "image/jpeg", ".json": "application/json"}
    headers["Content-Type"] = ct_map.get(ext, "application/octet-stream")

    url = f"{GRAPH_BASE}/drives/{UPLOAD_DRIVE_ID}/items/{UPLOAD_FOLDER_ID}:/{fname}:/content"
    r = requests.put(url, headers=headers, data=content)
    if r.status_code == 401:
        refresh_token()
        headers = get_headers()
        headers["Content-Type"] = ct_map.get(ext, "application/octet-stream")
        r = requests.put(url, headers=headers, data=content)
    if r.status_code not in (200, 201):
        err = r.json().get("error", {})
        print(f"ERROR {r.status_code}: {err.get('code', '')} — {err.get('message', '')}", file=sys.stderr)
        sys.exit(1)
    item = r.json()
    web_url = item.get("webUrl", "")
    print(f"Uploaded: {fname}")
    print(f"URL: {web_url}")
    return web_url


# --- SEARCH ---
def cmd_search(entity_type, query):
    """Search using Microsoft Search API. entity_type: message, driveItem, site"""
    valid_types = ["message", "driveItem", "site"]
    if entity_type not in valid_types:
        print(f"ERROR: entity_type must be one of: {', '.join(valid_types)}", file=sys.stderr)
        sys.exit(1)
    data = graph_post("/search/query", {
        "requests": [{
            "entityTypes": [entity_type],
            "query": {"queryString": query},
            "from": 0, "size": 10,
        }]
    })
    hits = data.get("value", [{}])[0].get("hitsContainers", [{}])[0].get("hits", [])
    for h in hits:
        res = h.get("resource", {})
        if entity_type == "message":
            print(f"  {res.get('subject', '?')}")
            print(f"    From: {res.get('from', {}).get('emailAddress', {}).get('name', '?')} — {res.get('receivedDateTime', '')[:16]}")
        elif entity_type == "driveItem":
            print(f"  {res.get('name', '?')}")
            print(f"    {res.get('webUrl', '')}")
        elif entity_type == "site":
            print(f"  {res.get('displayName', '?')}")
            print(f"    {res.get('webUrl', '')}")
    print(f"\n({len(hits)} results)")


# --- PLANNER ---
def cmd_planner_plans():
    """List your Planner plans with buckets."""
    data = graph_get("/me/planner/plans")
    plans = data.get("value", [])
    for p in plans:
        pid = p["id"]
        print(f"\n  Plan: {p.get('title', '?')}")
        print(f"  ID:   {pid}")
        buckets = graph_get(f"/planner/plans/{pid}/buckets").get("value", [])
        if buckets:
            print(f"  Buckets:")
            for b in buckets:
                print(f"    - {b.get('name', '?')} (id: {b['id']})")
        tasks = graph_get(f"/planner/plans/{pid}/tasks", params={"$select": "id,percentComplete"}).get("value", [])
        done = sum(1 for t in tasks if t.get("percentComplete") == 100)
        print(f"  Tasks: {len(tasks)} total, {done} done, {len(tasks) - done} open")
    print(f"\n({len(plans)} plans)")


def cmd_planner_tasks(*args):
    """List Planner tasks. Optional: plan_id to filter by plan."""
    plan_id = args[0] if args else None
    if plan_id:
        data = graph_get(f"/planner/plans/{plan_id}/tasks")
    else:
        data = graph_get("/me/planner/tasks")
    tasks = data.get("value", [])
    pri_map = {1: "Urgent", 3: "Important", 5: "Medium", 9: "Low"}
    for t in tasks:
        pct = t.get("percentComplete", 0)
        status = "Done" if pct == 100 else f"{pct}%"
        due = (t.get("dueDateTime") or "no due")[:10]
        pri = pri_map.get(t.get("priority", 5), "Medium")
        print(f"  [{status:>4}] {t.get('title', '?')}")
        print(f"         ID: {t['id']} | Due: {due} | {pri} | Bucket: {t.get('bucketId', '?')[:8]}...")
    print(f"\n({len(tasks)} tasks)")


def cmd_planner_task_create(*args):
    """Create a Planner task."""
    if len(args) < 2:
        print("Usage: planner create <plan_id> <title> [bucket_id] [due_date] [priority]")
        sys.exit(1)
    plan_id, title = args[0], args[1]
    bucket_id = args[2] if len(args) > 2 and args[2] != "-" else None
    due_date = args[3] if len(args) > 3 and args[3] != "-" else None
    priority = int(args[4]) if len(args) > 4 else 5

    body = {"planId": plan_id, "title": title, "priority": priority}
    if bucket_id:
        body["bucketId"] = bucket_id
    if due_date:
        body["dueDateTime"] = f"{due_date}T00:00:00Z" if "T" not in due_date else due_date

    result = graph_post("/planner/tasks", body)
    print(f"Created task: {result.get('title')}")
    print(f"  ID: {result['id']}")


def cmd_planner_task_update(*args):
    """Update a Planner task."""
    if len(args) < 3:
        print("Usage: planner update <task_id> <field> <value>")
        sys.exit(1)
    task_id, field, value = args[0], args[1], args[2]
    task = graph_get(f"/planner/tasks/{task_id}", params={"$select": "id"})
    etag = task.get("@odata.etag", "")
    field_map = {
        "title": ("title", value),
        "percent": ("percentComplete", int(value)),
        "priority": ("priority", int(value)),
        "due": ("dueDateTime", f"{value}T00:00:00Z" if "T" not in value else value),
        "bucket": ("bucketId", value),
    }
    if field not in field_map:
        print(f"Unknown field: {field}. Use: title, percent, priority, due, bucket")
        sys.exit(1)
    api_field, api_value = field_map[field]
    _graph_patch(f"/planner/tasks/{task_id}", {api_field: api_value}, etag=etag)
    print(f"Updated task {task_id}: {field} = {value}")


def cmd_planner_task_done(*args):
    """Mark a task as done."""
    if not args:
        print("Usage: planner done <task_id>")
        sys.exit(1)
    task_id = args[0]
    task = graph_get(f"/planner/tasks/{task_id}", params={"$select": "id,title"})
    etag = task.get("@odata.etag", "")
    _graph_patch(f"/planner/tasks/{task_id}", {"percentComplete": 100}, etag=etag)
    print(f"Marked as done: {task.get('title', task_id)}")


def cmd_planner_task_delete(*args):
    """Delete a Planner task."""
    if not args:
        print("Usage: planner delete <task_id>")
        sys.exit(1)
    task_id = args[0]
    task = graph_get(f"/planner/tasks/{task_id}", params={"$select": "id,title"})
    etag = task.get("@odata.etag", "")
    _graph_delete(f"/planner/tasks/{task_id}", etag=etag)
    print(f"Deleted task: {task.get('title', task_id)}")


def cmd_planner_bucket_create(*args):
    """Create a bucket in a plan."""
    if len(args) < 2:
        print("Usage: planner bucket-create <plan_id> <name>")
        sys.exit(1)
    result = graph_post("/planner/buckets", {"planId": args[0], "name": args[1]})
    print(f"Created bucket: {result.get('name')} (id: {result['id']})")


def cmd_planner_plan_create(*args):
    """Create a new Planner plan."""
    if len(args) < 2:
        print("Usage: planner plan-create <group_id> <title>")
        sys.exit(1)
    result = graph_post("/planner/plans", {"owner": args[0], "title": args[1]})
    print(f"Created plan: {result.get('title')} (id: {result['id']})")


# --- BRIEFING ---
def cmd_briefing():
    """Daily briefing: unread emails + today's events + presence."""
    print("=" * 60)
    print("  DAILY BRIEFING")
    print("=" * 60)

    data = graph_get("/me/mailFolders/inbox", params={"$select": "unreadItemCount,totalItemCount"})
    print(f"\nInbox: {data.get('unreadItemCount', '?')} unread / {data.get('totalItemCount', '?')} total")

    params = {
        "$top": "5",
        "$filter": "isRead eq false",
        "$select": "subject,from,receivedDateTime,importance",
        "$orderby": "receivedDateTime desc",
    }
    data = graph_get("/me/messages", params=params)
    for m in data.get("value", []):
        dt = m["receivedDateTime"][11:16]
        fr = m.get("from", {}).get("emailAddress", {}).get("name", "?")[:28]
        imp = "!" if m.get("importance") == "high" else " "
        print(f"  {imp} {dt}  {fr:28s}  {(m.get('subject') or '(no subject)')[:50]}")

    print()
    cmd_calendar_today()

    try:
        data = graph_get("/me/presence", beta=True)
        print(f"\nPresence: {data.get('availability', '?')} ({data.get('activity', '?')})")
    except SystemExit:
        pass


# --- ARCHIVE ---
PROJECT_SUBDIRS = ["Emails", "Meetings", "Teams", "Files", "Notes", "Calendar"]


def _slugify(text):
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')


def _is_project_dir(d):
    return any((d / sub).is_dir() for sub in PROJECT_SUBDIRS)


def _update_index():
    index = {"projects": {}, "updated": datetime.datetime.now().isoformat()}
    if ARCHIVE_DIR.exists():
        for topic_dir in sorted(ARCHIVE_DIR.iterdir()):
            if topic_dir.is_dir() and _is_project_dir(topic_dir):
                counts = {}
                for sub in PROJECT_SUBDIRS:
                    sub_dir = topic_dir / sub
                    if sub_dir.exists():
                        counts[sub] = len([x for x in sub_dir.iterdir() if x.name not in ('.gitkeep', 'README.md')])
                    else:
                        counts[sub] = 0
                index["projects"][topic_dir.name] = counts
    with open(ARCHIVE_DIR / "_projects.json", "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)


def cmd_mail_save(message_id, topic):
    """Save an email with attachments to the local archive under a topic."""
    data = graph_get(f"/me/messages/{message_id}")
    topic_slug = _slugify(topic)
    date = data["receivedDateTime"][:10]
    subject = data.get("subject", "no-subject")
    subject_slug = _slugify(subject)[:60]
    base_name = f"{date}_{subject_slug}"
    email_dir = ARCHIVE_DIR / topic_slug / "Emails" / base_name
    if email_dir.exists():
        counter = 2
        while (ARCHIVE_DIR / topic_slug / "Emails" / f"{base_name}_{counter}").exists():
            counter += 1
        email_dir = ARCHIVE_DIR / topic_slug / "Emails" / f"{base_name}_{counter}"
    email_dir.mkdir(parents=True, exist_ok=True)
    project_dir = ARCHIVE_DIR / topic_slug
    for sub in PROJECT_SUBDIRS:
        (project_dir / sub).mkdir(parents=True, exist_ok=True)

    readme_path = project_dir / "README.md"
    if not readme_path.exists():
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(f"# {topic}\n\nProject folder created {datetime.datetime.now().strftime('%Y-%m-%d')}.\n")

    fr = data.get("from", {}).get("emailAddress", {})
    to_list = [r["emailAddress"] for r in data.get("toRecipients", [])]
    cc_list = [r["emailAddress"] for r in data.get("ccRecipients", [])]
    metadata = {
        "id": message_id, "subject": data.get("subject", ""),
        "from": fr, "to": to_list, "cc": cc_list,
        "date": data["receivedDateTime"],
        "importance": data.get("importance", "normal"),
        "hasAttachments": data.get("hasAttachments", False),
        "topic": topic, "archived": datetime.datetime.now().isoformat(),
    }
    with open(email_dir / "Metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    body = data.get("body", {})
    if body.get("contentType") == "html":
        html_content = body.get("content", "")
        with open(email_dir / "Body.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        text = re.sub(r'<[^>]+>', '', html_content)
        text = re.sub(r'\n\s*\n', '\n\n', text).strip()
        with open(email_dir / "Body.txt", "w", encoding="utf-8") as f:
            f.write(text)
    else:
        with open(email_dir / "Body.txt", "w", encoding="utf-8") as f:
            f.write(body.get("content", ""))

    if data.get("hasAttachments"):
        atts = graph_get(f"/me/messages/{message_id}/attachments")
        att_dir = email_dir / "attachments"
        att_dir.mkdir(exist_ok=True)
        for a in atts.get("value", []):
            if "contentBytes" not in a:
                continue
            file_path, reason = _safe_attachment_path(att_dir, a["name"])
            if file_path is None:
                print(f"  BLOCKED: {a['name']} — {reason}", file=sys.stderr)
                continue
            with open(file_path, "wb") as f:
                f.write(base64.b64decode(a["contentBytes"]))
            print(f"  Attachment: {file_path.name}")

    _update_index()
    print(f"Saved to: {email_dir}")
    print(f"  Topic: {topic} ({topic_slug})")
    print(f"  Subject: {data.get('subject', '')}")
    print(f"  From: {fr.get('name', '')} <{fr.get('address', '')}>")


def cmd_archive_search(query):
    """Search archived content by keyword."""
    query_lower = query.lower()
    results = []
    if not ARCHIVE_DIR.exists():
        print("No archive found.")
        return
    for topic_dir in sorted(ARCHIVE_DIR.iterdir()):
        if not topic_dir.is_dir() or not _is_project_dir(topic_dir):
            continue
        emails_dir = topic_dir / "Emails"
        if not emails_dir.exists():
            continue
        for email_dir in sorted(emails_dir.iterdir()):
            if not email_dir.is_dir():
                continue
            meta_path = email_dir / "Metadata.json"
            if not meta_path.exists():
                continue
            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f)
            match = False
            if query_lower in (meta.get("subject", "")).lower():
                match = True
            if query_lower in (meta.get("from", {}).get("name", "")).lower():
                match = True
            if query_lower in (meta.get("from", {}).get("address", "")).lower():
                match = True
            if not match:
                body_path = email_dir / "Body.txt"
                if body_path.exists():
                    if query_lower in body_path.read_text(encoding="utf-8").lower():
                        match = True
            if match:
                results.append({
                    "topic": topic_dir.name, "path": str(email_dir),
                    "subject": meta.get("subject", ""),
                    "from": meta.get("from", {}).get("name", "?"),
                    "date": meta.get("date", "")[:10],
                })
    if results:
        for r in results:
            print(f"  [{r['topic']}] {r['date']}  {r['from'][:25]:25s}  {r['subject'][:50]}")
        print(f"\n({len(results)} results)")
    else:
        print(f"No results for '{query}'.")


def cmd_archive_list(topic=None):
    """List archived topics or items within a topic."""
    if not ARCHIVE_DIR.exists():
        print("No archive found.")
        return
    if topic:
        topic_slug = _slugify(topic)
        topic_dir = ARCHIVE_DIR / topic_slug
        if not topic_dir.exists():
            print(f"Topic not found: {topic} ({topic_slug})")
            return
        print(f"=== {topic_slug} ===\n")
        for sub in PROJECT_SUBDIRS:
            sub_dir = topic_dir / sub
            if sub_dir.exists():
                items = sorted([x for x in sub_dir.iterdir() if x.name != '.gitkeep'])
                if items:
                    print(f"  {sub}/ ({len(items)} items)")
                    for item in items:
                        if item.is_dir():
                            meta_path = item / "Metadata.json"
                            if meta_path.exists():
                                with open(meta_path, encoding="utf-8") as f:
                                    meta = json.load(f)
                                print(f"    {item.name}  — {meta.get('subject', '')[:50]}")
                            else:
                                print(f"    {item.name}")
                        else:
                            print(f"    {item.name}")
    else:
        projects = []
        for d in sorted(ARCHIVE_DIR.iterdir()):
            if d.is_dir() and _is_project_dir(d):
                counts = {}
                for sub in PROJECT_SUBDIRS:
                    sub_dir = d / sub
                    if sub_dir.exists():
                        counts[sub] = len([x for x in sub_dir.iterdir() if x.name not in ('.gitkeep', 'README.md')])
                    else:
                        counts[sub] = 0
                total = sum(counts.values())
                projects.append((d.name, counts, total))
        if projects:
            for name, counts, total in projects:
                parts = [f"{k}:{v}" for k, v in counts.items() if v > 0]
                print(f"  {name:30s}  {total} items  ({', '.join(parts) if parts else 'empty'})")
            print(f"\n({len(projects)} projects)")
        else:
            print("No projects yet. Save emails with: mail save <id> <project>")


def cmd_chat_save(chat_id, project, n="50"):
    """Save Teams chat messages to a project folder."""
    data = graph_get(f"/me/chats/{chat_id}/messages", params={"$top": n})
    messages = data.get("value", [])
    if not messages:
        print("No messages found.")
        return
    project_slug = _slugify(project)
    project_dir = ARCHIVE_DIR / project_slug
    chat_info = graph_get(f"/me/chats/{chat_id}", params={"$select": "id,topic,chatType,lastUpdatedDateTime"})
    chat_topic = chat_info.get("topic") or chat_info.get("chatType", "chat")
    chat_slug = _slugify(chat_topic)[:40]
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    chat_dir = project_dir / "Teams" / f"{date}_{chat_slug}"
    if chat_dir.exists():
        counter = 2
        while (project_dir / "Teams" / f"{date}_{chat_slug}_{counter}").exists():
            counter += 1
        chat_dir = project_dir / "Teams" / f"{date}_{chat_slug}_{counter}"
    chat_dir.mkdir(parents=True, exist_ok=True)
    for sub in PROJECT_SUBDIRS:
        (project_dir / sub).mkdir(parents=True, exist_ok=True)

    participants = set()
    for m in messages:
        _from = m.get("from") or {}
        fr = (_from.get("user") or {}).get("displayName")
        if fr:
            participants.add(fr)

    metadata = {
        "chat_id": chat_id, "topic": chat_topic,
        "chat_type": chat_info.get("chatType", "?"),
        "participants": sorted(participants), "message_count": len(messages),
        "date_range": {
            "from": messages[-1].get("createdDateTime", "")[:16] if messages else "",
            "to": messages[0].get("createdDateTime", "")[:16] if messages else "",
        },
        "project": project, "archived": datetime.datetime.now().isoformat(),
    }
    with open(chat_dir / "Metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    lines = []
    for m in reversed(messages):
        dt = (m.get("createdDateTime") or "")[:16].replace("T", " ")
        _from = m.get("from") or {}
        fr = (_from.get("user") or {}).get("displayName", "system")
        body = m.get("body", {}).get("content", "")
        body = re.sub(r'<[^>]+>', '', body).strip()
        if body:
            lines.append(f"[{dt}] {fr}: {body}")
    with open(chat_dir / "Messages.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    _update_index()
    print(f"Saved to: {chat_dir}")
    print(f"  Project: {project} ({project_slug})")
    print(f"  Messages: {len(messages)}")
    print(f"  Participants: {', '.join(sorted(participants))}")


# === CLI ROUTER ===

COMMANDS = {
    "auth login":       (cmd_auth_login, []),
    "auth status":      (cmd_auth_status, []),
    "briefing":         (cmd_briefing, []),
    "mail list":        (cmd_mail_list, ["n?"]),
    "mail read":        (cmd_mail_read, ["message_id"]),
    "mail send":        (cmd_mail_send, ["to", "subject", "body"]),
    "mail reply":       (cmd_mail_reply, ["message_id", "body"]),
    "mail unread":      (cmd_mail_unread, ["n?"]),
    "mail search":      (cmd_mail_search, ["query", "n?"]),
    "mail attachments": (cmd_mail_attachments, ["message_id", "save_dir?"]),
    "mail save":        (cmd_mail_save, ["message_id", "topic"]),
    "archive search":   (cmd_archive_search, ["query"]),
    "archive list":     (cmd_archive_list, ["topic?"]),
    "chat save":        (cmd_chat_save, ["chat_id", "project", "n?"]),
    "calendar today":   (cmd_calendar_today, []),
    "calendar tomorrow":(cmd_calendar_tomorrow, []),
    "calendar week":    (cmd_calendar_week, []),
    "calendar history": (cmd_calendar_history, ["start_date", "end_date", "search_query?"]),
    "calendar create":  (cmd_calendar_create, ["subject", "start", "end", "body?", "attendees?", "teams?"]),
    "calendar update":  (cmd_calendar_update, ["event_id", "field", "value"]),
    "calendar respond": (cmd_calendar_respond, ["event_id", "response", "message?"]),
    "calendar schedule":(cmd_calendar_schedule, ["emails", "start", "end"]),
    "calendar events":  (cmd_calendar_events, ["start_date", "end_date"]),
    "teams list":       (cmd_teams_list, []),
    "teams channels":   (cmd_teams_channels, ["team_id"]),
    "teams messages":   (cmd_teams_messages, ["team_id", "channel_id", "n?"]),
    "chats list":       (cmd_chats_list, ["n?"]),
    "chats messages":   (cmd_chats_messages, ["chat_id", "n?"]),
    "chats send":       (cmd_chats_send, ["chat_id", "message"]),
    "chats find":       (cmd_chats_find, ["user_email"]),
    "chats card":       (cmd_chats_card, ["chat_id", "title", "body_json"]),
    "sharepoint sites": (cmd_sharepoint_sites, ["query?"]),
    "presence":         (cmd_presence, []),
    "presence set":     (cmd_presence_set, ["availability", "activity?"]),
    "people search":    (cmd_people_search, ["query"]),
    "upload":           (cmd_upload, ["file_path", "filename?"]),
    "search":           (cmd_search, ["entity_type", "query"]),
    "planner plans":    (cmd_planner_plans, []),
    "planner tasks":    (cmd_planner_tasks, ["plan_id?"]),
    "planner create":   (cmd_planner_task_create, ["plan_id", "title", "bucket_id?", "due_date?", "priority?"]),
    "planner update":   (cmd_planner_task_update, ["task_id", "field", "value"]),
    "planner done":     (cmd_planner_task_done, ["task_id"]),
    "planner delete":   (cmd_planner_task_delete, ["task_id"]),
    "planner bucket-create": (cmd_planner_bucket_create, ["plan_id", "name"]),
    "planner plan-create":   (cmd_planner_plan_create, ["group_id", "title"]),
}


def main():
    args = sys.argv[1:]
    if not args:
        print("M365 Assistant — Microsoft Graph CLI\n")
        print("Commands:")
        for cmd, (fn, params) in sorted(COMMANDS.items()):
            param_str = " ".join(f"<{p.rstrip('?')}>" if not p.endswith("?") else f"[{p.rstrip('?')}]" for p in params)
            print(f"  {cmd} {param_str}")
        return

    cmd_key = args[0] if len(args) == 1 else f"{args[0]} {args[1]}"
    if cmd_key not in COMMANDS and args[0] in [k.split()[0] for k in COMMANDS]:
        if args[0] in COMMANDS:
            cmd_key = args[0]
        else:
            print(f"Unknown subcommand. Available for '{args[0]}':")
            for k in COMMANDS:
                if k.startswith(args[0]):
                    print(f"  {k}")
            return

    if cmd_key not in COMMANDS:
        print(f"Unknown command: {cmd_key}")
        return

    fn, param_spec = COMMANDS[cmd_key]
    cmd_args = args[len(cmd_key.split()):]
    required = [p for p in param_spec if not p.endswith("?")]
    if len(cmd_args) < len(required):
        print(f"Usage: {cmd_key} {' '.join(f'<{p}>' for p in required)}")
        return

    fn(*cmd_args[:len(param_spec)])


if __name__ == "__main__":
    main()
