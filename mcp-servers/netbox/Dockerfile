# Use Python slim image for smaller footprint
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY server.py .

# Create non-root user for security
RUN useradd -m -u 1000 mcp && chown -R mcp:mcp /app
USER mcp

# Set environment variables (can be overridden)
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

# Run the server
CMD ["python", "server.py"]
