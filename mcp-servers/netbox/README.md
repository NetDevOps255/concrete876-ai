# NetBox MCP Server

A comprehensive Model Context Protocol (MCP) server that provides Claude Code with full read/write access to your NetBox infrastructure data.

## Features

### Device Management
- **list_devices** - List devices with filters (site, role, manufacturer, status)
- **get_device** - Get detailed device information by ID or name
- **create_device** - Create new device
- **update_device** - Update device configuration

### Interface Management
- **list_interfaces** - List network interfaces with filters
- **get_interface** - Get interface details by ID
- **update_interface** - Update interface configuration

### IP Address Management
- **list_ip_addresses** - List IP addresses with filters
- **get_ip_address** - Get IP address details
- **create_ip_address** - Create new IP assignment
- **update_ip_address** - Update IP address
- **list_prefixes** - List IP prefixes/subnets
- **get_available_ips** - Get available IPs in a prefix

### VLAN Management
- **list_vlans** - List VLANs
- **create_vlan** - Create new VLAN

### VRF Management
- **list_vrfs** - List VRFs
- **create_vrf** - Create new VRF

### Infrastructure
- **list_sites** - List sites/locations
- **list_circuits** - List circuits
- **list_cables** - List cable connections

### Legacy/Advanced Tools
- **get_objects** - Generic object retrieval (supports 30+ object types)
- **get_object_by_id** - Get any object by type and ID
- **get_changelogs** - Access audit trail and change history

## Setup

### Prerequisites

- NetBox instance (existing)
- NetBox API token with appropriate permissions (read/write as needed)
- Docker Desktop (for containerized deployment) OR Python 3.11+ (for local deployment)

### Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and set your NetBox credentials:
   ```
   NETBOX_URL=https://your-netbox-instance.com
   NETBOX_TOKEN=your-api-token-here
   NETBOX_SSL_VERIFY=true
   ```

### Deployment Options

#### Option 1: Docker Desktop (Recommended)

1. Build and run with Docker Compose:
   ```bash
   docker-compose up -d
   ```

2. View logs:
   ```bash
   docker-compose logs -f
   ```

3. Stop the server:
   ```bash
   docker-compose down
   ```

#### Option 2: Local Python

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the server:
   ```bash
   python server.py
   ```

### Configure Claude Code

Add this server to your Claude Code MCP settings:

**For Docker:**
```json
{
  "mcpServers": {
    "netbox": {
      "command": "docker",
      "args": ["exec", "-i", "netbox-mcp-server", "python", "server.py"]
    }
  }
}
```

**For Local Python:**
```json
{
  "mcpServers": {
    "netbox": {
      "command": "python",
      "args": ["C:/Users/tcarr/Documents/GitHub Repos/claude-local/mcp-servers/netbox/server.py"],
      "env": {
        "NETBOX_URL": "https://your-netbox-instance.com",
        "NETBOX_TOKEN": "your-api-token-here"
      }
    }
  }
}
```

## Usage Examples

Once configured, you can ask Claude Code questions like:

### Device Management
- "Show me all active devices in site DC1"
- "Get details for device core-router-01"
- "Create a new device named edge-switch-01 in site DC2"
- "Update device core-router-01 to set status to maintenance"

### Interface Management
- "List all interfaces on device core-router-01"
- "Show me interface details for interface ID 456"
- "Update interface eth0 on device-123 to enable it"

### IP Management
- "List all IP addresses in VRF production"
- "Show me available IPs in prefix 10.0.1.0/24"
- "Assign IP 192.168.1.10/24 to interface 789"
- "Update IP address 10.0.0.5 to set status to reserved"

### VLAN Management
- "List all VLANs at site HQ"
- "Create VLAN 100 named 'Management' at site DC1"

### VRF Management
- "List all VRFs"
- "Create a new VRF named 'customer-a' with RD 65000:100"

### Infrastructure
- "Show me all sites"
- "List circuits from provider AT&T"
- "Show me all cable connections in rack A1"

## Tool Reference

### Device Management Tools

#### list_devices
List devices with optional filters.

**Parameters:**
- `filters` (optional): Filter criteria (e.g., `{"site": "dc1", "status": "active"}`)
- `limit` (optional): Max results (default: 50)

**Example:**
```json
{
  "filters": {"site": "dc1", "role": "router"},
  "limit": 20
}
```

#### get_device
Get device details by ID or name.

**Parameters:**
- `device_id` (optional): Device ID
- `device_name` (optional): Device name

**Example:**
```json
{
  "device_name": "core-router-01"
}
```

#### create_device
Create a new device.

