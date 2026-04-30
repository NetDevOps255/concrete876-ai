# PatchMon Lite

Self-hosted patch management for your Proxmox homelab. Drop-in replacement for the core features of PatchMon — patch management, Docker monitoring, Telegram alerting, Proxmox integration — running entirely on your own infrastructure.

---

## Features

| Feature | Details |
|---|---|
| **Patch Management** | apt / dnf / apk / pacman / FreeBSD pkg via SSH |
| **Docker Monitoring** | Container inventory + image digest comparison |
| **Telegram Alerts** | Configurable rules — patches, reboots, Docker outdated, VM offline |
| **Proxmox Integration** | API sync, LXC auto-enroll, VM discovery |
| **Audit Log** | Timestamped trail of all patch jobs, CSV export |
| **Authentication** | JWT session login + API key for curl/integrations |

---

## Quick Start

```bash
git clone <your-repo>/patchmon-lite
cd patchmon-lite
chmod +x setup.sh && ./setup.sh
```

Open **http://localhost:3000**

---

## Security Setup (Do This Before Anything Else)

### 1. Generate secrets

```bash
# Secret key for JWT signing
openssl rand -hex 32

# API key for curl/external access
openssl rand -hex 32
```

Paste both into your `.env`.

### 2. Set admin password

```bash
# Install deps first if running outside Docker
pip install passlib[bcrypt]

python3 scripts/hash_password.py
# Enter your chosen password when prompted
# Copy the ADMIN_PASSWORD_HASH=... line into .env
```

### 3. Lock down ALLOWED_ORIGINS

In `.env`, set this to your actual frontend address only:

```env
ALLOWED_ORIGINS=http://192.168.1.50:3000
```

Never use `*` in production. The default allows `localhost` only.

### 4. Your .env should look like this before first run

```env
SECRET_KEY=b3f2e1a4d9c8...   # 64 hex chars from openssl
API_KEY=7a1c9f3b2e4d...       # 64 hex chars from openssl
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=$2b$12$...  # from hash_password.py
ALLOWED_ORIGINS=http://192.168.1.50:3000
```

---

## Configuration

Copy `.env.example` → `.env`:

```bash
cp .env.example .env
```

### Full .env reference

```env
# Security
SECRET_KEY=                    # openssl rand -hex 32
API_KEY=                       # openssl rand -hex 32
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=           # python3 scripts/hash_password.py
ALLOWED_ORIGINS=http://localhost:3000

# Telegram
TELEGRAM_BOT_TOKEN=            # from @BotFather
TELEGRAM_CHAT_ID=              # group chat ID, starts with -100...

# Proxmox API
PROXMOX_HOST=192.168.1.100:8006
PROXMOX_TOKEN_ID=root@pam!patchmon
PROXMOX_TOKEN_SECRET=
PROXMOX_NODE=pve

# SSH
SSH_DEFAULT_USER=root

# Scheduler (seconds)
PATCH_CHECK_INTERVAL=3600
DOCKER_CHECK_INTERVAL=3600
PROXMOX_SYNC_INTERVAL=300

# Rate limiting (login attempts per IP per minute)
AUTH_RATE_LIMIT=10
```

---

## Authentication

### UI Login

The dashboard requires username + password login. A JWT is stored in `sessionStorage` (cleared on tab close). Sessions expire after 24 hours.

### API Key (for curl / scripts)

Pass `X-API-Key: <your-key>` header:

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/hosts/
```

### JWT (for scripting with sessions)

```bash
# Get a token
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"yourpassword"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Use it
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/hosts/
```

---

## Proxmox API Token Setup

In the Proxmox web UI:

1. **Datacenter → Permissions → API Tokens → Add**
2. User: `root@pam`, Token ID: `patchmon`, **uncheck Privilege Separation**
3. Copy the secret — it only shows once
4. **Datacenter → Permissions → Add → API Token Permission**
   - Path: `/`, Token: `root@pam!patchmon`, Role: `PVEAuditor`

> **Why `PVEAuditor`?** Read-only. PatchMon only needs to list VMs and read IPs — it never calls Proxmox to modify anything. Principle of least privilege.

---

## Telegram Bot Setup

1. Message `@BotFather` → `/newbot` → copy the token
2. Add your bot to a group, or get your personal chat ID via `@userinfobot`
3. Group chat IDs start with `-100...`
4. Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`
5. Or connect via the UI: **Telegram Alerts → Connect**

