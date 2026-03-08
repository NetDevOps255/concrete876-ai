# Homebox MCP Server

A Model Context Protocol (MCP) server that gives Claude full read/write access to your self-hosted Homebox home inventory instance. Supports natural language queries, full CRUD on items, and adding items directly from photos or images.

## Features

### Item Management
- **search_items** - Full-text search across inventory with filters for location and label
- **get_item** - Get complete item details by UUID (purchase info, warranty, serial number, custom fields)
- **create_item** - Add new items with full metadata (price, warranty, manufacturer, purchase date, etc.)
- **update_item** - Update any field on an existing item
- **delete_item** - Permanently remove an item from inventory
- **get_item_attachments** - List photos, receipts, and manuals attached to an item

### Organization
- **get_locations** - List all storage locations (rooms, shelves, boxes, etc.)
- **create_location** - Add new locations, supports nested/parent locations
- **get_labels** - List all labels/tags used to categorize items
- **create_label** - Create new labels with optional color coding

### Attachments & Images
- **upload_attachment** - Upload a photo, receipt, manual, or warranty doc to an item — from a local file path or URL

### Reporting
- **get_statistics** - Inventory summary: total items, locations, labels, and total estimated value

**12 tools total** across item management, organization, attachments, and reporting.

---

## Image-to-Inventory Workflow

The most powerful use case — share a photo and Claude handles the rest:

1. Share an image in the Claude conversation (paste, drag-drop, or provide a file path)
2. Claude reads the image using vision and extracts: name, manufacturer, model number, serial number, and other visible details
3. Claude calls `create_item` with the extracted data → Homebox item is created
4. Claude calls `upload_attachment` with the image → photo is stored on the item in Homebox

**Example prompts:**
- "Here's a photo of my new power drill — add it to inventory in the garage" *(attach image)*
- "Scan this receipt and add the item to Homebox"
- "Add everything on this shelf to my inventory" *(attach photo)*

For receipts, Claude will also extract purchase price, date, and retailer automatically.

---

## Setup

### Prerequisites

- Homebox instance running and accessible on your network
- Homebox API token **or** username/password credentials
- Docker Desktop (for containerized deployment) OR Python 3.11+ (for local deployment)

### Generating a Homebox API Token

1. Log into your Homebox instance
2. Go to **Profile > API Tokens**
3. Click **Generate Token**
4. Copy the token — it will only be shown once

### Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your Homebox details:
   ```env
   HOMEBOX_URL=http://192.168.1.100:7745
   HOMEBOX_TOKEN=your-api-token-here
   ```

   If you don't have an API token, use username/password instead:
   ```env
   HOMEBOX_URL=http://192.168.1.100:7745
   HOMEBOX_USERNAME=admin@example.com
   HOMEBOX_PASSWORD=your-password-here
   ```
   The server will authenticate automatically and refresh the session token when it expires.

---

## Deployment

### Option 1: Docker (Recommended)

```bash
cd mcp-servers/homebox
docker compose up -d --build
```

View logs:
```bash
docker compose logs -f
```

Stop:
```bash
docker compose down
```

### Option 2: Local Python

```bash
cd mcp-servers/homebox
pip install -r requirements.txt
python server.py
```

---

## Configure Claude Code

Add the server to your Claude Code MCP configuration (`claude_code_config.json` or via Settings > MCP Servers).

**Docker:**
```json
{
  "mcpServers": {
    "homebox": {
      "command": "docker",
      "args": ["exec", "-i", "homebox-mcp-server", "python", "server.py"]
    }
  }
}
```

**Local Python:**
```json
{
  "mcpServers": {
    "homebox": {
      "command": "python",
      "args": ["C:/Users/tcarr/Documents/Github Repos/local-ai/mcp-servers/homebox/server.py"],
      "env": {
        "HOMEBOX_URL": "http://192.168.1.100:7745",
        "HOMEBOX_TOKEN": "your-api-token-here"
      }
    }
  }
}
```

Restart Claude Code after saving the configuration.

---

## Usage Examples

### Querying Inventory
- "What items do I have in the garage?"
- "Search for all electronics worth over $100"
- "Show me everything with an expiring warranty"
- "Find my Dewalt tools"
- "What's stored in the basement shelving?"

### Adding Items
- "Add a new item: Sony WH-1000XM5 headphones, purchased from Amazon for $280, stored in the office"
- "Create an inventory entry for my Ryobi drill, serial number ABC123, warranty expires 2026-06-01"
- "Add 3x Ethernet cables to the network closet location"

### Updating Items
- "Update the TV to set its purchase price to $899"
- "Move the camping gear to the garage location"
- "Add the 'Electronics' label to item UUID abc-123"
- "Set the warranty expiration on my laptop to 2025-12-31"

