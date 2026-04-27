# awx_webhook_agent.py
import os
import json
import httpx
from fastmcp import FastMCP
from dotenv import load_dotenv

load_dotenv()

AWX_WEBHOOK_URL = os.getenv("AWX_WEBHOOK_URL")
AWX_WEBHOOK_KEY = os.getenv("AWX_WEBHOOK_KEY")

mcp = FastMCP("awx-webhook")

@mcp.tool()
def launch_awx_job(extra_vars: dict) -> str:
    """
    Launch any AWX job template via webhook by passing extra_vars as a dictionary.
    Claude should construct the dict based on what the user describes.

    Args:
        extra_vars: Dictionary of any key/value pairs to pass as extra vars to AWX.
                    e.g. {"network_prefixes": "10.0.0.0/24", "file_path": "/etc/frr/prefixes.txt"}
    """
    resp = httpx.post(
        AWX_WEBHOOK_URL,
        json={"extra_vars": json.dumps(extra_vars)},  # AWX needs a JSON string, not a dict
        headers={
            "Authorization": f"Bearer {AWX_WEBHOOK_KEY}",
            "Content-Type": "application/json",
        },
        verify=False,
        timeout=15,
    )
    resp.raise_for_status()
    job = resp.json()
    return f"Job {job['id']} launched. Status: {job['status']}"

if __name__ == "__main__":
    mcp.run(transport="stdio")