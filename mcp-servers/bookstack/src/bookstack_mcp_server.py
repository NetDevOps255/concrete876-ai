"""BookStack MCP Server - Provides access to BookStack API via MCP tools."""
import json
import os
from typing import Optional, List
from dotenv import load_dotenv
from fastmcp import FastMCP
from bookstack_client import BookStackClient

# Load environment variables
load_dotenv()

# Initialize FastMCP
mcp = FastMCP("BookStack")

# Initialize BookStack client
client = BookStackClient()

def fmt_res(result):
    """Format result to JSON string"""
    if isinstance(result, str):
        return result
    return json.dumps(result, indent=2)

# ==============================================================================
# BOOKS TOOLS (6 tools)
# ==============================================================================

@mcp.tool()
async def bookstack_books_list(
    count: int = 100,
    offset: int = 0,
    sort: str = "+id",
    filter_name: Optional[str] = None,
) -> str:
    """List all books."""
    params = {"count": count, "offset": offset, "sort": sort}
    if filter_name:
        params["filter[name]"] = filter_name
    return fmt_res(await client.get("/books", params=params))

@mcp.tool()
async def bookstack_books_create(
    name: str,
    description_html: Optional[str] = None,
    tags: Optional[str] = None,
) -> str:
    """Create a new book."""
    data = {"name": name}
    if description_html:
        data["description_html"] = description_html
    if tags:
        data["tags"] = json.loads(tags)
    return fmt_res(await client.post("/books", json=data))

@mcp.tool()
async def bookstack_books_read(book_id: int) -> str:
    """Get book details with chapters and pages."""
    return fmt_res(await client.get(f"/books/{book_id}"))

@mcp.tool()
async def bookstack_books_update(
    book_id: int,
    name: Optional[str] = None,
    description_html: Optional[str] = None,
    tags: Optional[str] = None,
) -> str:
    """Update a book."""
    data = {}
    if name: data["name"] = name
    if description_html: data["description_html"] = description_html
    if tags: data["tags"] = json.loads(tags)
    return fmt_res(await client.put(f"/books/{book_id}", json=data))

@mcp.tool()
async def bookstack_books_delete(book_id: int) -> str:
    """Delete a book (moves to recycle bin)."""
    return fmt_res(await client.delete(f"/books/{book_id}"))

@mcp.tool()
async def bookstack_books_export(book_id: int, format: str = "pdf") -> str:
    """Export a book. Formats: html, pdf, markdown, plaintext"""
    return fmt_res(await client.get(f"/books/{book_id}/export/{format}"))

# ==============================================================================
# PAGES TOOLS (6 tools)
# ==============================================================================

@mcp.tool()
async def bookstack_pages_list(
    count: int = 100,
    offset: int = 0,
    sort: str = "+id",
    filter_name: Optional[str] = None,
) -> str:
    """List all pages."""
    params = {"count": count, "offset": offset, "sort": sort}
    if filter_name:
        params["filter[name]"] = filter_name
    return fmt_res(await client.get("/pages", params=params))

@mcp.tool()
async def bookstack_pages_create(
    name: str,
    book_id: Optional[int] = None,
    chapter_id: Optional[int] = None,
    html: Optional[str] = None,
    markdown: Optional[str] = None,
    tags: Optional[str] = None,
) -> str:
    """Create a page."""
    if not book_id and not chapter_id:
        return "Error: Either book_id or chapter_id is required"
    data = {"name": name}
    if book_id: data["book_id"] = book_id
    if chapter_id: data["chapter_id"] = chapter_id
    if html: data["html"] = html
    if markdown: data["markdown"] = markdown
    if tags: data["tags"] = json.loads(tags)
    return fmt_res(await client.post("/pages", json=data))

@mcp.tool()
async def bookstack_pages_read(page_id: int) -> str:
    """Get page content."""
    return fmt_res(await client.get(f"/pages/{page_id}"))

@mcp.tool()
async def bookstack_pages_update(
    page_id: int,
    name: Optional[str] = None,
    html: Optional[str] = None,
    markdown: Optional[str] = None,
    tags: Optional[str] = None,
) -> str:
    """Update a page."""
    data = {}
    if name: data["name"] = name
    if html: data["html"] = html
    if markdown: data["markdown"] = markdown
    if tags: data["tags"] = json.loads(tags)
    return fmt_res(await client.put(f"/pages/{page_id}", json=data))

@mcp.tool()
async def bookstack_pages_delete(page_id: int) -> str:
    """Delete a page."""
    return fmt_res(await client.delete(f"/pages/{page_id}"))

