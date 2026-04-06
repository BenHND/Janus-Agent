# Deep Links Guide - Opening SaaS Applications Directly

**TICKET-BIZ-003: Generic Deep Linker**

This guide explains how to use Janus to open SaaS applications directly using deep links, bypassing browser dialogs and intermediate steps.

## Overview

The Generic Deep Linker allows Janus to open applications like Zoom, Spotify, Notion, Slack, and many others using native URL schemes or web fallbacks. This provides a seamless experience by:

- **Direct opening**: Launch directly into meetings, tracks, pages, etc.
- **No browser dialogs**: Avoid "Open in app?" prompts
- **Cross-platform**: Works on macOS, Windows, and Linux
- **Extensible**: Easy to add new applications via JSON registry

## Supported Applications

| Application | Description | Example URL Scheme |
|------------|-------------|-------------------|
| **Zoom** | Video conferencing meetings | `zoommtg://zoom.us/join?confno={id}` |
| **Notion** | Workspace pages | `notion://www.notion.so/{slug}` |
| **Spotify** | Music tracks, albums, playlists | `spotify:{type}:{id}` |
| **Slack** | Team channels and DMs | `slack://channel?team={team_id}&id={channel_id}` |
| **Microsoft Teams** | Meetings and chats | `msteams:/l/meetup-join/{id}` |
| **Jira** | Issues and boards | `jira://issue/{id}` |
| **Trello** | Boards and cards | `trello://card/{id}` |
| **Figma** | Design files | `figma://file/{id}` |
| **Discord** | Servers and channels | `discord://discord.com/channels/{server_id}/{channel_id}` |
| **GitHub** | Repositories and issues | `github://github.com/{owner}/{repo}` |
| **VS Code** | Open workspace and files | `vscode://file/{path}` |
| **Calendar** | Calendar events (macOS/iOS) | `x-apple-calevent://{event_id}` |

## Usage Examples

### Voice Commands

Simply speak naturally to Janus:

```
"Lance le call Zoom 123-456-789"
"Open Zoom meeting 123-456-789"

"Ouvre la page Notion My-Project"
"Open Notion page My-Project-123abc"

"Joue la track Spotify 3n3Ppam7vgaVa1iaRUc9Lp"
"Play Spotify track 3n3Ppam7vgaVa1iaRUc9Lp"

"Va sur le channel Slack C456DEF"
"Open Slack channel C456DEF with team T123ABC"
```

### Programmatic Usage

#### Python API

```python
from janus.os.app_deep_links import DeepLinkHandler

handler = DeepLinkHandler()

# Open Zoom meeting
handler.open_deep_link("zoom", {"id": "123-456-789"})

# Open Spotify track
handler.open_deep_link("spotify", {
    "type": "track",
    "id": "3n3Ppam7vgaVa1iaRUc9Lp"
})

# Open Notion page
handler.open_deep_link("notion", {"slug": "My-Page-123abc"})

# Open Slack channel
handler.open_deep_link("slack", {
    "team_id": "T123ABC",
    "channel_id": "C456DEF"
})

# Use web fallback if native app not installed
handler.open_deep_link("zoom", {"id": "123"}, use_web_fallback=True)
```

#### Agent Action (JSON)

For direct agent execution:

```json
{
  "module": "system",
  "action": "open_deep_link",
  "args": {
    "app": "zoom",
    "args": {"id": "123-456-789"}
  }
}
```

With web fallback:

```json
{
  "module": "system",
  "action": "open_deep_link",
  "args": {
    "app": "notion",
    "args": {"slug": "My-Page-123abc"},
    "use_web_fallback": true
  }
}
```

## Application-Specific Details

### Zoom

**Required arguments:**
- `id`: Meeting ID (can include dashes)

**Examples:**
```python
handler.open_deep_link("zoom", {"id": "123-456-789"})
handler.open_deep_link("zoom", {"id": "123456789"})
```