### Organization
- "List all my storage locations"
- "Create a new location called 'Attic Storage'"
- "Add a nested location 'Top Shelf' under 'Garage'"
- "Show me all labels I have set up"
- "Create a label called 'Insured' with color #00aa00"

### Adding Items from Images

- "Here's a photo of my new drill — add it to inventory in the garage" *(attach image)*
- "Add this item to Homebox" *(attach image)*
- "Scan this receipt and create the item"

### Uploading Files to Existing Items

- "Attach this receipt to item UUID abc-123"
- "Upload the manual at /home/user/docs/manual.pdf to my washing machine item"
- "Add this warranty document to the TV item"
- "Mark this attachment as type 'warranty'"

### Reporting
- "Give me a summary of my entire inventory"
- "How many items do I have total?"
- "What's the total estimated value of my inventory?"

---

## Tool Reference

### search_items

Search and filter inventory items.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `query` | string | No | Full-text search (name, description, serial number, etc.) |
| `locations` | array | No | Filter by location UUIDs |
| `labels` | array | No | Filter by label UUIDs |
| `page` | integer | No | Page number (default: 1) |
| `page_size` | integer | No | Results per page (default: 50) |

---

### get_item

Get complete details for one item by UUID.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `item_id` | string | Yes | Item UUID |

---

### create_item

Add a new item to inventory.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Item name |
| `description` | string | No | Item description |
| `location_id` | string | No | Storage location UUID |
| `label_ids` | array | No | Label UUIDs to apply |
| `quantity` | integer | No | Quantity (default: 1) |
| `serial_number` | string | No | Serial number |
| `model_number` | string | No | Model number |
| `manufacturer` | string | No | Manufacturer name |
| `purchase_price` | number | No | Purchase price |
| `purchase_from` | string | No | Where purchased |
| `purchase_time` | string | No | Purchase date (ISO 8601, e.g. `2024-01-15`) |
| `warranty_expires` | string | No | Warranty expiration (ISO 8601) |
| `warranty_details` | string | No | Warranty notes |
| `notes` | string | No | Additional notes |

---

### update_item

Update fields on an existing item. Fetches the current item first and merges changes, so only provided fields are overwritten.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `item_id` | string | Yes | Item UUID |
| *(all create_item fields)* | — | No | Any field from create_item |

---

### delete_item

Permanently delete an item.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `item_id` | string | Yes | Item UUID |

---

### get_item_attachments

List all attachments (photos, receipts, manuals) for an item.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `item_id` | string | Yes | Item UUID |

---

### get_locations

Returns all locations. No parameters required.

---

### create_location

Create a new storage location.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Location name |
| `description` | string | No | Location description |
| `parent_id` | string | No | UUID of parent location (for nesting) |

---

### get_labels

Returns all labels. No parameters required.

---

### create_label

Create a new label.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Label name |
| `description` | string | No | Label description |
| `color` | string | No | Hex color code (e.g. `#ff0000`) |

---

### get_statistics

Returns inventory summary stats. No parameters required.

---

### upload_attachment

Upload a file to an existing item as an attachment. Provide either `file_path` or `url`.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `item_id` | string | Yes | Item UUID |
| `file_path` | string | No | Absolute local path to the file |
| `url` | string | No | URL to fetch the file from |
| `attachment_type` | string | No | `photo`, `manual`, `warranty`, `receipt`, or `other` (default: `photo`) |
| `filename` | string | No | Override filename (inferred from path/URL if omitted) |

---

## Security Notes

- Store credentials in `.env` only — never commit it to version control
- API token auth is preferred over username/password for persistent services
- For HTTPS with self-signed certificates, set `HOMEBOX_SSL_VERIFY=false`
- The server runs as a non-root user inside Docker

---

## Troubleshooting

**401 Unauthorized**
- Verify `HOMEBOX_TOKEN` is correct and hasn't expired
- If using username/password, check credentials are correct
- Ensure the Homebox user has API access enabled

**Connection refused / timeout**
- Verify `HOMEBOX_URL` is reachable from where the server is running
- If running in Docker, ensure the container can reach your Homebox host (use host IP, not `localhost`)
- Check Homebox is running: `docker compose ps` or visit the URL in a browser

**SSL errors**
- For self-signed certs set `HOMEBOX_SSL_VERIFY=false` in `.env`

**Tool not appearing in Claude Code**
- Restart Claude Code after adding/changing MCP server config
- Check server logs for startup errors: `docker compose logs homebox-mcp-server`
- Validate JSON syntax in your MCP config file

**Docker container can't reach Homebox**
- Use the host machine's LAN IP instead of `localhost` or `127.0.0.1`
- Example: `HOMEBOX_URL=http://192.168.1.100:7745`

**File not found when uploading attachment**
- Paths must be absolute (e.g. `/home/user/photos/drill.jpg`, not `~/photos/drill.jpg`)
- If running in Docker, the path must exist inside the container — mount a volume or use a URL instead

---

## License

MIT
