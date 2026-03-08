#!/usr/bin/env python3
import os
import json
import httpx
from fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

OPNSENSE_URL = os.getenv("OPNSENSE_URL", "")
OPNSENSE_API_KEY = os.getenv("OPNSENSE_API_KEY", "")
OPNSENSE_API_SECRET = os.getenv("OPNSENSE_API_SECRET", "")

if not OPNSENSE_URL.endswith('/'):
    OPNSENSE_URL += '/'

BASE_URL = f"{OPNSENSE_URL}api"

mcp = FastMCP("opnsense-firewall-mcp")

async def opnsense_request(endpoint, method="GET", data=None, params=None):
    """Make authenticated request to OPNsense API"""
    url = f"{BASE_URL}{endpoint}"
    auth = httpx.BasicAuth(OPNSENSE_API_KEY, OPNSENSE_API_SECRET)

    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        if method == "GET":
            r = await client.get(url, auth=auth, params=params)
        elif method == "POST":
            r = await client.post(url, auth=auth, json=data)
        elif method == "DELETE":
            r = await client.delete(url, auth=auth)

        r.raise_for_status()
        return r.json()

# ========== ALIAS MANAGEMENT ==========

@mcp.tool()
async def list_aliases() -> str:
    """Get all firewall aliases"""
    result = await opnsense_request("/firewall/alias/get")
    return json.dumps(result, indent=2)

@mcp.tool()
async def get_alias(uuid: str) -> str:
    """Get details of a specific alias by UUID"""
    result = await opnsense_request(f"/firewall/alias/get_item/{uuid}")
    return json.dumps(result, indent=2)

@mcp.tool()
async def add_alias(name: str, alias_type: str, content: str, description: str = "") -> str:
    """
    Create a new firewall alias

    Args:
        name: Alias name
        alias_type: Type (host, network, port, url, etc.)
        content: Alias content/values
        description: Optional description
    """
    data = {
        "alias": {
            "name": name,
            "type": alias_type,
            "content": content,
            "description": description
        }
    }
    result = await opnsense_request("/firewall/alias/add_item", method="POST", data=data)
    return json.dumps(result, indent=2)

@mcp.tool()
async def update_alias(uuid: str, name: str = None, alias_type: str = None,
                      content: str = None, description: str = None) -> str:
    """Update an existing alias"""
    # Get current alias first
    current = await opnsense_request(f"/firewall/alias/get_item/{uuid}")

    # Update only provided fields
    alias_data = current.get("alias", {})
    if name:
        alias_data["name"] = name
    if alias_type:
        alias_data["type"] = alias_type
    if content:
        alias_data["content"] = content
    if description is not None:
        alias_data["description"] = description

    data = {"alias": alias_data}
    result = await opnsense_request(f"/firewall/alias/set_item/{uuid}", method="POST", data=data)
    return json.dumps(result, indent=2)

@mcp.tool()
async def delete_alias(uuid: str) -> str:
    """Delete an alias by UUID"""
    result = await opnsense_request(f"/firewall/alias/del_item/{uuid}", method="POST")
    return json.dumps(result, indent=2)

@mcp.tool()
async def toggle_alias(uuid: str, enabled: bool = None) -> str:
    """Enable or disable an alias"""
    endpoint = f"/firewall/alias/toggle_item/{uuid}"
    if enabled is not None:
        endpoint += f"/{1 if enabled else 0}"
    result = await opnsense_request(endpoint, method="POST")
    return json.dumps(result, indent=2)

@mcp.tool()
async def list_countries() -> str:
    """Get list of available countries for GeoIP aliases"""
    result = await opnsense_request("/firewall/alias/list_countries")
    return json.dumps(result, indent=2)

@mcp.tool()
async def export_aliases() -> str:
    """Export all aliases"""
    result = await opnsense_request("/firewall/alias/export", method="POST")
    return json.dumps(result, indent=2)

@mcp.tool()
async def import_aliases(alias_data: str) -> str:
    """Import aliases from data"""
    data = {"data": alias_data}
    result = await opnsense_request("/firewall/alias/import", method="POST", data=data)
    return json.dumps(result, indent=2)

# ========== FILTER RULES ==========

@mcp.tool()
async def search_filter_rules(search_phrase: str = "", current_page: int = 1,
                             rows_per_page: int = 100) -> str:
    """Search firewall filter rules"""
    params = {
        "searchPhrase": search_phrase,
        "current": current_page,
        "rowCount": rows_per_page
    }
    result = await opnsense_request("/firewall/filter/search_rule", params=params)
    return json.dumps(result, indent=2)