**Voice commands:**
- "Lance le call Zoom 123-456-789"
- "Open Zoom meeting 987654321"
- "Join Zoom 555-444-333"

### Spotify

**Required arguments:**
- `type`: Content type (`track`, `album`, `playlist`, `artist`)
- `id`: Spotify ID

**Examples:**
```python
# Open track
handler.open_deep_link("spotify", {
    "type": "track",
    "id": "3n3Ppam7vgaVa1iaRUc9Lp"
})

# Open album
handler.open_deep_link("spotify", {
    "type": "album",
    "id": "1DFixLWuPkv3KT3TnV35m3"
})

# Open playlist
handler.open_deep_link("spotify", {
    "type": "playlist",
    "id": "37i9dQZF1DXcBWIGoYBM5M"
})
```

**Voice commands:**
- "Play Spotify track 3n3Ppam7vgaVa1iaRUc9Lp"
- "Open Spotify playlist 37i9dQZF1DXcBWIGoYBM5M"

### Notion

**Required arguments:**
- `slug`: Page slug or ID

**Examples:**
```python
handler.open_deep_link("notion", {"slug": "My-Page-123abc"})
handler.open_deep_link("notion", {"slug": "myworkspace/page-id-123"})
```

**Voice commands:**
- "Ouvre la page Notion My-Project"
- "Open Notion page Team-Meeting-Notes"

### Slack

**Required arguments:**
- `team_id`: Team/workspace ID (starts with `T`)
- `channel_id`: Channel or DM ID (starts with `C` or `D`)

**Examples:**
```python
# Open channel
handler.open_deep_link("slack", {
    "team_id": "T123ABC",
    "channel_id": "C456DEF"
})

# Open DM
handler.open_deep_link("slack", {
    "team_id": "T123ABC",
    "channel_id": "D789GHI"
})
```

### Microsoft Teams

**Required arguments:**
- `id`: Meeting join ID

**Examples:**
```python
handler.open_deep_link("teams", {"id": "19%3ameeting_abc123"})
```

### Jira

**Required arguments:**
- `id`: Issue key (e.g., `PROJ-123`)

**Optional arguments:**
- `domain`: Your Atlassian domain (for web fallback)

**Examples:**
```python
handler.open_deep_link("jira", {"id": "PROJ-123"})

# With custom domain for web fallback
handler.open_deep_link("jira", {
    "id": "PROJ-123",
    "domain": "mycompany"
}, use_web_fallback=True)
```

## Adding New Applications

You can extend the deep link registry by editing `janus/resources/deep_links.json`:

```json
{
  "apps": {
    "myapp": {
      "name": "My App",
      "description": "Description of what My App does",
      "url_scheme": "myapp://open?id={id}",
      "web_fallback": "https://myapp.com/open/{id}",
      "examples": [
        "myapp://open?id=123"
      ]
    }
  }
}
```

**Field descriptions:**
- `name`: Human-readable app name
- `description`: Brief description
- `url_scheme`: Template for native URL scheme (use `{param}` for variables)
- `web_fallback`: Template for web URL (optional, use `null` if not available)
- `examples`: Sample URLs for reference

**Required parameters** are denoted by `{param}` in the templates. When calling `open_deep_link()`, provide these as a dictionary.

## Platform Support

### macOS
Uses the `open` command to launch URLs. Supports both URL schemes and HTTPS URLs.

```bash
# Native app scheme
open zoommtg://zoom.us/join?confno=123

# Web fallback
open https://zoom.us/j/123
```

### Windows
Uses the `start` command via `cmd /c`.

```cmd
start "" "zoommtg://zoom.us/join?confno=123"
```

### Linux
Uses `xdg-open` to launch URLs.

```bash
xdg-open "zoommtg://zoom.us/join?confno=123"
```

### Fallback
If platform-specific commands fail, Janus falls back to Python's `webbrowser` module.

## Troubleshooting

### Application Not Opening

**Problem**: Deep link opens browser instead of app.

