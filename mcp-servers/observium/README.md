# Observium MCP Server

Simple MCP server for Observium network monitoring.

## Install

### Option 1: Docker (Recommended)

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env

# Build and start container
docker-compose up -d --build

# Verify container is running
docker ps | grep observium-mcp-server
```

To stop the container:
```bash
docker-compose down
```

### Option 2: Local Python

```bash
pip install -r requirements.txt

# Set environment variables
export OBSERVIUM_URL="https://observium.yourdomain.com"
export OBSERVIUM_USER="your_username"
export OBSERVIUM_PASS="your_password"

# Run
python server.py
```

## Configure Claude Code

### Docker Setup

First, make sure the container is running:
```bash
docker-compose up -d
```

Add to `~/.config/claude-code/mcp_settings.json`:

```json
{
  "mcpServers": {
    "observium": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "observium-mcp-server",
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
    "observium": {
      "command": "python3",
      "args": ["/path/to/observium-mcp-server/server.py"],
      "env": {
        "OBSERVIUM_URL": "https://observium.yourdomain.com",
        "OBSERVIUM_USER": "your_username",
        "OBSERVIUM_PASS": "your_password"
      }
    }
  }
}
```

## Tools

### Query Tools
- **get_devices** - Get network devices (filter by hostname, os, location, status)
- **get_device** - Get specific device details by ID or hostname
- **get_ports** - Get network interfaces (filter by device, state, errors)
- **get_alerts** - Get alerts (filter by device, status, entity type)
- **get_sensors** - Get sensors (temperature, voltage, etc)
- **get_inventory** - Get hardware inventory

### Management Tools
- **add_device** - Add a new device to Observium
- **delete_device** - Remove a device
- **update_device** - Update device settings (ignore, disable, purpose)
- **ignore_alert** - Acknowledge/ignore an alert

## Usage Examples

```
# Get all devices
get_devices

# Get Cisco devices
get_devices with os="ios"

# Get device by hostname
get_device with device_id="router01.company.com"

# Get ports for a specific device
get_ports with device_id="123"

# Get all down ports
get_ports with state="down"

# Get active alerts
get_alerts with status="failed"

# Get temperature sensors
get_sensors with sensor_class="temperature"

# Add a new device
add_device with hostname="switch01.company.com" and snmp_community="public"

# Disable polling for a device
update_device with device_id="123" and disabled=1

# Acknowledge an alert
ignore_alert with alert_id="456" and ignore_until_ok=1
```

## API Endpoints

This MCP server uses the Observium REST API v0. Available endpoints:
- `/devices/` - Device management
- `/ports/` - Interface/port information
- `/alerts/` - Alert monitoring
- `/sensors/` - Environmental sensors
- `/inventory/` - Hardware inventory
- `/alert_checks/` - Alert check definitions

## Notes

- Requires Observium Subscription Edition (API not available in CE)
- Uses HTTP Basic Auth
- All timestamps in format: `Y-m-d H:i:s` (e.g., `2025-01-21 12:00:00`)



{
  "mcpServers": {
    "observium": {
      "command": "docker",
      "args": ["exec", "-i", "observium-mcp-server", "python", "server.py"]
    }
  }
}