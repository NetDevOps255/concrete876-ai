#!/usr/bin/env bash
# PatchMon Lite — Interactive Setup
# Guides you through every required step before starting containers
set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()  { echo -e "${CYAN}==>${NC} $1"; }
ok()    { echo -e "${GREEN}  ✓${NC} $1"; }
warn()  { echo -e "${YELLOW}  ⚠${NC} $1"; }
err()   { echo -e "${RED}  ✗${NC} $1"; }
header(){ echo -e "\n${BOLD}$1${NC}"; echo "────────────────────────────────────────"; }

# ─── Dependency checks ────────────────────────────────────────────────────────
header "Checking dependencies"

MISSING=0
for cmd in docker openssl; do
  if command -v $cmd &>/dev/null; then
    ok "$cmd found"
  else
    err "$cmd not found — install it first"
    MISSING=1
  fi
done

# Check docker compose (v2 plugin or v1 standalone)
if docker compose version &>/dev/null 2>&1; then
  ok "docker compose (v2) found"
  COMPOSE="docker compose"
elif command -v docker-compose &>/dev/null; then
  ok "docker-compose (v1) found"
  COMPOSE="docker-compose"
else
  err "docker compose not found — install Docker Engine with Compose plugin"
  MISSING=1
fi

[ $MISSING -eq 1 ] && echo "" && err "Fix missing dependencies then re-run setup.sh" && exit 1

# ─── .env setup ───────────────────────────────────────────────────────────────
header "Environment configuration"

if [ -f .env ]; then
  warn ".env already exists — skipping creation (delete it to regenerate)"
else
  cp .env.example .env
  ok "Created .env from template"
fi

# Helper: read a value from .env
get_env() { grep "^$1=" .env 2>/dev/null | cut -d= -f2- || echo ""; }
set_env() {
  local key="$1" val="$2"
  if grep -q "^${key}=" .env 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${val}|" .env
  else
    echo "${key}=${val}" >> .env
  fi
}

# ─── Secret key ───────────────────────────────────────────────────────────────
header "Generating secrets"

CURRENT_SK=$(get_env SECRET_KEY)
if [ -z "$CURRENT_SK" ] || [ "$CURRENT_SK" = "change-me-use-openssl-rand-hex-32" ]; then
  SK=$(openssl rand -hex 32)
  set_env "SECRET_KEY" "$SK"
  ok "SECRET_KEY generated"
else
  ok "SECRET_KEY already set"
fi

CURRENT_AK=$(get_env API_KEY)
if [ -z "$CURRENT_AK" ] || [ "$CURRENT_AK" = "change-me-use-openssl-rand-hex-32" ]; then
  AK=$(openssl rand -hex 32)
  set_env "API_KEY" "$AK"
  ok "API_KEY generated"
  echo ""
  echo -e "  ${YELLOW}Save this API key for curl/script access:${NC}"
  echo -e "  ${BOLD}$AK${NC}"
  echo ""
else
  ok "API_KEY already set"
fi

# ─── Admin password ───────────────────────────────────────────────────────────
header "Admin password"

CURRENT_HASH=$(get_env ADMIN_PASSWORD_HASH)
if [ -n "$CURRENT_HASH" ] && [ "$CURRENT_HASH" != "" ]; then
  ok "ADMIN_PASSWORD_HASH already set"
