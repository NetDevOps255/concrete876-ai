# Rapid7 MCP Server

MCP server covering **InsightIDR** (SIEM) and **InsightOps** (Log Management) APIs.
Follows the Docker stdio exec pattern matching your existing MCP stack.

## Tools (14 total)

### Connectivity
| Tool | Description |
|------|-------------|
| `rapid7_validate_connection` | Test API key and connectivity |

### Investigations (InsightIDR)
| Tool | Description |
|------|-------------|
| `rapid7_list_investigations` | List/search investigations with status, priority, time filters |
| `rapid7_get_investigation` | Deep detail on a single investigation by ID or RRN |
| `rapid7_update_investigation` | Change status, priority, assignee, or title |
| `rapid7_list_investigation_alerts` | Alerts that triggered a given investigation |

### Assets
| Tool | Description |
|------|-------------|
| `rapid7_search_assets` | Search endpoints by hostname or IP |

### Accounts / Users
| Tool | Description |
|------|-------------|
| `rapid7_search_accounts` | Search AD/user accounts by username or domain |

### Log Search / InsightOps (LEQL)
| Tool | Description |
|------|-------------|
| `rapid7_list_logs` | List all log sources and their IDs |
| `rapid7_list_logsets` | List logset groups |
| `rapid7_query_log` | LEQL query against a single log source |
| `rapid7_query_multi_log` | LEQL query across up to 10 logs simultaneously |

### Threat Intelligence
| Tool | Description |
|------|-------------|
| `rapid7_add_threat_indicators` | Add IPs, hashes, domains, URLs to a threat |

### Comments
| Tool | Description |
|------|-------------|
| `rapid7_add_comment` | Add analyst note to an investigation |
| `rapid7_list_comments` | List all comments on an investigation |

### Audit
| Tool | Description |
|------|-------------|
| `rapid7_get_audit_log` | Pull platform audit log entries |

---

## Setup

### 1. Get your API Key
InsightIDR → **Settings → API Keys → Generate New User Key**

### 2. Build the Docker image
```bash
cd rapid7-mcp
docker build -t rapid7-mcp:latest .
```

### 3. Add to Claude Code config (`~/.claude.json`)
```json
{
  "mcpServers": {
    "rapid7": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "rapid7-mcp-server",
        "python",
        "rapid7_mcp.py"
      ]
    }
  }
}
```

> The container must already be running before Claude Code starts. See step 4.

### 4. Start the container
```bash
docker run -d --name rapid7-mcp-server --env-file /path/to/rapid7-mcp/.env rapid7-mcp:latest
```

> Replace `/path/to/rapid7-mcp/.env` with the absolute path to your `.env` file.  
> **Region codes**: `us`, `us2`, `us3`, `eu`, `ca`, `au`, `ap` — check your InsightIDR URL, the subdomain is your region.

---

## LEQL Quick Reference

LEQL (Log Entry Query Language) is InsightOps' query language:

| Pattern | Example |
|---------|---------|
| Filter by field | `where(src_ip=10.0.0.1)` |
| String contains | `where(message contains "failed")` |
| Multiple conditions | `where(severity=HIGH AND src_ip=10.0.0.1)` |
| Count aggregation | `calculate(count) group by(src_ip)` |
| All events | _(empty string)_ |

---

## Example Workflows

### SOC Triage
```
1. rapid7_validate_connection          # confirm auth
2. rapid7_list_investigations          # status=OPEN, priority=CRITICAL
3. rapid7_get_investigation            # drill into top hit
4. rapid7_list_investigation_alerts    # see what fired it
5. rapid7_search_assets                # look up involved host
6. rapid7_add_comment                  # document findings
7. rapid7_update_investigation         # assign + set INVESTIGATING
```

### Log Hunt (lateral movement)
```
1. rapid7_list_logs                    # find Windows auth log ID
2. rapid7_query_log                    # where(event_type=4624) — successful logons
3. rapid7_query_multi_log              # correlate with firewall log
4. rapid7_add_threat_indicators        # block attacker IP
```

---

## Notes
- All tools support `response_format: "json"` for programmatic use
- Pagination via `index` (offset) + `size` across all list tools
- RRNs (Rapid7 Resource Names) are globally unique identifiers — preferred over UUIDs where both accepted