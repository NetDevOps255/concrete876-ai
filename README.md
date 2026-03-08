# concrete876-ai
A collection of AI-driven tools for network operations, infrastructure automation, and systems integration

---

## Overview

**concrete876-ai** is a collection of production-grade MCP (Model Context Protocol) servers and automation tools built at the intersection of network engineering and artificial intelligence. These integrations allow Claude to directly interact with real infrastructure — firewalls, monitoring platforms, documentation systems, and inventory management — through natural language.

All tools are containerized with Docker and designed for real-world environments. Expect Palo Alto, OPNsense, NetBox, Observium, and self-hosted stacks throughout.

---

## MCP Servers

| Server | Target System | Tools | Description |
|---|---|---|---|
| [`mcp-servers/paloalto`](./mcp-servers/paloalto) | Palo Alto NGFW | 10 | Firewall ops via PAN-OS XML API — policies, sessions, BGP, logs, address objects, commit |
| [`mcp-servers/opnsense`](./mcp-servers/opnsense) | OPNsense Firewall | 30+ | Full firewall management — aliases, filter rules, NAT (DNAT/SNAT/1:1/NPT), savepoints, rollback |
| [`mcp-servers/netbox`](./mcp-servers/netbox) | NetBox | 20+ | DCIM & IPAM — devices, interfaces, IPs, prefixes, VLANs, VRFs, sites, circuits, cables |
| [`mcp-servers/observium`](./mcp-servers/observium) | Observium NMS | 10 | Network monitoring — devices, ports, alerts, sensors, inventory, device management |
| [`mcp-servers/bookstack`](./mcp-servers/bookstack) | BookStack | 40+ | Documentation management — books, pages, chapters, shelves, users, roles, search, attachments |
| [`mcp-servers/homebox`](./mcp-servers/homebox) | Homebox | 12 | Home inventory — items, locations, labels, attachments, image-to-inventory via Claude vision |
| [`mcp-servers/uptime-kuma`](./mcp-servers/uptime-kuma) | Uptime Kuma | 26 | Uptime monitoring — monitors, heartbeats, notifications, status pages, maintenance windows, tags |

---

## Server Details

### Palo Alto NGFW MCP
Interfaces with the PAN-OS XML API using API key authentication. All write operations target candidate config only — an explicit `pa_commit` is required to push changes to running config. Multi-vsys aware.

**Key tools:** `pa_overview`, `pa_check_interfaces`, `pa_check_routes`, `pa_check_sessions`, `pa_check_policies`, `pa_check_bgp_peers`, `pa_query_logs`, `pa_create_address_object`, `pa_commit`

---

### OPNsense Firewall MCP
Full read/write control over OPNsense via its REST API. Includes a safe change workflow with savepoints and automatic rollback protection — create a savepoint, make changes, apply, test, then confirm or revert.

**Key tool groups:** Alias management, filter rules (with rule ordering), DNAT/SNAT/1:1 NAT, NPT (IPv6), rule groups/categories, config savepoint/rollback

---

### Observium NMS MCP
Query and manage devices in Observium. Requires Observium Subscription Edition (API not available in Community Edition). Uses HTTP Basic Auth.

**Key tools:** `get_devices`, `get_device`, `get_ports`, `get_alerts`, `get_sensors`, `get_inventory`, `add_device`, `delete_device`, `update_device`, `ignore_alert`

---

### BookStack MCP
40+ tools covering nearly the entire BookStack API. Full CRUD on all content types plus export, search, user/role management, and recycle bin.

**Key tool groups:** Books, Pages, Chapters, Shelves, Users, Roles, Search, Attachments, Images, Recycle Bin, Permissions, System Info

---

### NetBox DCIM & IPAM MCP
Full read/write access to NetBox for device, interface, and IP address management. The source of truth for infrastructure documentation — use it to look up IPs, document new devices, manage VLANs/VRFs, and pull audit changelogs. Includes a generic `get_objects` tool supporting 30+ NetBox object types.

**Key tool groups:** Device management, interface management, IP address management, prefix/subnet queries, VLAN management, VRF management, sites, circuits, cables, changelogs

---

### Homebox Inventory MCP
Natural language inventory management for self-hosted Homebox. Supports image-to-inventory: share a photo, Claude extracts item details via vision, creates the item, and uploads the photo as an attachment automatically.

**Key tools:** `search_items`, `get_item`, `create_item`, `update_item`, `delete_item`, `get_locations`, `create_location`, `get_labels`, `create_label`, `upload_attachment`, `get_statistics`

---

### Uptime Kuma MCP
Monitor management for self-hosted Uptime Kuma via the Socket.IO API. Full lifecycle control over monitors plus heartbeat history, uptime stats, notification channels, status pages, maintenance windows, and tags.

**Key tool groups:** Monitor management (create/edit/pause/resume/delete), heartbeat history, uptime percentages, notifications (Telegram/Slack/Discord/webhook/email), status pages, maintenance windows, tags, system info

---

## Deployment

All servers run as persistent Docker containers and expose themselves to Claude Code via stdio transport (`docker exec -i`).

```bash
# Start any server
cd mcp-servers/<server-name>
cp .env.example .env       # add your credentials
docker compose up -d --build

# Verify running
docker ps | grep <server-name>-mcp-server
```

Each server folder contains its own `README.md` with full setup, configuration, and Claude Code integration instructions.

---

## Tech Stack

### Networking
![Palo Alto](https://img.shields.io/badge/Palo_Alto_Networks-F04E23?style=flat&logo=paloaltonetworks&logoColor=white)
![OPNsense](https://img.shields.io/badge/OPNsense-D94F00?style=flat&logoColor=white)
![BGP](https://img.shields.io/badge/BGP-Multi--ISP-informational?style=flat)

### Automation & Infrastructure
![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)
![Ansible](https://img.shields.io/badge/Ansible-EE0000?style=flat&logo=ansible&logoColor=white)

### AI & MCP
![FastMCP](https://img.shields.io/badge/FastMCP-Model_Context_Protocol-green?style=flat)
![Claude](https://img.shields.io/badge/Anthropic-Claude-black?style=flat)

### Monitoring & Observability
![Observium](https://img.shields.io/badge/Observium-NMS-blue?style=flat)
![Grafana](https://img.shields.io/badge/Grafana-F46800?style=flat&logo=grafana&logoColor=white)

---

## About

Network Engineer with deep roots in datacenter and enterprise infrastructure — BGP, VRFs, VXLAN, multi-ISP traffic engineering, and large-scale automation. Passionate about closing the gap between traditional network operations and modern AI-driven tooling.

All projects are built against real infrastructure and intended for production use.

---

## Contact

- 🌐 [Website](https://traviscarr.dev)
- 🐙 [GitHub](https://github.com/NetDevOps255/concrete876-ai)
- 💼 [LinkedIn](https://www.linkedin.com/in/travis-carr/)
