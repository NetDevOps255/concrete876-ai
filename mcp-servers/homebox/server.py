#!/usr/bin/env python3
"""
Homebox MCP Server - Provides access to Homebox home inventory via MCP protocol.
"""

import os
import sys
import logging
import json
import mimetypes
from pathlib import Path
from typing import Any, Optional
from dotenv import load_dotenv
import httpx
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
logger = logging.getLogger("homebox-mcp-server")

# Homebox configuration
HOMEBOX_URL = os.getenv("HOMEBOX_URL", "").rstrip("/")
HOMEBOX_TOKEN = os.getenv("HOMEBOX_TOKEN")
HOMEBOX_USERNAME = os.getenv("HOMEBOX_USERNAME")
HOMEBOX_PASSWORD = os.getenv("HOMEBOX_PASSWORD")
HOMEBOX_SSL_VERIFY = os.getenv("HOMEBOX_SSL_VERIFY", "true").lower() == "true"

if not HOMEBOX_URL:
    logger.error("HOMEBOX_URL environment variable is required")
    sys.exit(1)

if not HOMEBOX_TOKEN and not (HOMEBOX_USERNAME and HOMEBOX_PASSWORD):
    logger.error("Either HOMEBOX_TOKEN or both HOMEBOX_USERNAME and HOMEBOX_PASSWORD are required")
    sys.exit(1)


class HomeboxClient:
    def __init__(self):
        self.base_url = f"{HOMEBOX_URL}/api/v1"
        self.token: Optional[str] = HOMEBOX_TOKEN
        self.client = httpx.AsyncClient(verify=HOMEBOX_SSL_VERIFY, timeout=30.0)

    async def _authenticate(self):
        """Authenticate with username/password and store the token."""
        resp = await self.client.post(
            f"{self.base_url}/users/login",
            json={"username": HOMEBOX_USERNAME, "password": HOMEBOX_PASSWORD, "stayLoggedIn": True}
        )
        resp.raise_for_status()
        self.token = resp.json()["token"]
        logger.info("Successfully authenticated with Homebox")

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        if not self.token:
            await self._authenticate()

        url = f"{self.base_url}{path}"
        resp = await self.client.request(method, url, headers=self._headers(), **kwargs)

        # Re-authenticate on 401 (token expired) then retry once
        if resp.status_code == 401 and HOMEBOX_USERNAME:
            logger.info("Token expired, re-authenticating")
            await self._authenticate()
            resp = await self.client.request(method, url, headers=self._headers(), **kwargs)

        resp.raise_for_status()

        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    async def search_items(self, query: str = "", locations: list = None,
                           labels: list = None, page: int = 1, page_size: int = 50) -> dict:
        params = {"page": page, "pageSize": page_size}
        if query:
            params["q"] = query
        if locations:
            params["locations"] = locations
        if labels:
            params["labels"] = labels
        return await self._request("GET", "/items", params=params)

    async def get_item(self, item_id: str) -> dict:
        return await self._request("GET", f"/items/{item_id}")

    async def create_item(self, data: dict) -> dict:
        return await self._request("POST", "/items", json=data)

    async def update_item(self, item_id: str, data: dict) -> dict:
        return await self._request("PUT", f"/items/{item_id}", json=data)

    async def delete_item(self, item_id: str) -> None:
        await self._request("DELETE", f"/items/{item_id}")

    async def get_item_attachments(self, item_id: str) -> list:
        return await self._request("GET", f"/items/{item_id}/attachments")

    async def get_locations(self) -> list:
        return await self._request("GET", "/locations")

    async def create_location(self, data: dict) -> dict:
        return await self._request("POST", "/locations", json=data)

    async def get_labels(self) -> list:
        return await self._request("GET", "/labels")

    async def create_label(self, data: dict) -> dict:
        return await self._request("POST", "/labels", json=data)

    async def get_statistics(self) -> dict:
        return await self._request("GET", "/statistics/summary")

    async def upload_attachment(self, item_id: str, file_data: bytes,
                                filename: str, attachment_type: str = "photo") -> dict:
        if not self.token:
            await self._authenticate()

        url = f"{self.base_url}/items/{item_id}/attachments"
        headers = {"Authorization": f"Bearer {self.token}"}
        mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        files = {"file": (filename, file_data, mime_type)}
        data = {"type": attachment_type, "name": filename}

        resp = await self.client.post(url, headers=headers, files=files, data=data)

        if resp.status_code == 401 and HOMEBOX_USERNAME:
            logger.info("Token expired, re-authenticating")
            await self._authenticate()
            headers = {"Authorization": f"Bearer {self.token}"}
            resp = await self.client.post(url, headers=headers, files=files, data=data)

        resp.raise_for_status()
        return resp.json() if resp.content else {"success": True}