@mcp.tool()
async def get_filter_rule(uuid: str) -> str:
    """Get details of a specific filter rule by UUID"""
    result = await opnsense_request(f"/firewall/filter/get_rule/{uuid}")
    return json.dumps(result, indent=2)

@mcp.tool()
async def add_filter_rule(interface: str, direction: str, action: str,
                         source: str = "any", destination: str = "any",
                         description: str = "", protocol: str = "any",
                         source_port: str = "", dest_port: str = "",
                         enabled: bool = True, log: bool = False) -> str:
    """
    Create a new firewall filter rule

    Args:
        interface: Interface name (e.g., wan, lan, opt1)
        direction: Direction (in, out)
        action: Action (pass, block, reject)
        source: Source address/alias (default: any)
        destination: Destination address/alias (default: any)
        description: Rule description
        protocol: Protocol (tcp, udp, icmp, any)
        source_port: Source port or port range
        dest_port: Destination port or port range
        enabled: Enable rule (default: True)
        log: Enable logging (default: False)
    """
    data = {
        "rule": {
            "interface": interface,
            "direction": direction,
            "action": action,
            "source_net": source,
            "destination_net": destination,
            "description": description,
            "protocol": protocol,
            "enabled": "1" if enabled else "0",
            "log": "1" if log else "0"
        }
    }

    if source_port:
        data["rule"]["source_port"] = source_port
    if dest_port:
        data["rule"]["destination_port"] = dest_port

    result = await opnsense_request("/firewall/filter/add_rule", method="POST", data=data)
    return json.dumps(result, indent=2)

@mcp.tool()
async def update_filter_rule(uuid: str, interface: str = None, direction: str = None,
                            action: str = None, source: str = None, destination: str = None,
                            description: str = None, protocol: str = None,
                            enabled: bool = None, log: bool = None) -> str:
    """Update an existing filter rule"""
    # Get current rule first
    current = await opnsense_request(f"/firewall/filter/get_rule/{uuid}")

    # Update only provided fields
    rule_data = current.get("rule", {})
    if interface:
        rule_data["interface"] = interface
    if direction:
        rule_data["direction"] = direction
    if action:
        rule_data["action"] = action
    if source:
        rule_data["source_net"] = source
    if destination:
        rule_data["destination_net"] = destination
    if description is not None:
        rule_data["description"] = description
    if protocol:
        rule_data["protocol"] = protocol
    if enabled is not None:
        rule_data["enabled"] = "1" if enabled else "0"
    if log is not None:
        rule_data["log"] = "1" if log else "0"

    data = {"rule": rule_data}
    result = await opnsense_request(f"/firewall/filter/set_rule/{uuid}", method="POST", data=data)
    return json.dumps(result, indent=2)

@mcp.tool()
async def delete_filter_rule(uuid: str) -> str:
    """Delete a filter rule by UUID"""
    result = await opnsense_request(f"/firewall/filter/del_rule/{uuid}", method="POST")
    return json.dumps(result, indent=2)

@mcp.tool()
async def toggle_filter_rule(uuid: str, enabled: bool = None) -> str:
    """Enable or disable a filter rule"""
    endpoint = f"/firewall/filter/toggle_rule/{uuid}"
    if enabled is not None:
        endpoint += f"/{1 if enabled else 0}"
    result = await opnsense_request(endpoint, method="POST")
    return json.dumps(result, indent=2)

@mcp.tool()
async def toggle_rule_logging(uuid: str, log: bool) -> str:
    """Enable or disable logging for a specific rule"""
    endpoint = f"/firewall/filter/toggle_rule_log/{uuid}/{1 if log else 0}"
    result = await opnsense_request(endpoint)
    return json.dumps(result, indent=2)

@mcp.tool()
async def move_rule_before(selected_uuid: str, target_uuid: str) -> str:
    """Move a rule before another rule (reorder rules)"""
    result = await opnsense_request(
        f"/firewall/filter/move_rule_before/{selected_uuid}/{target_uuid}",
        method="POST"
    )
    return json.dumps(result, indent=2)

# ========== NAT RULES (Destination NAT / Port Forwarding) ==========