---

## SSH Key Auth

The backend container mounts `/root/.ssh` from the Docker host (read-only). Ensure your SSH key is authorized on all managed hosts:

```bash
# From your Docker host:
ssh-copy-id -i ~/.ssh/id_ed25519.pub root@192.168.1.x
```

For LXC containers, the Proxmox host's key works directly:

```bash
# On each LXC:
mkdir -p ~/.ssh
cat /etc/pve/priv/authorized_keys >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

**Using a dedicated SSH key (recommended):**

```bash
# Generate a dedicated key for PatchMon
ssh-keygen -t ed25519 -f ~/.ssh/patchmon_ed25519 -C "patchmon" -N ""

# Distribute to all managed hosts
for HOST in 192.168.1.101 192.168.1.102 192.168.1.103; do
  ssh-copy-id -i ~/.ssh/patchmon_ed25519.pub root@$HOST
done
```

Then per-host in the UI or API, set `ssh_key_path` to `/root/.ssh/patchmon_ed25519`.

---

## Adding Hosts

**Via UI:** Patch Management → + Add Host

**Via API:**
```bash
curl -X POST http://localhost:8000/hosts/ \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "pve-app01",
    "ip_address": "192.168.1.101",
    "ssh_user": "root",
    "ssh_port": 22
  }'
```

After adding, trigger a check immediately:

```bash
curl -X POST http://localhost:8000/hosts/1/check \
  -H "X-API-Key: your-api-key"
```

---

## Proxmox Auto-Enrollment

When Proxmox is configured:
- **LXC containers** are auto-enrolled — IP fetched via Proxmox API directly, no agent needed
- **VMs** with the QEMU guest agent installed are also auto-discovered and IP-resolved
- VMs without guest agent appear in the inventory but require manual IP entry

Trigger a sync manually:
```bash
curl -X POST http://localhost:8000/proxmox/sync \
  -H "X-API-Key: your-api-key"
```

---

## Supported Package Managers

| OS | Package Manager |
|---|---|
| Ubuntu / Debian / Proxmox VE | `apt` |
| RHEL / CentOS / Fedora / AlmaLinux | `dnf` |
| Alpine Linux | `apk` |
| Arch Linux | `pacman` |
| FreeBSD | `pkg` |

Detection is automatic — PatchMon probes for each binary on first contact.

---

## Scheduler Intervals

| Variable | Default | Description |
|---|---|---|
| `PATCH_CHECK_INTERVAL` | `3600` | Refresh patch status for all hosts (1h) |
| `DOCKER_CHECK_INTERVAL` | `3600` | Scan Docker images for digest changes (1h) |
| `PROXMOX_SYNC_INTERVAL` | `300` | Sync VM/LXC list from Proxmox (5m) |

---

## API Reference

Interactive Swagger docs: **http://localhost:8000/docs**

```
POST /auth/login                    Get JWT token
GET  /auth/me                       Check current auth

GET  /hosts/                        List all hosts
POST /hosts/                        Add host
DELETE /hosts/{id}                  Remove host
POST /hosts/{id}/check              Trigger patch check (async)
POST /hosts/{id}/patch              Apply patches (?dry_run=true)
GET  /hosts/{id}/packages           List pending packages
GET  /hosts/{id}/jobs               Patch job history
GET  /hosts/{id}/containers         Docker containers on host

GET  /docker/                       All containers across all hosts
POST /docker/scan                   Trigger full Docker scan (async)
GET  /docker/summary                Container count summary

