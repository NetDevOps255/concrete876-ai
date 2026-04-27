# AWX MCP Server — Environment Setup

## Overview

Python virtual environment for the AWX webhook MCP server.

## Environment Details

| Item | Value |
|---|---|
| Python version | 3.11.1 |
| Python path | `C:\Users\<USER>\AppData\Local\Programs\Python\Python311\python.exe` |
| Venv location | `.venv\` (project root) |
| Created | 2026-04-26 |

## Installed Packages

| Package | Version | Purpose |
|---|---|---|
| fastmcp | 3.2.4 | MCP server framework |
| httpx | 0.28.1 | Async HTTP client (AWX API calls) |
| python-dotenv | 1.2.2 | Load credentials from `.env` file |

## Setup Commands

```powershell
# Create the venv (run from project root)
py -m venv .venv

# Activate (PowerShell)
.\.venv\Scripts\Activate.ps1

# Activate (CMD)
.\.venv\Scripts\activate.bat

# Install dependencies
<PATH-to-Virtual-ENV>/.venv/Scripts/pip.exe" install fastmcp httpx python-dotenv 2>&1
pip install fastmcp httpx python-dotenv

# Freeze dependencies after changes
pip freeze > requirements.txt
```

## Environment Variables

Create a `.env` file in the project root:

```env
AWX_URL=https://awx.test.com
AWX_WEBHOOK_KEY=<your_webhook_key>
```

## Running the Server

```powershell
# With venv activated
python server.py

# Or directly
.\.venv\Scripts\python.exe server.py
```

## Notes

- `python` alias is not available system-wide on this machine — use `py` launcher or the full venv path
- System site-packages are excluded (`include-system-site-packages = false`)
- `.venv\` should be added to `.gitignore`

Get yuh AWX Token
bash# Via AWX CLI or UI:
# Settings → Users → your user → Tokens → Add Token
# Scope: Write

# Or via API:
curl -X POST https://awx.test.com/api/v2/tokens/ \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{"description": "claude-code-mcp", "scope": "write"}'

# Add to .claude.json
"awx-webhook": {
      "command": "PATH-to-Virtual-ENV/.venv/Scripts/python.exe",
      "args": [
        "PATH-to-Python-Script/awx_webhook_agent.py"
      ]
    }