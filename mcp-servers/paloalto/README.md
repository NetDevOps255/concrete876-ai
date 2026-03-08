# paloalto-mcp

MCP server for Palo Alto NGFW — built with FastMCP and the PAN-OS XML API. Runs as a persistent Docker container and integrates with Claude Code via stdio transport.

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Project Structure](#project-structure)
- [Environment Variables](#environment-variables)
- [Setup & Deployment](#setup--deployment)
- [Claude Code Configuration](#claude-code-configuration)
- [MCP Tools](#mcp-tools)
- [Tool Reference](#tool-reference)
- [Security Notes](#security-notes)
- [Troubleshooting](#troubleshooting)

---

## Overview

This server exposes Palo Alto NGFW operational and configuration data to Claude Code through 10 MCP tools. Authentication is API-key only — no username/password handling. All write operations target the candidate config only and require an explicit `pa_commit` call to push changes to the running config.

---

## Prerequisites

- Docker and Docker Compose installed on the host running Claude Code
- PAN-OS API key (see [Generating an API Key](#generating-an-api-key))
- Network reachability from the Docker host to the firewall management interface
- Claude Code installed and configured

### Generating an API Key

From the web UI: **Device > Administrators > [account] > Generate API Key**

Or via curl:

```bash
curl -k -X GET \
  'https://<firewall-ip>/api/?type=keygen&user=admin&password=<password>'
```

Copy the `<key>` value from the XML response and store it as `PA_API_KEY` in your `.env` file.

---

## Project Structure

```
paloalto-mcp/
├── server.py            # MCP server — all tools defined here
├── Dockerfile           # Python 3.12-slim image
├── docker-compose.yml   # Container definition with env var bindings
├── requirements.txt     # fastmcp, httpx, pydantic
├── .env                 # Credentials — never commit this
└── README.md
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `PA_HOST` | Yes | Firewall URL including scheme (e.g. `https://192.168.1.1`) |
| `PA_API_KEY` | Yes | PAN-OS API key |
| `PA_VSYS` | No | vsys to target. Defaults to `vsys1` |
| `PA_VERIFY_SSL` | No | Set to `true` to enable SSL verification. Defaults to `false` |

Example `.env`:

```env
PA_HOST=https://192.168.1.1
PA_API_KEY=LUFRPT14MW5xOEo1ck9BaVFoNnhXREJPREhIbzRMa2c9...
PA_VSYS=vsys1
PA_VERIFY_SSL=false
```

---

## Setup & Deployment

**1. Clone or copy the project folder to the Docker host.**

**2. Populate your `.env` file** with the variables above.

**3. Build and start the container:**

```bash
cd paloalto-mcp
docker compose up -d --build
```

**4. Verify the container is running:**

```bash
docker ps | grep paloalto-mcp-server
```

**Container management:**

```bash
# View logs
docker logs paloalto-mcp-server

# Restart
docker compose restart

# Stop
docker compose down

# Rebuild after server.py changes
docker compose up -d --build
```

---

## Claude Code Configuration

Add the following block to your `~/.claude.json` under `mcpServers`. If you already have other servers configured, merge this entry alongside them — do not replace the entire object.

```json
{
  "mcpServers": {
    "paloalto": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "paloalto-mcp-server",
        "python",
        "server.py"
      ]
    }
  }
}
```

Restart Claude Code after editing `claude.json`. The `paloalto-mcp-server` container must be running before Claude Code can invoke the tools.

---

## MCP Tools

| Tool | Type | Description |
|---|---|---|
| `pa_overview` | Read | System info, HA state, session summary, interface count |
| `pa_check_interfaces` | Read | Interface status — state, IP, speed, duplex, MAC |
| `pa_check_routes` | Read | Routing table with virtual router and prefix filter |
| `pa_check_sessions` | Read | Active sessions filterable by src/dst IP or application |
| `pa_check_policies` | Read | Security, NAT, or PBF rules from candidate config |
| `pa_check_address_objects` | Read | Address objects in a vsys with optional name filter |
| `pa_check_bgp_peers` | Read | BGP peer state, prefix counts, session duration |
| `pa_query_logs` | Read | Threat, traffic, system, or URL logs with PAN-OS filter syntax |
| `pa_create_address_object` | Write | Create address object in candidate config (no auto-commit) |
| `pa_commit` | Write | Commit candidate config to running config, returns job ID |

---

## Tool Reference

### `pa_overview`

No parameters. Returns hostname, model, software version, serial, uptime, HA state, and active session counts (total, TCP, UDP, ICMP).

---

### `pa_check_interfaces`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `interface` | string | `""` | Filter by name (e.g. `ethernet1/1`). Blank returns all. |
| `vsys` | string | `PA_VSYS` | Target vsys |

Returns: name, state, IP, speed, duplex, MAC.

---

### `pa_check_routes`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `virtual_router` | string | `default` | Virtual router name |
| `destination` | string | `""` | Optional prefix filter (e.g. `10.0.0.0/8`) |

Returns: destination, nexthop, metric, flags, interface, route-table, age.

---

### `pa_check_sessions`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `source_ip` | string | `""` | Filter by source IP |
| `dest_ip` | string | `""` | Filter by destination IP |
| `application` | string | `""` | Filter by app name (e.g. `ssl`, `dns`) |
| `limit` | int | `50` | Max results (max 500) |

Returns: session index, application, state, src, dst, sport, dport, proto, vsys, start-time.

---

### `pa_check_policies`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `vsys` | string | `PA_VSYS` | Target vsys |
| `name_filter` | string | `""` | Substring match against rule names |
| `policy_type` | string | `security` | `security`, `nat`, or `pbf` |

Reads from candidate config. Returns full rule objects including zones, addresses, applications, services, and action.

---

### `pa_check_address_objects`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `vsys` | string | `PA_VSYS` | Target vsys |
| `name_filter` | string | `""` | Filter by name substring |

Returns: name, ip_netmask (or ip-range/fqdn), description, tags.

---

### `pa_check_bgp_peers`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `virtual_router` | string | `default` | Virtual router name |
| `peer_filter` | string | `""` | Filter by peer name or IP substring |

Returns: peer name, peer address, local address, BGP state, status duration, messages in/out, prefixes received.

---

### `pa_query_logs`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `log_type` | string | `threat` | `threat`, `traffic`, `system`, or `url` |
| `query` | string | `""` | PAN-OS filter expression (e.g. `(addr.src in 10.0.0.0/8)`) |
| `limit` | int | `50` | Max entries (max 500) |

Returns: time, src, dst, app, action, rule, threat name/type, severity, category, src zone, dst zone.

---

### `pa_create_address_object`

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Address object name |
| `ip_netmask` | string | Yes | CIDR notation (e.g. `10.1.1.0/24`) |
| `description` | string | No | Optional description |
| `vsys` | string | No | Defaults to `PA_VSYS` |
| `tag` | string | No | Tag name to apply |

Writes to candidate config only. Call `pa_commit` to push to running config.

---

### `pa_commit`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `description` | string | `""` | Commit description (max 255 chars) |

Returns commit job ID. Track progress in the PAN-OS web UI under **Monitor > Jobs**.

---

## Security Notes

- Never commit `.env` to version control. Add it to `.gitignore`.
- The API key grants access equivalent to the account it was generated from. Treat it like a password.
- Set `PA_VERIFY_SSL=true` in production environments with a valid management certificate.
- The container runs as root by default. Add a non-root user to the Dockerfile for hardened deployments.
- No built-in rate limiting. Avoid rapid bulk queries against production firewalls.

---

## Troubleshooting

**Container not found error in Claude Code**
The `paloalto-mcp-server` container must be running. Run `docker ps` to verify, then `docker compose up -d` if needed.

**Authentication failed (401)**
Verify `PA_API_KEY` in `.env`. Regenerate from Device > Administrators if expired. Confirm the admin account has API access permissions enabled under its admin role.

**Connection refused / timeout**
Verify `PA_HOST` is reachable from the Docker host — not just the machine running Claude Code. Check management interface ACLs on the firewall; the Docker bridge network IP range may need to be permitted.

**Empty results from policy or address object tools**
Confirm `PA_VSYS` matches the vsys where objects are defined. On multi-vsys firewalls each vsys has its own rulebase and address objects.

**SSL certificate errors**
Set `PA_VERIFY_SSL=false` for self-signed certs (default). For production, ensure the cert CN or SAN matches the `PA_HOST` value and set `PA_VERIFY_SSL=true`.