GET  /proxmox/status                Proxmox connection status
GET  /proxmox/guests                List VMs and LXCs
POST /proxmox/sync                  Sync from Proxmox API (async)

GET  /alerts/telegram/status        Telegram connection status
POST /alerts/telegram/connect       Connect bot (tests connection first)
GET  /alerts/rules                  List alert rules
PATCH /alerts/rules/{id}            Enable/disable a rule
POST /alerts/test/{event_type}      Send test alert

GET  /logs/                         Audit log (?limit=100&hostname=x)
GET  /logs/export/csv               Download full log as CSV
GET  /logs/summary                  24h event counts

GET  /stats                         Dashboard summary stats
GET  /health                        Health check (public, no auth)
```

---

## Security Model Summary

| Layer | Implementation |
|---|---|
| **UI auth** | Username + bcrypt password → JWT (24h expiry, sessionStorage) |
| **API auth** | `X-API-Key` header, constant-time compare |
| **CORS** | Explicit origin whitelist only, no wildcard |
| **Rate limiting** | 10 login attempts/IP/minute (configurable) |
| **Security headers** | `X-Frame-Options`, `X-Content-Type-Options`, `X-XSS-Protection`, `Referrer-Policy` |
| **SSH** | Key auth only (no password SSH), read-only key mount in container |
| **Proxmox** | Read-only `PVEAuditor` role, API token (no root password) |
| **Secrets** | All in `.env`, never committed — `.gitignore` enforced |
| **DB** | SQLite in named Docker volume, not bind-mounted to host filesystem |
| **Passwords** | bcrypt hashed, never stored plaintext |

---

## Directory Structure

```
patchmon-lite/
├── backend/
│   ├── main.py                 FastAPI app, middleware, route registration
│   ├── core/
│   │   ├── config.py           Settings + DB engine
│   │   └── auth.py             JWT + API key auth dependencies
│   ├── models/models.py        SQLModel DB tables
│   ├── routers/
│   │   ├── auth.py             Login endpoint
│   │   ├── hosts.py            Host CRUD + patch operations
│   │   ├── docker_router.py    Docker endpoints
│   │   ├── proxmox.py          Proxmox API endpoints
│   │   ├── alerts.py           Telegram config + alert rules
│   │   └── logs.py             Audit log + CSV export
│   └── services/
│       ├── ssh_service.py      SSH exec + multi-distro package manager logic
│       ├── docker_service.py   Docker inspect via SSH, digest comparison
│       ├── proxmox_service.py  Proxmox REST API client
│       ├── telegram_service.py Alert templates + MarkdownV2 sender
│       └── scheduler.py        APScheduler background jobs
├── frontend/
│   └── src/
│       ├── App.jsx             Full React dashboard
│       ├── api.js              API client (handles auth headers)
│       └── main.jsx            Entry point
├── scripts/
│   └── hash_password.py        bcrypt hash generator for ADMIN_PASSWORD_HASH
├── docker-compose.yml
├── .env.example
├── setup.sh
└── README.md
```

---

## Updating

```bash
docker compose pull
docker compose up -d --build
```

Data persists in the `patchmon-data` Docker volume. SQLite DB survives rebuilds.

---

## Hardening for Exposure Beyond LAN

If you're putting this behind a reverse proxy (Nginx, Caddy, Traefik) and exposing it externally:

1. **TLS only** — terminate SSL at the proxy, HTTP only on the internal Docker network
2. **Set `ALLOWED_ORIGINS`** to your public HTTPS domain
3. **Change `AUTH_RATE_LIMIT`** to `5` or lower
4. **Disable Swagger docs** — set `docs_url=None` and `redoc_url=None` in `main.py`
5. **Firewall port 8000** — only the proxy should reach the backend
6. **Consider Fail2ban** on your proxy for the `/auth/login` endpoint

For homelab-internal use only, the default config with a strong password and API key is sufficient.
