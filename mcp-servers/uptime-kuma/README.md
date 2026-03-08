# Uptime Kuma MCP Server

MCP server for [Uptime Kuma](https://github.com/louislam/uptime-kuma) — lets Claude manage monitors, notifications, status pages, maintenance windows, and tags via the `uptime-kuma-api` Socket.IO wrapper.

**26 tools** covering full monitor lifecycle, heartbeat history, uptime stats, notifications, status pages, maintenance windows, tags, and system info.

## Prerequisites

- Docker and Docker Compose (recommended)
- OR Python 3.10+ (local deployment)
- Running Uptime Kuma instance (v1.23.x or v2.x)

## Installation

### Option 1: Docker (Recommended)

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env

# Build and start container
docker compose up -d --build

# Verify container is running
docker ps | grep uptime-kuma-mcp-server
```

To stop the container:
```bash
docker compose down
```

### Option 2: Local Python

```bash
pip install -r requirements.txt

# Set environment variables
export UPTIME_KUMA_URL="http://192.168.1.50:3001"
export UPTIME_KUMA_USERNAME="admin"
export UPTIME_KUMA_PASSWORD="yourpassword"

# Run
python server.py
```

## Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `UPTIME_KUMA_URL` | Yes | `http://127.0.0.1:3001` | Your Uptime Kuma instance URL |
| `UPTIME_KUMA_USERNAME` | Yes | — | Admin username |
| `UPTIME_KUMA_PASSWORD` | Yes | — | Admin password |

## Configure Claude Code

### Docker Setup

First, ensure the container is running:
```bash
docker compose up -d
```

Add to your Claude Code MCP configuration:

```json
{
  "mcpServers": {
    "uptime-kuma": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "uptime-kuma-mcp-server",
        "python",
        "server.py"
      ]
    }
  }
}
```

### Local Python Setup

```json
{
  "mcpServers": {
    "uptime-kuma": {
      "command": "python",
      "args": ["/path/to/uptime-kuma/server.py"],
      "env": {
        "UPTIME_KUMA_URL": "http://192.168.1.50:3001",
        "UPTIME_KUMA_USERNAME": "admin",
        "UPTIME_KUMA_PASSWORD": "yourpassword"
      }
    }
  }
}
```

Restart Claude Code after saving the configuration.

## Tools

### Monitor Management

| Tool | Description |
|---|---|
| `kuma_get_monitors` | List all monitors with full config and status |
| `kuma_get_monitor` | Get single monitor by ID |
| `kuma_add_monitor` | Create a new monitor (HTTP, ping, TCP, DNS, push, etc.) |
| `kuma_edit_monitor` | Update an existing monitor (merges changes, only provided fields updated) |
| `kuma_delete_monitor` | Delete a monitor permanently (⚠️ destructive) |
| `kuma_pause_monitor` | Pause a monitor — stops checks, retains config |
| `kuma_resume_monitor` | Resume a paused monitor |
| `kuma_get_monitor_beats` | Paginated heartbeat history (timestamps, status, ping, message) |
| `kuma_get_important_heartbeats` | Status-change events only (outage history without noise) |
| `kuma_get_avg_ping` | Average response time in ms for a monitor |
| `kuma_get_uptime` | 24h and 30d uptime percentages for a monitor |

### Notifications

| Tool | Description |
|---|---|
| `kuma_get_notifications` | List all notification channels |
| `kuma_add_notification` | Add Telegram, Slack, Discord, webhook, email, and more |
| `kuma_delete_notification` | Remove a notification channel |

### Status Pages

| Tool | Description |
|---|---|
| `kuma_get_status_pages` | List all public status pages |
| `kuma_get_status_page` | Get full status page config and monitor groups by slug |

### Maintenance Windows

| Tool | Description |
|---|---|
| `kuma_get_maintenances` | List all scheduled maintenance windows |
| `kuma_add_maintenance` | Schedule a maintenance window (single or recurring) |
| `kuma_delete_maintenance` | Delete a maintenance window |

### Tags

| Tool | Description |
|---|---|
| `kuma_get_tags` | List all tags |
| `kuma_add_tag` | Create a new tag with name and color |
| `kuma_add_monitor_tag` | Attach a tag to a monitor |

### System

| Tool | Description |
|---|---|
| `kuma_get_info` | Server version, base URL, timezone |
| `kuma_get_settings` | Global server settings |
| `kuma_get_proxies` | Configured proxy connections |
| `kuma_get_docker_hosts` | Docker host configs (for container monitors) |

## Usage Examples

```
"List all my monitors and show me which ones are currently down"
"Pause the monitor named 'staging-api' while I deploy"
"Add a new HTTP monitor for https://app.example.com checking every 30s"
"Show me the last 20 heartbeats for monitor ID 5"
"What's the 30-day uptime on the production API monitor?"
"Create a maintenance window this Saturday 2am–4am"
"Add a Slack notification channel using webhook https://hooks.slack.com/..."
"Resume all paused monitors"
"Show me only the down/up transitions for monitor 3 — not every heartbeat"
```

## Notes

- The `uptime-kuma-api` library uses **Socket.IO** (not REST). Each tool call opens a new connection and disconnects after. Expect ~1–2s overhead per call.
- Credentials grant **full admin access** — treat them like a password.
- Tested against Uptime Kuma v1.23.x and v2.x.

## License

MIT