@mcp.tool()
async def bookstack_pages_export(page_id: int, format: str = "pdf") -> str:
    """Export a page."""
    return fmt_res(await client.get(f"/pages/{page_id}/export/{format}"))

# ==============================================================================
# CHAPTERS TOOLS (6 tools)
# ==============================================================================

@mcp.tool()
async def bookstack_chapters_list(
    count: int = 100, offset: int = 0, sort: str = "+id"
) -> str:
    """List chapters."""
    return fmt_res(await client.get("/chapters", params={"count": count, "offset": offset, "sort": sort}))

@mcp.tool()
async def bookstack_chapters_create(
    name: str, book_id: int, description_html: Optional[str] = None, tags: Optional[str] = None
) -> str:
    """Create a chapter."""
    data = {"name": name, "book_id": book_id}
    if description_html: data["description_html"] = description_html
    if tags: data["tags"] = json.loads(tags)
    return fmt_res(await client.post("/chapters", json=data))

@mcp.tool()
async def bookstack_chapters_read(chapter_id: int) -> str:
    """Read chapter."""
    return fmt_res(await client.get(f"/chapters/{chapter_id}"))

@mcp.tool()
async def bookstack_chapters_update(
    chapter_id: int, name: Optional[str] = None, description_html: Optional[str] = None, tags: Optional[str] = None
) -> str:
    """Update chapter."""
    data = {}
    if name: data["name"] = name
    if description_html: data["description_html"] = description_html
    if tags: data["tags"] = json.loads(tags)
    return fmt_res(await client.put(f"/chapters/{chapter_id}", json=data))

@mcp.tool()
async def bookstack_chapters_delete(chapter_id: int) -> str:
    """Delete chapter."""
    return fmt_res(await client.delete(f"/chapters/{chapter_id}"))

@mcp.tool()
async def bookstack_chapters_export(chapter_id: int, format: str = "pdf") -> str:
    """Export chapter."""
    return fmt_res(await client.get(f"/chapters/{chapter_id}/export/{format}"))

# ==============================================================================
# SHELVES TOOLS (5 tools + ? permissions/export?)
# ==============================================================================

@mcp.tool()
async def bookstack_shelves_list(count: int = 100, offset: int = 0, sort: str = "+id") -> str:
    """List shelves."""
    return fmt_res(await client.get("/shelves", params={"count": count, "offset": offset, "sort": sort}))

@mcp.tool()
async def bookstack_shelves_create(
    name: str, description_html: Optional[str] = None, books: Optional[str] = None, tags: Optional[str] = None
) -> str:
    """Create shelf."""
    data = {"name": name}
    if description_html: data["description_html"] = description_html
    if books: data["books"] = json.loads(books)
    if tags: data["tags"] = json.loads(tags)
    return fmt_res(await client.post("/shelves", json=data))

@mcp.tool()
async def bookstack_shelves_read(shelf_id: int) -> str:
    """Read shelf."""
    return fmt_res(await client.get(f"/shelves/{shelf_id}"))

@mcp.tool()
async def bookstack_shelves_update(
    shelf_id: int, name: Optional[str] = None, description_html: Optional[str] = None, books: Optional[str] = None
) -> str:
    """Update shelf."""
    data = {}
    if name: data["name"] = name
    if description_html: data["description_html"] = description_html
    if books: data["books"] = json.loads(books)
    return fmt_res(await client.put(f"/shelves/{shelf_id}", json=data))

@mcp.tool()
async def bookstack_shelves_delete(shelf_id: int) -> str:
    """Delete shelf."""
    return fmt_res(await client.delete(f"/shelves/{shelf_id}"))

# ==============================================================================
# SEARCH (1 tool)
# ==============================================================================

@mcp.tool()
async def bookstack_search(query: str, count: int = 20, page: int = 1, type: Optional[str] = None) -> str:
    """Search content. Type: page, chapter, book, bookshelf"""
    params = {"query": query, "count": count, "page": page}
    if type: params["type"] = type
    return fmt_res(await client.get("/search", params=params))

# ==============================================================================
# USERS (5 tools)
# ==============================================================================

@mcp.tool()
async def bookstack_users_list(count: int = 100, offset: int = 0, sort: str = "+id") -> str:
    """List users."""
    return fmt_res(await client.get("/users", params={"count": count, "offset": offset, "sort": sort}))

@mcp.tool()
async def bookstack_users_create(name: str, email: str, password: Optional[str] = None) -> str:
    """Create user."""
    data = {"name": name, "email": email}
    if password: data["password"] = password
    return fmt_res(await client.post("/users", json=data))

