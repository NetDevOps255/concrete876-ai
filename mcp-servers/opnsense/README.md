# OPNsense Firewall MCP Server

MCP server for managing OPNsense firewall through the API. Provides tools for managing firewall rules, aliases, NAT configurations, and more.

## Features

- **Alias Management** - Create, update, delete, and manage firewall aliases
- **Filter Rules** - Full control over firewall filter rules
- **NAT Configuration** - Destination NAT, Source NAT, One-to-One NAT, and NPT
- **Groups & Categories** - Organize rules with groups and categories
- **Configuration Management** - Savepoints, rollback, and change application
- **Safe Rollback** - Automatic rollback protection for risky changes

## Prerequisites

1. OPNsense firewall (tested on 23.x and later)
2. API access enabled in OPNsense
3. API key and secret generated

### Generate API Credentials

In OPNsense web interface:
1. Go to **System → Access → Users**
2. Edit your user or create a new API user
3. Scroll to **API Keys** section
4. Click **+** to generate a new API key
5. Save the **Key** and **Secret** (you'll need both)

## Installation

### Option 1: Docker (Recommended)

```bash
# Copy environment template
cp .env .env.local

# Edit .env.local with your credentials
nano .env.local

# Build and start container
docker-compose up -d --build

# Verify container is running
docker ps | grep opnsense-mcp-server
```

To stop the container:
```bash
docker-compose down
```

### Option 2: Local Python

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export OPNSENSE_URL="https://your-opnsense.local"
export OPNSENSE_API_KEY="your_api_key"
export OPNSENSE_API_SECRET="your_api_secret"

# Run
python server.py
```

## Configure Claude Code

### Docker Setup

First, ensure the container is running:
```bash
docker-compose up -d
```

Add to `~/.config/claude-code/mcp_settings.json` (Linux/Mac) or `%APPDATA%\claude-code\mcp_settings.json` (Windows):

```json
{
  "mcpServers": {
    "opnsense": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "opnsense-mcp-server",
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
    "opnsense": {
      "command": "python3",
      "args": ["/path/to/opnsense-mcp-server/server.py"],
      "env": {
        "OPNSENSE_URL": "https://your-opnsense.local",
        "OPNSENSE_API_KEY": "your_api_key",
        "OPNSENSE_API_SECRET": "your_api_secret"
      }
    }
  }
}
```

## Available Tools

### Alias Management

- **list_aliases** - Get all firewall aliases
- **get_alias** - Get specific alias details by UUID
- **add_alias** - Create a new alias (host, network, port, url, etc.)
- **update_alias** - Update existing alias
- **delete_alias** - Delete an alias
- **toggle_alias** - Enable/disable an alias
- **list_countries** - Get available countries for GeoIP aliases
- **export_aliases** - Export all aliases
- **import_aliases** - Import aliases from data

### Filter Rules

- **search_filter_rules** - Search and list filter rules
- **get_filter_rule** - Get specific rule details
- **add_filter_rule** - Create a new firewall rule
- **update_filter_rule** - Update existing rule
- **delete_filter_rule** - Delete a rule
- **toggle_filter_rule** - Enable/disable a rule
- **toggle_rule_logging** - Enable/disable logging for a rule
- **move_rule_before** - Reorder rules

### Destination NAT (Port Forwarding)

- **add_dnat_rule** - Create port forward rule
- **update_dnat_rule** - Update port forward rule
- **delete_dnat_rule** - Delete port forward rule

### Source NAT (Outbound NAT)

- **add_source_nat_rule** - Create outbound NAT rule
- **update_source_nat_rule** - Update outbound NAT rule
- **toggle_source_nat_rule** - Enable/disable outbound NAT rule

### One-to-One NAT

- **add_one_to_one_nat** - Create 1:1 NAT rule
- **get_one_to_one_nat** - Get 1:1 NAT rule details
- **move_one_to_one_before** - Reorder 1:1 NAT rules

### NPT (IPv6 Network Prefix Translation)

- **add_npt_rule** - Create NPT rule
- **search_npt_rules** - Search NPT rules

### Groups & Categories

- **add_rule_group** - Create rule group
- **search_rule_groups** - Search rule groups
- **add_rule_category** - Create rule category

### Configuration Management

- **create_savepoint** - Create config savepoint for rollback
- **apply_changes** - Apply firewall changes (with optional auto-rollback)
- **cancel_rollback** - Confirm changes and prevent rollback
- **revert_config** - Revert to previous configuration

## Usage Examples

### Managing Aliases

```
# List all aliases
list_aliases

# Create a new host alias
add_alias with name="WebServers" alias_type="host" content="10.0.1.10,10.0.1.11" description="Web server pool"

# Get specific alias
get_alias with uuid="12345678-1234-1234-1234-123456789abc"

# Delete an alias
delete_alias with uuid="12345678-1234-1234-1234-123456789abc"
```

### Managing Firewall Rules

```
# Search all rules
search_filter_rules

# Create a new allow rule
add_filter_rule with interface="wan" direction="in" action="pass" source="any" destination="WebServers" dest_port="443" protocol="tcp" description="Allow HTTPS to web servers"

# Block a specific IP
add_filter_rule with interface="wan" direction="in" action="block" source="192.0.2.100" destination="any" description="Block malicious IP"

# Enable logging for a rule
toggle_rule_logging with uuid="12345678-1234-1234-1234-123456789abc" log=true

# Disable a rule
toggle_filter_rule with uuid="12345678-1234-1234-1234-123456789abc" enabled=false
```

### Port Forwarding (Destination NAT)

```
# Forward external port 8080 to internal server on port 80
add_dnat_rule with interface="wan" protocol="tcp" destination="WANAddress" dest_port="8080" redirect_target_ip="10.0.1.10" redirect_target_port="80" description="Web server port forward"
```

### Outbound NAT

```
# Create outbound NAT rule
add_source_nat_rule with interface="wan" source="10.0.1.0/24" destination="any" description="NAT for internal network"
```

### Safe Change Management

```
# Create a savepoint before making changes
create_savepoint

# Apply changes with automatic rollback protection (60 second timeout)
# If you don't confirm within 60 seconds, config reverts automatically
apply_changes with rollback_revision="revision_id_from_savepoint"

# Test your changes, then confirm within 60 seconds
cancel_rollback with rollback_revision="revision_id_from_savepoint"

# Or apply without rollback protection
apply_changes
```

## Important Notes

### Authentication

- Uses API Key + API Secret (not username/password)
- API credentials are sent via HTTP Basic Auth
- Supports self-signed certificates (SSL verification disabled)

### Configuration Changes

- **Changes are NOT applied automatically**
- After creating/modifying rules, you MUST call `apply_changes`
- Use `create_savepoint` before risky changes for rollback capability
- The 60-second rollback window protects against lockouts

### Rule UUIDs

- All rules are identified by UUID (not integer IDs)
- Use search/list functions to find UUIDs
- UUIDs persist across reboots

### Interface Names

Common interface names:
- `wan` - WAN interface
- `lan` - LAN interface
- `opt1`, `opt2`, etc. - Optional interfaces
- Check your OPNsense config for exact names

## API Documentation

Based on OPNsense Core Firewall API:
- https://docs.opnsense.org/development/api/core/firewall.html

## Troubleshooting

### API Access Denied

1. Verify API credentials are correct
2. Check that API access is enabled for the user
3. Ensure the user has sufficient privileges

### SSL Certificate Errors

The server disables SSL verification by default for self-signed certs. For production:
1. Use a valid SSL certificate on OPNsense
2. Modify `verify=True` in `server.py` if needed

### Changes Not Applied

Remember to call `apply_changes` after making modifications. Changes are staged until applied.

### Connection Timeouts

- Default timeout is 30 seconds
- Increase in `server.py` if needed for slow connections
- Check firewall access from the server running this MCP

## Security Considerations

- Store API credentials securely (use `.env` file, never commit)
- Use HTTPS for OPNsense API endpoint
- Consider IP restrictions on API access in OPNsense
- Use read-only API user for monitoring-only scenarios
- Always use savepoints before making significant changes

## License

MIT License - see LICENSE file for details