@mcp.tool()
async def add_dnat_rule(interface: str, protocol: str, destination: str, dest_port: str,
                       redirect_target_ip: str, redirect_target_port: str,
                       description: str = "", enabled: bool = True) -> str:
    """
    Create a destination NAT (port forward) rule

    Args:
        interface: Interface (e.g., wan)
        protocol: Protocol (tcp, udp, tcp/udp)
        destination: Destination IP/alias
        dest_port: Destination port
        redirect_target_ip: Internal IP to forward to
        redirect_target_port: Internal port to forward to
        description: Rule description
        enabled: Enable rule
    """
    data = {
        "rule": {
            "interface": interface,
            "protocol": protocol,
            "destination": destination,
            "destination_port": dest_port,
            "target": redirect_target_ip,
            "local-port": redirect_target_port,
            "description": description,
            "enabled": "1" if enabled else "0"
        }
    }
    result = await opnsense_request("/firewall/d_nat/add_rule", method="POST", data=data)
    return json.dumps(result, indent=2)

@mcp.tool()
async def update_dnat_rule(uuid: str, interface: str = None, protocol: str = None,
                          redirect_target_ip: str = None, description: str = None,
                          enabled: bool = None) -> str:
    """Update a destination NAT rule"""
    data = {"rule": {}}
    if interface:
        data["rule"]["interface"] = interface
    if protocol:
        data["rule"]["protocol"] = protocol
    if redirect_target_ip:
        data["rule"]["target"] = redirect_target_ip
    if description is not None:
        data["rule"]["description"] = description
    if enabled is not None:
        data["rule"]["enabled"] = "1" if enabled else "0"

    result = await opnsense_request(f"/firewall/d_nat/set_rule/{uuid}", method="POST", data=data)
    return json.dumps(result, indent=2)

@mcp.tool()
async def delete_dnat_rule(uuid: str) -> str:
    """Delete a destination NAT rule"""
    result = await opnsense_request(f"/firewall/d_nat/del_rule/{uuid}", method="POST")
    return json.dumps(result, indent=2)

# ========== SOURCE NAT (Outbound NAT) ==========

@mcp.tool()
async def add_source_nat_rule(interface: str, source: str, destination: str,
                             target: str = "", description: str = "",
                             enabled: bool = True) -> str:
    """
    Create a source NAT (outbound NAT) rule

    Args:
        interface: Interface
        source: Source network/alias
        destination: Destination network/alias
        target: NAT target address (leave empty for interface address)
        description: Rule description
        enabled: Enable rule
    """
    data = {
        "rule": {
            "interface": interface,
            "source": source,
            "destination": destination,
            "target": target,
            "description": description,
            "disabled": "0" if enabled else "1"
        }
    }
    result = await opnsense_request("/firewall/source_nat/add_rule", method="POST", data=data)
    return json.dumps(result, indent=2)

@mcp.tool()
async def update_source_nat_rule(uuid: str, interface: str = None, source: str = None,
                                destination: str = None, target: str = None,
                                description: str = None, enabled: bool = None) -> str:
    """Update a source NAT rule"""
    data = {"rule": {}}
    if interface:
        data["rule"]["interface"] = interface
    if source:
        data["rule"]["source"] = source
    if destination:
        data["rule"]["destination"] = destination
    if target is not None:
        data["rule"]["target"] = target
    if description is not None:
        data["rule"]["description"] = description
    if enabled is not None:
        data["rule"]["disabled"] = "0" if enabled else "1"

    result = await opnsense_request(f"/firewall/source_nat/set_rule/{uuid}", method="POST", data=data)
    return json.dumps(result, indent=2)

@mcp.tool()
async def toggle_source_nat_rule(uuid: str, enabled: bool = None) -> str:
    """Enable or disable a source NAT rule"""
    endpoint = f"/firewall/source_nat/toggle_rule/{uuid}"
    if enabled is not None:
        endpoint += f"/{0 if enabled else 1}"  # Note: disabled flag is inverted
    result = await opnsense_request(endpoint, method="POST")
    return json.dumps(result, indent=2)

# ========== ONE-TO-ONE NAT ==========

@mcp.tool()
async def add_one_to_one_nat(interface: str, external_ip: str, internal_ip: str,
                            description: str = "", enabled: bool = True) -> str:
    """
    Create a one-to-one NAT rule

    Args:
        interface: Interface
        external_ip: External IP address
        internal_ip: Internal IP address
        description: Rule description
        enabled: Enable rule
    """
    data = {
        "rule": {
            "interface": interface,
            "external": external_ip,
            "destination": internal_ip,
            "description": description,
            "enabled": "1" if enabled else "0"
        }
    }
    result = await opnsense_request("/firewall/one_to_one/add_rule", method="POST", data=data)
    return json.dumps(result, indent=2)

