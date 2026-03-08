# BookStack MCP Server

A robust **Model Context Protocol (MCP)** server for [BookStack](https://www.bookstackapp.com/), enabling AI assistants to interact with your documentation. 

This server implements **40+ tools** covering the vast majority of the BookStack API, allowing for comprehensive management of Books, Pages, Chapters, Shelves, Users, and more.

## Features

- **Books**: List, Create, Read, Update, Delete, Export
- **Pages**: List, Create, Read, Update, Delete, Export
- **Chapters**: List, Create, Read, Update, Delete, Export
- **Shelves**: List, Create, Read, Update, Delete
- **Users**: List, Create, Read, Update, Delete
- **Roles**: List, Create, Read, Update, Delete
- **Search**: Advanced content search
- **Attachments**: List, Create, Delete
- **Images**: List, Create (URL), Delete
- **Recycle Bin**: List, Restore
- **Permissions**: Check content permissions
- **System**: View system information

## Installation

### Prerequisites

- Docker and Docker Compose (Recommended)
- OR Python 3.11+
- A running BookStack instance

### Configuration

1. Create a `.env` file from the example:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your credentials:
   ```env
   BOOKSTACK_BASE_URL=http://your-bookstack-url/api
   BOOKSTACK_TOKEN_ID=your_token_id
   BOOKSTACK_TOKEN_SECRET=your_token_secret
   ```

## Usage

### Method 1: Docker (Recommended)

Run the server using Docker Compose. This ensures a consistent environment.

```bash
docker-compose up --build -d
```

To view logs:
```bash
docker-compose logs -f
```

### Method 2: Manual Python

1. Install dependencies:
   ```bash
   pip install fastmcp httpx python-dotenv
   ```

2. Run the server:
   ```bash
   fastmcp run src/bookstack_mcp_server.py:mcp
   ```

### Method 3: Claude Desktop Configuration

Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "bookstack": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e", "BOOKSTACK_BASE_URL=http://host.docker.internal:6875/api",
        "-e", "BOOKSTACK_TOKEN_ID=your_id",
        "-e", "BOOKSTACK_TOKEN_SECRET=your_secret",
        "bookstack-mcp-server"
      ]
    }
  }
}
```

*Note: If running BookStack locally, use `host.docker.internal` to allow the container to reach your host machine.*

## Tool Reference

### Books
- `bookstack_books_list`: List all books
- `bookstack_books_create`: Create a new book
- `bookstack_books_read`: Get book details
- `bookstack_books_update`: Update a book
- `bookstack_books_delete`: Delete a book
- `bookstack_books_export`: Export book (pdf/html/md/txt)

### Pages
- `bookstack_pages_list`: List pages
- `bookstack_pages_create`: Create page
- `bookstack_pages_read`: Read page content
- `bookstack_pages_update`: Update page
- `bookstack_pages_delete`: Delete page
- `bookstack_pages_export`: Export page

### Chapters
- `bookstack_chapters_list`
- `bookstack_chapters_create`
- `bookstack_chapters_read`
- `bookstack_chapters_update`
- `bookstack_chapters_delete`
- `bookstack_chapters_export`

### and many more...
(Shelves, Users, Roles, Search, Attachments, Images, Recycle Bin, Permissions)

## License

MIT