# Initialize client and MCP server
hb = HomeboxClient()
app = Server("homebox-mcp-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available Homebox MCP tools."""
    return [
        Tool(
            name="search_items",
            description="Search and filter inventory items in Homebox. Supports full-text search, "
                        "filtering by location IDs and label IDs, and pagination.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Full-text search query (searches name, description, serial number, etc.)"
                    },
                    "locations": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by location UUIDs"
                    },
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by label UUIDs"
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number (default: 1)",
                        "default": 1
                    },
                    "page_size": {
                        "type": "integer",
                        "description": "Items per page (default: 50)",
                        "default": 50
                    }
                }
            }
        ),
        Tool(
            name="get_item",
            description="Get full details for a single inventory item by its UUID, including "
                        "purchase info, warranty, serial number, custom fields, and location.",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "string",
                        "description": "UUID of the item"
                    }
                },
                "required": ["item_id"]
            }
        ),
        Tool(
            name="create_item",
            description="Add a new item to the Homebox inventory.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Item name (required)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Item description"
                    },
                    "location_id": {
                        "type": "string",
                        "description": "UUID of the location where the item is stored"
                    },
                    "label_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of label UUIDs to apply"
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Quantity (default: 1)"
                    },
                    "serial_number": {
                        "type": "string",
                        "description": "Serial number"
                    },
                    "model_number": {
                        "type": "string",
                        "description": "Model number"
                    },
                    "manufacturer": {
                        "type": "string",
                        "description": "Manufacturer name"
                    },
                    "purchase_price": {
                        "type": "number",
                        "description": "Purchase price"
                    },
                    "purchase_from": {
                        "type": "string",
                        "description": "Where item was purchased"
                    },
                    "purchase_time": {
                        "type": "string",
                        "description": "Purchase date (ISO 8601 format, e.g. 2024-01-15)"
                    },
                    "warranty_expires": {
                        "type": "string",
                        "description": "Warranty expiration date (ISO 8601 format)"
                    },
                    "warranty_details": {
                        "type": "string",
                        "description": "Warranty details/notes"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Additional notes"
                    }
                },
                "required": ["name"]
            }
        ),
        Tool(
            name="update_item",
            description="Update an existing inventory item. Only provided fields will be changed.",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "string",
                        "description": "UUID of the item to update"
                    },
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "location_id": {"type": "string"},
                    "label_ids": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "quantity": {"type": "integer"},
                    "serial_number": {"type": "string"},
                    "model_number": {"type": "string"},
                    "manufacturer": {"type": "string"},
                    "purchase_price": {"type": "number"},
                    "purchase_from": {"type": "string"},
                    "purchase_time": {"type": "string"},
                    "warranty_expires": {"type": "string"},
                    "warranty_details": {"type": "string"},
                    "notes": {"type": "string"}
                },
                "required": ["item_id"]
            }
        ),
        Tool(
            name="delete_item",
            description="Permanently delete an item from Homebox inventory.",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "string",
                        "description": "UUID of the item to delete"
                    }
                },
                "required": ["item_id"]
            }
        ),
        Tool(
            name="get_item_attachments",
            description="Get all attachments (photos, receipts, manuals) for a specific item.",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "string",
                        "description": "UUID of the item"
                    }
                },
                "required": ["item_id"]
            }
        ),
        Tool(
            name="get_locations",
            description="List all storage locations defined in Homebox (e.g., rooms, shelves, boxes).",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="create_location",
            description="Create a new storage location in Homebox.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Location name (required)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Location description"
                    },
                    "parent_id": {
                        "type": "string",
                        "description": "UUID of parent location (for nested locations)"
                    }
                },
                "required": ["name"]
            }
        ),
        Tool(
            name="get_labels",
            description="List all labels/tags defined in Homebox for categorizing items.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="create_label",
            description="Create a new label/tag in Homebox.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Label name (required)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Label description"
                    },
                    "color": {
                        "type": "string",
                        "description": "Label color as hex code (e.g. #ff0000)"
                    }
                },
                "required": ["name"]
            }
        ),
        Tool(
            name="get_statistics",
            description="Get a summary of inventory statistics: total items, locations, labels, and total value.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="upload_attachment",
            description="Upload an image or file as an attachment to an existing Homebox item. "
                        "Accepts a local file path or a URL. Use this after create_item to attach "
                        "a photo, receipt, manual, or warranty document to the item.",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "string",
                        "description": "UUID of the item to attach the file to"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Absolute local file path to the image or document"
                    },
                    "url": {
                        "type": "string",
                        "description": "URL to fetch the file from (used if file_path is not provided)"
                    },
                    "attachment_type": {
                        "type": "string",
                        "description": "Type of attachment",
                        "enum": ["photo", "manual", "warranty", "receipt", "other"],
                        "default": "photo"
                    },
                    "filename": {
                        "type": "string",
                        "description": "Override filename (optional — inferred from path or URL if omitted)"
                    }
                },
                "required": ["item_id"]
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls for Homebox operations."""
    try:
        if name == "search_items":
            return await handle_search_items(arguments)
        elif name == "get_item":
            return await handle_get_item(arguments)
        elif name == "create_item":
            return await handle_create_item(arguments)
        elif name == "update_item":
            return await handle_update_item(arguments)
        elif name == "delete_item":
            return await handle_delete_item(arguments)
        elif name == "get_item_attachments":
            return await handle_get_item_attachments(arguments)
        elif name == "get_locations":
            return await handle_get_locations(arguments)
        elif name == "create_location":
            return await handle_create_location(arguments)
        elif name == "get_labels":
            return await handle_get_labels(arguments)
        elif name == "create_label":
            return await handle_create_label(arguments)
        elif name == "get_statistics":
            return await handle_get_statistics(arguments)
        elif name == "upload_attachment":
            return await handle_upload_attachment(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")
    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_search_items(arguments: dict) -> list[TextContent]:
    query = arguments.get("query", "")
    locations = arguments.get("locations")
    labels = arguments.get("labels")
    page = arguments.get("page", 1)
    page_size = arguments.get("page_size", 50)

    logger.info(f"Searching items: query='{query}' locations={locations} labels={labels}")
    result = await hb.search_items(query=query, locations=locations, labels=labels,
                                   page=page, page_size=page_size)

    items = result.get("items", []) if isinstance(result, dict) else result
    total = result.get("total", len(items)) if isinstance(result, dict) else len(items)

    text = f"Found {total} items (showing {len(items)}):\n\n"
    text += json.dumps(items, indent=2, default=str)
    return [TextContent(type="text", text=text)]


async def handle_get_item(arguments: dict) -> list[TextContent]:
    item_id = arguments["item_id"]
    logger.info(f"Fetching item: {item_id}")
    result = await hb.get_item(item_id)
    return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]


async def handle_create_item(arguments: dict) -> list[TextContent]:
    data = {
        "name": arguments["name"],
        "description": arguments.get("description", ""),
        "quantity": arguments.get("quantity", 1),
        "notes": arguments.get("notes", ""),
    }

    if "location_id" in arguments:
        data["locationId"] = arguments["location_id"]
    if "label_ids" in arguments:
        data["labelIds"] = arguments["label_ids"]
    if "serial_number" in arguments:
        data["serialNumber"] = arguments["serial_number"]
    if "model_number" in arguments:
        data["modelNumber"] = arguments["model_number"]
    if "manufacturer" in arguments:
        data["manufacturer"] = arguments["manufacturer"]
    if "purchase_price" in arguments:
        data["purchasePrice"] = arguments["purchase_price"]
    if "purchase_from" in arguments:
        data["purchaseFrom"] = arguments["purchase_from"]
    if "purchase_time" in arguments:
        data["purchaseTime"] = arguments["purchase_time"]
    if "warranty_expires" in arguments:
        data["warrantyExpires"] = arguments["warranty_expires"]
    if "warranty_details" in arguments:
        data["warrantyDetails"] = arguments["warranty_details"]

    logger.info(f"Creating item: {data['name']}")
    result = await hb.create_item(data)
    return [TextContent(type="text", text=f"Item created successfully:\n\n{json.dumps(result, indent=2, default=str)}")]


async def handle_update_item(arguments: dict) -> list[TextContent]:
    item_id = arguments["item_id"]

    # Fetch existing item first to merge fields
    existing = await hb.get_item(item_id)

    field_map = {
        "name": "name",
        "description": "description",
        "quantity": "quantity",
        "notes": "notes",
        "location_id": "locationId",
        "label_ids": "labelIds",
        "serial_number": "serialNumber",
        "model_number": "modelNumber",
        "manufacturer": "manufacturer",
        "purchase_price": "purchasePrice",
        "purchase_from": "purchaseFrom",
        "purchase_time": "purchaseTime",
        "warranty_expires": "warrantyExpires",
        "warranty_details": "warrantyDetails",
    }

    data = dict(existing)
    for arg_key, api_key in field_map.items():
        if arg_key in arguments:
            data[api_key] = arguments[arg_key]

    logger.info(f"Updating item: {item_id}")
    result = await hb.update_item(item_id, data)
    return [TextContent(type="text", text=f"Item updated successfully:\n\n{json.dumps(result, indent=2, default=str)}")]


async def handle_delete_item(arguments: dict) -> list[TextContent]:
    item_id = arguments["item_id"]
    logger.info(f"Deleting item: {item_id}")
    await hb.delete_item(item_id)
    return [TextContent(type="text", text=f"Item {item_id} deleted successfully.")]


async def handle_get_item_attachments(arguments: dict) -> list[TextContent]:
    item_id = arguments["item_id"]
    logger.info(f"Fetching attachments for item: {item_id}")
    result = await hb.get_item_attachments(item_id)
    text = f"Attachments for item {item_id}:\n\n{json.dumps(result, indent=2, default=str)}"
    return [TextContent(type="text", text=text)]


async def handle_get_locations(arguments: dict) -> list[TextContent]:
    logger.info("Fetching all locations")
    result = await hb.get_locations()
    text = f"Locations:\n\n{json.dumps(result, indent=2, default=str)}"
    return [TextContent(type="text", text=text)]


async def handle_create_location(arguments: dict) -> list[TextContent]:
    data = {"name": arguments["name"]}
    if "description" in arguments:
        data["description"] = arguments["description"]
    if "parent_id" in arguments:
        data["parentId"] = arguments["parent_id"]

    logger.info(f"Creating location: {data['name']}")
    result = await hb.create_location(data)
    return [TextContent(type="text", text=f"Location created successfully:\n\n{json.dumps(result, indent=2, default=str)}")]


async def handle_get_labels(arguments: dict) -> list[TextContent]:
    logger.info("Fetching all labels")
    result = await hb.get_labels()
    text = f"Labels:\n\n{json.dumps(result, indent=2, default=str)}"
    return [TextContent(type="text", text=text)]


async def handle_create_label(arguments: dict) -> list[TextContent]:
    data = {"name": arguments["name"]}
    if "description" in arguments:
        data["description"] = arguments["description"]
    if "color" in arguments:
        data["color"] = arguments["color"]

    logger.info(f"Creating label: {data['name']}")
    result = await hb.create_label(data)
    return [TextContent(type="text", text=f"Label created successfully:\n\n{json.dumps(result, indent=2, default=str)}")]


async def handle_get_statistics(arguments: dict) -> list[TextContent]:
    logger.info("Fetching inventory statistics")
    result = await hb.get_statistics()
    text = f"Inventory Statistics:\n\n{json.dumps(result, indent=2, default=str)}"
    return [TextContent(type="text", text=text)]


async def handle_upload_attachment(arguments: dict) -> list[TextContent]:
    item_id = arguments["item_id"]
    file_path = arguments.get("file_path")
    url = arguments.get("url")
    attachment_type = arguments.get("attachment_type", "photo")

    if not file_path and not url:
        raise ValueError("Either file_path or url must be provided")

    if file_path:
        path = Path(file_path)
        if not path.exists():
            raise ValueError(f"File not found: {file_path}")
        filename = arguments.get("filename", path.name)
        file_data = path.read_bytes()
        logger.info(f"Uploading attachment from path: {file_path} to item {item_id}")
    else:
        logger.info(f"Fetching attachment from URL: {url}")
        async with httpx.AsyncClient(verify=HOMEBOX_SSL_VERIFY, timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            file_data = resp.content
        filename = arguments.get("filename", url.split("/")[-1].split("?")[0] or "attachment")

    result = await hb.upload_attachment(item_id, file_data, filename, attachment_type)
    return [TextContent(type="text", text=f"Attachment uploaded successfully:\n\n{json.dumps(result, indent=2, default=str)}")]


async def main():
    """Run the MCP server using stdio transport."""
    logger.info(f"Starting Homebox MCP server (connecting to {HOMEBOX_URL})")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