**Parameters:**
- `name` (required): Device name
- `device_type` (required): Device type ID
- `role` (required): Device role ID
- `site` (required): Site ID
- `status` (optional): Status (default: "active")

**Example:**
```json
{
  "name": "edge-switch-01",
  "device_type": 10,
  "role": 5,
  "site": 3,
  "status": "active"
}
```

#### update_device
Update device configuration.

**Parameters:**
- `device_id` (required): Device ID
- `data` (required): Fields to update

**Example:**
```json
{
  "device_id": 123,
  "data": {"status": "maintenance", "comments": "Scheduled maintenance"}
}
```

### Interface Management Tools

#### list_interfaces
List interfaces with filters.

**Parameters:**
- `filters` (optional): Filters like `device_id`, `name`, `type`
- `limit` (optional): Max results (default: 50)

#### get_interface
Get interface details.

**Parameters:**
- `interface_id` (required): Interface ID

#### update_interface
Update interface configuration.

**Parameters:**
- `interface_id` (required): Interface ID
- `data` (required): Fields to update

### IP Address Management Tools

#### list_ip_addresses
List IP addresses.

**Parameters:**
- `filters` (optional): Filters like `address`, `device`, `vrf`
- `limit` (optional): Max results (default: 50)

#### get_ip_address
Get IP address details.

**Parameters:**
- `ip_id` (required): IP address ID

#### create_ip_address
Create new IP address.

**Parameters:**
- `address` (required): IP with prefix (e.g., "192.168.1.10/24")
- `status` (optional): Status (default: "active")
- `interface` (optional): Interface ID
- `vrf` (optional): VRF ID

#### update_ip_address
Update IP address.

**Parameters:**
- `ip_id` (required): IP address ID
- `data` (required): Fields to update

#### list_prefixes
List IP prefixes/subnets.

**Parameters:**
- `filters` (optional): Filters like `prefix`, `site`, `vrf`
- `limit` (optional): Max results (default: 50)

#### get_available_ips
Get available IPs in a prefix.

**Parameters:**
- `prefix_id` (required): Prefix ID
- `limit` (optional): Number of IPs to return (default: 10)

### VLAN Management Tools

#### list_vlans
List VLANs.

**Parameters:**
- `filters` (optional): Filters like `vid`, `name`, `site`
- `limit` (optional): Max results (default: 50)

#### create_vlan
Create new VLAN.

**Parameters:**
- `vid` (required): VLAN ID (1-4094)
- `name` (required): VLAN name
- `site` (optional): Site ID
- `status` (optional): Status (default: "active")

### VRF Management Tools

#### list_vrfs
List VRFs.

**Parameters:**
- `filters` (optional): Filters like `name`, `rd`, `tenant`
- `limit` (optional): Max results (default: 50)

#### create_vrf
Create new VRF.

**Parameters:**
- `name` (required): VRF name
- `rd` (optional): Route distinguisher
- `tenant` (optional): Tenant ID

### Infrastructure Tools

#### list_sites
List sites/locations.

**Parameters:**
- `filters` (optional): Filters like `name`, `region`, `status`
- `limit` (optional): Max results (default: 50)

#### list_circuits
List circuits.

**Parameters:**
- `filters` (optional): Filters like `provider`, `type`, `status`
- `limit` (optional): Max results (default: 50)

#### list_cables
List cable connections.

**Parameters:**
- `filters` (optional): Filters like `device`, `type`, `status`
- `limit` (optional): Max results (default: 50)

## Security Notes

- **Write operations** are enabled - ensure your API token has appropriate permissions
- Store API tokens securely in `.env` file
- Never commit `.env` to version control
- Use SSL verification in production (`NETBOX_SSL_VERIFY=true`)
- Consider using read-only tokens if you only need query capabilities

## Troubleshooting

**Connection errors:**
- Verify `NETBOX_URL` is correct and accessible
- Check that `NETBOX_TOKEN` has valid permissions
- For self-signed certs, set `NETBOX_SSL_VERIFY=false`

**Permission errors:**
- Ensure API token has appropriate permissions (read/write as needed)
- Check NetBox user permissions

**Docker issues:**
- Ensure Docker Desktop is running
- Check container logs: `docker-compose logs -f`
- Verify environment variables in `.env` file

**Tool not appearing in Claude Code:**
- Restart Claude Code after configuration changes
- Check MCP server logs for errors
- Verify JSON configuration syntax

## Performance Tips

- Use filters to limit result sets
- Specify `limit` parameter for large datasets
- Use field filtering in `get_objects` to reduce response size
- Consider indexing frequently queried NetBox objects

## License

MIT
