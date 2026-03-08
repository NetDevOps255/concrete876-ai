#!/usr/bin/env python3
"""
NetBox MCP Server - Full CRUD access to NetBox infrastructure data via MCP protocol.
Supports: get, create, update (partial/full), and delete for all major NetBox object types.
"""

import os
import sys
import logging
from typing import Any, Optional
from dotenv import load_dotenv
import pynetbox
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger("netbox-mcp-server")

# NetBox configuration
NETBOX_URL = os.getenv("NETBOX_URL")
NETBOX_TOKEN = os.getenv("NETBOX_TOKEN")
NETBOX_SSL_VERIFY = os.getenv("NETBOX_SSL_VERIFY", "true").lower() == "true"

if not NETBOX_URL or not NETBOX_TOKEN:
    logger.error("NETBOX_URL and NETBOX_TOKEN environment variables are required")
    sys.exit(1)

# Initialize NetBox API client
try:
    nb = pynetbox.api(NETBOX_URL, token=NETBOX_TOKEN)
    nb.http_session.verify = NETBOX_SSL_VERIFY
    logger.info(f"Connected to NetBox at {NETBOX_URL}")
except Exception as e:
    logger.error(f"Failed to connect to NetBox: {e}")
    sys.exit(1)

# Create MCP server instance
app = Server("netbox-mcp-server")

# Supported NetBox object types mapping
OBJECT_TYPES = {
    # DCIM
    "sites": nb.dcim.sites,
    "racks": nb.dcim.racks,
    "devices": nb.dcim.devices,
    "device_types": nb.dcim.device_types,
    "device_roles": nb.dcim.device_roles,
    "manufacturers": nb.dcim.manufacturers,
    "platforms": nb.dcim.platforms,
    "interfaces": nb.dcim.interfaces,
    "cables": nb.dcim.cables,
    "power_ports": nb.dcim.power_ports,
    "power_outlets": nb.dcim.power_outlets,
    "console_ports": nb.dcim.console_ports,
    "console_server_ports": nb.dcim.console_server_ports,

    # IPAM
    "ip_addresses": nb.ipam.ip_addresses,
    "prefixes": nb.ipam.prefixes,
    "vlans": nb.ipam.vlans,
    "vlan_groups": nb.ipam.vlan_groups,
    "vrfs": nb.ipam.vrfs,
    "aggregates": nb.ipam.aggregates,

    # Circuits
    "circuits": nb.circuits.circuits,
    "circuit_types": nb.circuits.circuit_types,
    "providers": nb.circuits.providers,

    # Virtualization
    "virtual_machines": nb.virtualization.virtual_machines,
    "clusters": nb.virtualization.clusters,
    "cluster_types": nb.virtualization.cluster_types,

    # Tenancy
    "tenants": nb.tenancy.tenants,
    "tenant_groups": nb.tenancy.tenant_groups,
}