**Solution**:
1. Ensure the application is installed
2. On first use, you may need to approve opening the app
3. Try with `use_web_fallback=True` to use the web version

```python
# Force web version
handler.open_deep_link("zoom", {"id": "123"}, use_web_fallback=True)
```

### Missing Required Arguments

**Problem**: Error about missing required argument.

**Solution**: Check the URL template to see which parameters are required.

```python
from janus.os.app_deep_links import DeepLinkHandler

handler = DeepLinkHandler()
app_info = handler.get_app_info("spotify")
print(app_info["url_scheme"])  # spotify:{type}:{id}
# Both 'type' and 'id' are required
```

### Unknown Application

**Problem**: Error "Unknown app 'appname'".

**Solution**: Check supported apps or add the app to the registry.

```python
handler = DeepLinkHandler()
print(handler.get_supported_apps())  # List all supported apps
```

## Best Practices

1. **Test with web fallback first**: If unsure whether the app is installed, use `use_web_fallback=True`

2. **Validate IDs**: Ensure meeting IDs, track IDs, etc. are in the correct format

3. **Handle errors gracefully**: Wrap calls in try-except to handle missing apps

   ```python
   from janus.os.app_deep_links import DeepLinkError
   
   try:
       handler.open_deep_link("zoom", {"id": "123"})
   except DeepLinkError as e:
       print(f"Failed to open: {e}")
       # Fall back to manual navigation
   ```

4. **Use voice commands for convenience**: The reasoner can extract IDs from natural language

## Security Considerations

- Deep links are marked as **LOW risk** in the action schema
- URLs are validated before opening
- No execution of arbitrary code - only URL opening
- Platform-specific security dialogs may still appear on first use

## Examples Gallery

### Complete Workflow Examples

**Open Zoom meeting from calendar:**
```python
# Get meeting ID from calendar event
meeting_id = "123-456-789"

# Open Zoom directly
handler.open_deep_link("zoom", {"id": meeting_id})
```

**Share Spotify track in Slack:**
```python
# Get Spotify track
track_id = "3n3Ppam7vgaVa1iaRUc9Lp"

# Open Slack channel
handler.open_deep_link("slack", {
    "team_id": "T123ABC",
    "channel_id": "C456DEF"
})

# Type message with Spotify link
# (handled by other Janus modules)
```

**Open GitHub issue from Jira:**
```python
# Open Jira issue
handler.open_deep_link("jira", {"id": "PROJ-123"})

# Extract linked GitHub issue
github_url = "microsoft/vscode"

# Open in GitHub
handler.open_deep_link("github", {
    "owner": "microsoft",
    "repo": "vscode"
})
```

## Technical Details

### Architecture

The deep linker consists of:

1. **Registry** (`deep_links.json`): JSON configuration of all apps
2. **Handler** (`app_deep_links.py`): Core logic for URL building and opening
3. **Agent Integration** (`system_agent.py`): Agent action for execution
4. **Action Schema** (`module_action_schema.py`): Action definition for LLM

### URL Building

URLs are built using Python's `str.format()`:

```python
template = "spotify:{type}:{id}"
args = {"type": "track", "id": "abc123"}
url = template.format(**args)  # spotify:track:abc123
```

### Platform Detection

Platform detection uses `platform.system()`:

```python
import platform

system = platform.system()
if system == "Darwin":    # macOS
    subprocess.run(["open", url])
elif system == "Windows":
    subprocess.run(["cmd", "/c", "start", "", url])
elif system == "Linux":
    subprocess.run(["xdg-open", url])
```

## See Also

- [User Manual](USER_MANUAL.md) - General Janus usage
- [Use Cases](04-use-cases.md) - Real-world scenarios
- [FAQ & Troubleshooting](06-faq-troubleshooting.md) - Common issues

## Support

For issues or questions:
1. Check the [FAQ](06-faq-troubleshooting.md)
2. Review app-specific documentation
3. Open an issue on GitHub with "deep-link" label
