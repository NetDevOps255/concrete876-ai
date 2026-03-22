
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY rapid7_mcp.py .
CMD ["python", "rapid7_mcp.py"]