@mcp.tool()
async def bookstack_users_read(user_id: int) -> str:
    """Read user."""
    return fmt_res(await client.get(f"/users/{user_id}"))

@mcp.tool()
async def bookstack_users_update(user_id: int, name: Optional[str] = None, email: Optional[str] = None) -> str:
    """Update user."""
    data = {}
    if name: data["name"] = name
    if email: data["email"] = email
    return fmt_res(await client.put(f"/users/{user_id}", json=data))

@mcp.tool()
async def bookstack_users_delete(user_id: int) -> str:
    """Delete user."""
    return fmt_res(await client.delete(f"/users/{user_id}"))

# ==============================================================================
# ROLES (5 tools)
# ==============================================================================

@mcp.tool()
async def bookstack_roles_list() -> str:
    """List roles."""
    return fmt_res(await client.get("/roles"))

@mcp.tool()
async def bookstack_roles_create(display_name: str, description: Optional[str] = None) -> str:
    """Create role."""
    data = {"display_name": display_name}
    if description: data["description"] = description
    return fmt_res(await client.post("/roles", json=data))

@mcp.tool()
async def bookstack_roles_read(role_id: int) -> str:
    """Read role."""
    return fmt_res(await client.get(f"/roles/{role_id}"))

@mcp.tool()
async def bookstack_roles_update(
    role_id: int, display_name: Optional[str] = None, description: Optional[str] = None
) -> str:
    """Update role."""
    data = {}
    if display_name: data["display_name"] = display_name
    if description: data["description"] = description
    return fmt_res(await client.put(f"/roles/{role_id}", json=data))

@mcp.tool()
async def bookstack_roles_delete(role_id: int) -> str:
    """Delete role."""
    return fmt_res(await client.delete(f"/roles/{role_id}"))

# ==============================================================================
# ATTACHMENTS (3 tools)
# ==============================================================================

@mcp.tool()
async def bookstack_attachments_list(page_id: int) -> str:
    """List attachments."""
    return fmt_res(await client.get("/attachments", params={"filter[page_id]": page_id}))

@mcp.tool()
async def bookstack_attachments_create(page_id: int, name: str, link: str) -> str:
    """Create link attachment."""
    data = {"uploaded_to": page_id, "name": name, "link": link}
    return fmt_res(await client.post("/attachments", json=data))

@mcp.tool()
async def bookstack_attachments_delete(attachment_id: int) -> str:
    """Delete attachment."""
    return fmt_res(await client.delete(f"/attachments/{attachment_id}"))

# ==============================================================================
# IMAGES (3 tools)
# ==============================================================================

@mcp.tool()
async def bookstack_images_list(count: int = 100, offset: int = 0) -> str:
    """List images."""
    return fmt_res(await client.get("/images", params={"count": count, "offset": offset}))

@mcp.tool()
async def bookstack_images_create(page_id: int, name: str, url: str) -> str:
    """Create image (from URL)."""
    # Note: Real file upload is complex via JSON API proxy, this simplifies to URL upload if supported or just placeholder
    return "Image upload from URL not fully standard in simple client, requires multipart. Use UI."

@mcp.tool()
async def bookstack_images_delete(image_id: int) -> str:
    """Delete image."""
    return fmt_res(await client.delete(f"/images/{image_id}"))

# ==============================================================================
# RECYCLE BIN (2 tools)
# ==============================================================================

@mcp.tool()
async def bookstack_recycle_bin_list(count: int = 100, offset: int = 0) -> str:
    """List recycle bin."""
    return fmt_res(await client.get("/recycle-bin", params={"count": count, "offset": offset}))

@mcp.tool()
async def bookstack_recycle_bin_restore(id: int) -> str:
    """Restore item."""
    return fmt_res(await client.put(f"/recycle-bin/{id}"))

# ==============================================================================
# MISC (2 tools)
# ==============================================================================

@mcp.tool()
async def bookstack_permissions_read(content_type: str, content_id: int) -> str:
    """Read permissions for book/chapter/page/shelf."""
    endpoint_map = {"book": "books", "chapter": "chapters", "page": "pages", "shelf": "shelves"}
    if content_type not in endpoint_map: return "Invalid type"
    return fmt_res(await client.get(f"/{endpoint_map[content_type]}/{content_id}"))

@mcp.tool()
async def bookstack_system_info() -> str:
    """Get system info."""
    return fmt_res(await client.get("/docs"))

if __name__ == "__main__":
    mcp.run()