OBJECT_TYPES_LIST = sorted(OBJECT_TYPES.keys())


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available NetBox MCP tools."""
    return [
        Tool(
            name="get_objects",
            description=(
                "Retrieve a list of NetBox objects by type with optional filters. "
                f"Supported types: {', '.join(OBJECT_TYPES_LIST)}."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "object_type": {
                        "type": "string",
                        "description": f"NetBox object type. Options: {', '.join(OBJECT_TYPES_LIST)}",
                        "enum": OBJECT_TYPES_LIST
                    },
                    "filters": {
                        "type": "object",
                        "description": "Key/value filters (e.g., {'site': 'dc1', 'status': 'active'})",
                        "additionalProperties": True
                    },
                    "fields": {
                        "type": "array",
                        "description": "Specific fields to return (omit for full object)",
                        "items": {"type": "string"}
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return (default: 50)",
                        "default": 50
                    }
                },
                "required": ["object_type"]
            }
        ),
        Tool(
            name="get_object_by_id",
            description="Get full details of a specific NetBox object by its numeric ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_type": {
                        "type": "string",
                        "description": f"NetBox object type. Options: {', '.join(OBJECT_TYPES_LIST)}",
                        "enum": OBJECT_TYPES_LIST
                    },
                    "object_id": {
                        "type": "integer",
                        "description": "Numeric ID of the object in NetBox"
                    },
                    "fields": {
                        "type": "array",
                        "description": "Specific fields to return (omit for full object)",
                        "items": {"type": "string"}
                    }
                },
                "required": ["object_type", "object_id"]
            }
        ),
        Tool(
            name="create_object",
            description=(
                "Create a new NetBox object. Provide all required fields for the object type. "
                "Returns the created object with its assigned ID. "
                "Example: create a device with name, device_type, device_role, site, and status."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "object_type": {
                        "type": "string",
                        "description": f"NetBox object type to create. Options: {', '.join(OBJECT_TYPES_LIST)}",
                        "enum": OBJECT_TYPES_LIST
                    },
                    "data": {
                        "type": "object",
                        "description": (
                            "Object fields as key/value pairs. Required fields vary by type. "
                            "For nested/foreign-key fields, use the numeric ID "
                            "(e.g., {'device_type': 12, 'site': 3}). "
                            "For tags, use a list of slugs: {'tags': ['prod', 'core']}."
                        ),
                        "additionalProperties": True
                    }
                },
                "required": ["object_type", "data"]
            }
        ),
        Tool(
            name="update_object",
            description=(
                "Update an existing NetBox object by ID. "
                "Use 'partial=true' (default) for PATCH — only provided fields are changed. "
                "Use 'partial=false' for full PUT — all required fields must be supplied. "
                "Returns the updated object."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "object_type": {
                        "type": "string",
                        "description": f"NetBox object type. Options: {', '.join(OBJECT_TYPES_LIST)}",
                        "enum": OBJECT_TYPES_LIST
                    },
                    "object_id": {
                        "type": "integer",
                        "description": "Numeric ID of the object to update"
                    },
                    "data": {
                        "type": "object",
                        "description": (
                            "Fields to update. For partial updates only include changed fields. "
                            "For foreign keys, provide the numeric ID. "
                            "For tags, provide the full desired list of slugs."
                        ),
                        "additionalProperties": True
                    },
                    "partial": {
                        "type": "boolean",
                        "description": "True = PATCH (update only supplied fields). False = PUT (replace full object). Default: true",
                        "default": True
                    }
                },
                "required": ["object_type", "object_id", "data"]
            }
        ),
        Tool(
            name="delete_object",
            description=(
                "Permanently delete a NetBox object by ID. "
                "This action is irreversible — confirm the ID before calling. "
                "Returns confirmation of deletion."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "object_type": {
                        "type": "string",
                        "description": f"NetBox object type. Options: {', '.join(OBJECT_TYPES_LIST)}",
                        "enum": OBJECT_TYPES_LIST
                    },
                    "object_id": {
                        "type": "integer",
                        "description": "Numeric ID of the object to delete"
                    }
                },
                "required": ["object_type", "object_id"]
            }
        ),
        Tool(
            name="get_changelogs",
            description="Retrieve audit trail / change history for NetBox objects. Shows who changed what and when.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filters": {
                        "type": "object",
                        "description": "Filters (e.g., {'object_type': 'dcim.device', 'object_id': 123, 'user_name': 'admin'})",
                        "additionalProperties": True
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max changelog entries to return (default: 50)",
                        "default": 50
                    }
                },
                "required": []
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Dispatch tool calls to handlers."""
    try:
        if name == "get_objects":
            return await handle_get_objects(arguments)
        elif name == "get_object_by_id":
            return await handle_get_object_by_id(arguments)
        elif name == "create_object":
            return await handle_create_object(arguments)
        elif name == "update_object":
            return await handle_update_object(arguments)
        elif name == "delete_object":
            return await handle_delete_object(arguments)
        elif name == "get_changelogs":
            return await handle_get_changelogs(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")
    except pynetbox.RequestError as e:
        logger.error(f"NetBox API error in {name}: {e}", exc_info=True)
        return [TextContent(type="text", text=f"NetBox API Error: {e.error}")]
    except Exception as e:
        logger.error(f"Error in tool {name}: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _validate_object_type(object_type: str) -> None:
    if object_type not in OBJECT_TYPES:
        raise ValueError(
            f"Invalid object_type '{object_type}'. Must be one of: {', '.join(OBJECT_TYPES_LIST)}"
        )


def _serialize(obj: Any, fields: Optional[list] = None) -> dict:
    """Serialize a pynetbox Record, optionally filtering to specific fields."""
    if fields:
        return {field: getattr(obj, field, None) for field in fields}
    return dict(obj)


# ─── Read handlers ────────────────────────────────────────────────────────────

async def handle_get_objects(arguments: dict) -> list[TextContent]:
    object_type = arguments.get("object_type")
    filters = arguments.get("filters", {})
    fields = arguments.get("fields")
    limit = arguments.get("limit", 50)

    _validate_object_type(object_type)
    logger.info(f"GET {object_type} filters={filters} limit={limit}")

    endpoint = OBJECT_TYPES[object_type]
    results = list(endpoint.filter(**filters))[:limit]
    objects = [_serialize(obj, fields) for obj in results]

    return [TextContent(type="text", text=f"Found {len(objects)} {object_type}:\n\n{objects}")]


async def handle_get_object_by_id(arguments: dict) -> list[TextContent]:
    object_type = arguments.get("object_type")
    object_id = arguments.get("object_id")
    fields = arguments.get("fields")

    _validate_object_type(object_type)
    logger.info(f"GET {object_type} id={object_id}")

    obj = OBJECT_TYPES[object_type].get(object_id)
    if not obj:
        return [TextContent(type="text", text=f"No {object_type} found with ID {object_id}")]

    return [TextContent(type="text", text=f"{object_type} (ID: {object_id}):\n\n{_serialize(obj, fields)}")]


# ─── Write handlers ───────────────────────────────────────────────────────────

async def handle_create_object(arguments: dict) -> list[TextContent]:
    object_type = arguments.get("object_type")
    data = arguments.get("data", {})

    _validate_object_type(object_type)
    if not data:
        raise ValueError("'data' must be a non-empty dict of fields to create the object.")

    logger.info(f"CREATE {object_type} data={data}")

    endpoint = OBJECT_TYPES[object_type]
    created = endpoint.create(**data)

    return [TextContent(
        type="text",
        text=f"Successfully created {object_type} (ID: {created.id}):\n\n{_serialize(created)}"
    )]


async def handle_update_object(arguments: dict) -> list[TextContent]:
    object_type = arguments.get("object_type")
    object_id = arguments.get("object_id")
    data = arguments.get("data", {})
    partial = arguments.get("partial", True)

    _validate_object_type(object_type)
    if not data:
        raise ValueError("'data' must be a non-empty dict of fields to update.")

    logger.info(f"{'PATCH' if partial else 'PUT'} {object_type} id={object_id} data={data}")

    obj = OBJECT_TYPES[object_type].get(object_id)
    if not obj:
        return [TextContent(type="text", text=f"No {object_type} found with ID {object_id}")]

    if partial:
        # PATCH: set only provided attributes then save
        for key, value in data.items():
            setattr(obj, key, value)
        obj.save()
    else:
        # Full PUT: update() replaces the full object payload
        obj.update(data)

    # Re-fetch to get the fully resolved object after save
    updated = OBJECT_TYPES[object_type].get(object_id)

    return [TextContent(
        type="text",
        text=f"Successfully updated {object_type} (ID: {object_id}):\n\n{_serialize(updated)}"
    )]


async def handle_delete_object(arguments: dict) -> list[TextContent]:
    object_type = arguments.get("object_type")
    object_id = arguments.get("object_id")

    _validate_object_type(object_type)
    logger.info(f"DELETE {object_type} id={object_id}")

    obj = OBJECT_TYPES[object_type].get(object_id)
    if not obj:
        return [TextContent(type="text", text=f"No {object_type} found with ID {object_id}")]

    obj_repr = str(obj)
    obj.delete()

    return [TextContent(
        type="text",
        text=f"Successfully deleted {object_type} '{obj_repr}' (ID: {object_id})"
    )]


# ─── Changelog handler ────────────────────────────────────────────────────────

async def handle_get_changelogs(arguments: dict) -> list[TextContent]:
    filters = arguments.get("filters", {})
    limit = arguments.get("limit", 50)

    logger.info(f"GET changelogs filters={filters}")

    results = list(nb.extras.object_changes.filter(**filters))[:limit]

    changes = [
        {
            "id": log.id,
            "time": str(log.time),
            "user": str(log.user_name),
            "action": log.action.label if hasattr(log.action, "label") else str(log.action),
            "object_type": log.changed_object_type,
            "object_id": log.changed_object_id,
            "object": str(log.changed_object) if log.changed_object else None,
        }
        for log in results
    ]

    return [TextContent(type="text", text=f"Found {len(changes)} changelog entries:\n\n{changes}")]


# ─── Entrypoint ───────────────────────────────────────────────────────────────

async def main():
    logger.info("Starting NetBox MCP server")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())