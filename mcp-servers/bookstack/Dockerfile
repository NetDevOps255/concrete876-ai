FROM python:3.11-slim

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY src/ src/

# Install dependencies
RUN pip install --no-cache-dir .

# Command to run the MCP server
# We use the fastmcp CLI to run the server
ENTRYPOINT ["fastmcp", "run", "src/bookstack_mcp_server.py:mcp"]