else
  echo "Set a password for the PatchMon dashboard login."
  echo ""

  # Try to hash using Docker (avoids needing Python+passlib locally)
  while true; do
    read -s -p "  Enter admin password (min 8 chars): " PW1; echo ""
    read -s -p "  Confirm password: " PW2; echo ""

    if [ "$PW1" != "$PW2" ]; then
      err "Passwords don't match. Try again."
      continue
    fi
    if [ ${#PW1} -lt 8 ]; then
      err "Password must be at least 8 characters."
      continue
    fi

    info "Hashing password..."
    HASH=$(docker run --rm python:3.12-slim \
      sh -c "pip install passlib[bcrypt] -q && python3 -c \"from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('${PW1}'))\"" \
      2>/dev/null)

    if [ -z "$HASH" ]; then
      err "Could not hash password using Docker. Set ADMIN_PASSWORD_HASH manually:"
      echo "  pip install passlib[bcrypt] && python3 scripts/hash_password.py"
      break
    fi

    set_env "ADMIN_PASSWORD_HASH" "$HASH"
    ok "Password set and hashed"
    break
  done
fi

# ─── Admin username (optional override) ──────────────────────────────────────
CURRENT_USER=$(get_env ADMIN_USERNAME)
if [ -z "$CURRENT_USER" ] || [ "$CURRENT_USER" = "admin" ]; then
  read -p "  Admin username [admin]: " UNAME
  UNAME="${UNAME:-admin}"
  set_env "ADMIN_USERNAME" "$UNAME"
  ok "Admin username: $UNAME"
fi

# ─── ALLOWED_ORIGINS ──────────────────────────────────────────────────────────
header "Frontend origin (CORS)"

CURRENT_ORIGINS=$(get_env ALLOWED_ORIGINS)
echo "  What address will you access the dashboard from?"
echo "  Examples: http://192.168.1.50:3000   or   http://localhost:3000"
echo ""
read -p "  Frontend URL [http://localhost:3000]: " ORIGIN
ORIGIN="${ORIGIN:-http://localhost:3000}"
set_env "ALLOWED_ORIGINS" "$ORIGIN"
ok "ALLOWED_ORIGINS set to $ORIGIN"

# ─── Telegram (optional) ──────────────────────────────────────────────────────
header "Telegram alerts (optional — press Enter to skip)"

CURRENT_TG=$(get_env TELEGRAM_BOT_TOKEN)
if [ -n "$CURRENT_TG" ]; then
  ok "Telegram already configured"
else
  echo "  Get a bot token from @BotFather on Telegram."
  read -p "  Bot token (or press Enter to skip): " TG_TOKEN
  if [ -n "$TG_TOKEN" ]; then
    set_env "TELEGRAM_BOT_TOKEN" "$TG_TOKEN"
    read -p "  Chat ID (group starts with -100...): " TG_CHAT
    set_env "TELEGRAM_CHAT_ID" "${TG_CHAT:-}"
    ok "Telegram configured"
  else
    warn "Skipped — you can configure this in the dashboard later"
  fi
fi

# ─── Proxmox (optional) ───────────────────────────────────────────────────────
header "Proxmox API integration (optional — press Enter to skip)"

CURRENT_PVE=$(get_env PROXMOX_HOST)
if [ -n "$CURRENT_PVE" ] && [ "$CURRENT_PVE" != "192.168.1.100:8006" ]; then
  ok "Proxmox already configured"
else
  echo "  Requires an API token with PVEAuditor role."
  echo "  PVE UI: Datacenter → Permissions → API Tokens → Add"
  echo ""
  read -p "  Proxmox host:port (or press Enter to skip): " PVE_HOST
  if [ -n "$PVE_HOST" ]; then
    set_env "PROXMOX_HOST" "$PVE_HOST"
    read -p "  Token ID (e.g. root@pam!patchmon): " PVE_TID
    set_env "PROXMOX_TOKEN_ID" "${PVE_TID:-root@pam!patchmon}"
    read -s -p "  Token secret: " PVE_SEC; echo ""
    set_env "PROXMOX_TOKEN_SECRET" "$PVE_SEC"
    read -p "  Node name [pve]: " PVE_NODE
    set_env "PROXMOX_NODE" "${PVE_NODE:-pve}"
    ok "Proxmox configured"
  else
    warn "Skipped — you can add this to .env later"
  fi
fi

# ─── SSH keys ─────────────────────────────────────────────────────────────────
header "SSH key check"

if [ -f "$HOME/.ssh/id_ed25519" ]; then
  ok "Found ~/.ssh/id_ed25519"
elif [ -f "$HOME/.ssh/id_rsa" ]; then
  ok "Found ~/.ssh/id_rsa"
else
  warn "No SSH key found at ~/.ssh/"
  echo ""
  echo "  PatchMon connects to managed hosts via SSH key auth."
  read -p "  Generate a new ed25519 key now? [Y/n]: " GENKEY
  GENKEY="${GENKEY:-Y}"
  if [[ "$GENKEY" =~ ^[Yy] ]]; then
    ssh-keygen -t ed25519 -f "$HOME/.ssh/id_ed25519" -C "patchmon" -N ""
    ok "SSH key created at ~/.ssh/id_ed25519"
    echo ""
    echo -e "  ${YELLOW}Distribute this public key to your managed hosts:${NC}"
    echo "  ssh-copy-id -i ~/.ssh/id_ed25519.pub root@<host-ip>"
    echo ""
    echo "  For Proxmox LXC containers:"
    echo "  cat ~/.ssh/id_ed25519.pub >> /etc/pve/priv/authorized_keys"
  fi
fi

# ─── Start containers ─────────────────────────────────────────────────────────
header "Starting PatchMon Lite"

info "Building and starting containers (first run takes ~2 min)..."
$COMPOSE up -d --build

# Wait for backend health
info "Waiting for backend to be ready..."
ATTEMPTS=0
until curl -sf http://localhost:8000/health > /dev/null 2>&1; do
  ATTEMPTS=$((ATTEMPTS+1))
  if [ $ATTEMPTS -ge 30 ]; then
    warn "Backend not responding after 60s — check logs: $COMPOSE logs backend"
    break
  fi
  sleep 2
done

if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
  ok "Backend is up"
fi

# ─── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}PatchMon Lite is running!${NC}"
echo ""
echo -e "  Dashboard:   ${CYAN}$(get_env ALLOWED_ORIGINS | cut -d, -f1)${NC}"
echo -e "  API docs:    ${CYAN}http://localhost:8000/docs${NC}"
echo -e "  Username:    ${BOLD}$(get_env ADMIN_USERNAME)${NC}"
echo ""
echo "Next steps:"
echo "  1. Open the dashboard and sign in"
echo "  2. Patch Management → + Add Host — add your first server"
echo "  3. Click ↻ on a host to run the first patch check"
echo "  4. Telegram Alerts — connect your bot if you skipped it above"
echo ""
echo "Useful commands:"
echo "  $COMPOSE logs -f backend      — watch backend logs"
echo "  $COMPOSE logs -f frontend     — watch frontend logs"
echo "  $COMPOSE restart backend      — restart after .env changes"
echo "  $COMPOSE down                 — stop everything"
echo "  $COMPOSE down -v              — stop and delete all data"
echo ""
echo -e "API key (for curl): ${CYAN}$(get_env API_KEY)${NC}"