@mcp.tool()
async def get_one_to_one_nat(uuid: str) -> str:
    """Get details of a one-to-one NAT rule"""
    result = await opnsense_request(f"/firewall/one_to_one/get_rule/{uuid}")
    return json.dumps(result, indent=2)

@mcp.tool()
async def move_one_to_one_before(selected_uuid: str, target_uuid: str) -> str:
    """Move a one-to-one NAT rule before another rule"""
    result = await opnsense_request(
        f"/firewall/one_to_one/move_rule_before/{selected_uuid}/{target_uuid}",
        method="POST"
    )
    return json.dumps(result, indent=2)

# ========== NPT (Network Prefix Translation) ==========

@mcp.tool()
async def add_npt_rule(interface: str, source_prefix: str, destination_prefix: str,
                      description: str = "", enabled: bool = True) -> str:
    """
    Create an NPT (IPv6 Network Prefix Translation) rule

    Args:
        interface: Interface
        source_prefix: Source IPv6 prefix
        destination_prefix: Destination IPv6 prefix
        description: Rule description
        enabled: Enable rule
    """
    data = {
        "rule": {
            "interface": interface,
            "src": source_prefix,
            "dst": destination_prefix,
            "description": description,
            "enabled": "1" if enabled else "0"
        }
    }
    result = await opnsense_request("/firewall/npt/add_rule", method="POST", data=data)
    return json.dumps(result, indent=2)

@mcp.tool()
async def search_npt_rules(search_phrase: str = "") -> str:
    """Search NPT rules"""
    params = {"searchPhrase": search_phrase}
    result = await opnsense_request("/firewall/npt/search_rule", params=params)
    return json.dumps(result, indent=2)

# ========== GROUPS & CATEGORIES ==========

@mcp.tool()
async def add_rule_group(name: str, description: str = "") -> str:
    """Create a new rule group"""
    data = {
        "group": {
            "name": name,
            "description": description
        }
    }
    result = await opnsense_request("/firewall/group/add_item", method="POST", data=data)
    return json.dumps(result, indent=2)

@mcp.tool()
async def search_rule_groups(search_phrase: str = "") -> str:
    """Search rule groups"""
    params = {"searchPhrase": search_phrase}
    result = await opnsense_request("/firewall/group/search_item", params=params)
    return json.dumps(result, indent=2)

@mcp.tool()
async def add_rule_category(name: str, description: str = "") -> str:
    """Create a new rule category"""
    data = {
        "category": {
            "name": name,
            "description": description
        }
    }
    result = await opnsense_request("/firewall/category/add_item", method="POST", data=data)
    return json.dumps(result, indent=2)

# ========== CONFIGURATION MANAGEMENT ==========

@mcp.tool()
async def create_savepoint() -> str:
    """Create a configuration savepoint for rollback capability"""
    result = await opnsense_request("/firewall/filter/savepoint", method="POST")
    return json.dumps(result, indent=2)

@mcp.tool()
async def apply_changes(rollback_revision: str = "") -> str:
    """
    Apply firewall configuration changes

    Args:
        rollback_revision: Optional revision ID for automatic rollback (60 second timeout)

    Note: If rollback_revision is provided, you must call cancel_rollback within 60 seconds
    to confirm changes, otherwise the configuration will automatically revert.
    """
    endpoint = "/firewall/filter/apply"
    if rollback_revision:
        endpoint += f"/{rollback_revision}"
    result = await opnsense_request(endpoint, method="POST")
    return json.dumps(result, indent=2)

@mcp.tool()
async def cancel_rollback(rollback_revision: str) -> str:
    """
    Cancel automatic rollback and confirm changes

    Args:
        rollback_revision: The revision ID from the apply_changes call

    Call this within 60 seconds of apply_changes to prevent automatic reversion.
    """
    result = await opnsense_request(
        f"/firewall/filter/cancel_rollback/{rollback_revision}",
        method="POST"
    )
    return json.dumps(result, indent=2)

@mcp.tool()
async def revert_config(revision: str) -> str:
    """
    Revert to a previous configuration revision

    Args:
        revision: The revision ID to revert to
    """
    result = await opnsense_request(f"/firewall/filter/revert/{revision}", method="POST")
    return json.dumps(result, indent=2)

if __name__ == "__main__":
    if not OPNSENSE_URL or not OPNSENSE_API_KEY or not OPNSENSE_API_SECRET:
        print("Error: Set OPNSENSE_URL, OPNSENSE_API_KEY, and OPNSENSE_API_SECRET")
        print("Generate API credentials in OPNsense: System -> Access -> Users -> Edit User -> API Keys")
        exit(1)
    mcp.run()
