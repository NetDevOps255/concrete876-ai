"""
Rapid7 MCP Server
Covers InsightIDR (SIEM) and InsightOps (Log Management) APIs.
Transport: stdio (Docker exec pattern, consistent with your stack)
Auth: X-Api-Key header
Region: configurable via RAPID7_REGION env var (default: us)
"""

import json
import os
import asyncio
from datetime import datetime, timezone
from typing import Optional, List, Any, Dict
from enum import Enum

import httpx
from pydantic import BaseModel, Field, field_validator, ConfigDict
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Config / constants
# ---------------------------------------------------------------------------
API_KEY = os.environ.get("RAPID7_API_KEY", "")
REGION = os.environ.get("RAPID7_REGION", "us")
BASE_URL = f"https://{REGION}.api.insight.rapid7.com"
IDR_BASE = f"{BASE_URL}/idr/v1"
IDR_V2_BASE = f"{BASE_URL}/idr/v2"
LOG_SEARCH_BASE = f"{BASE_URL}/log_search"
TIMEOUT = 30.0

mcp = FastMCP("rapid7_mcp")


# ---------------------------------------------------------------------------
# Shared HTTP client helpers
# ---------------------------------------------------------------------------

def _headers() -> dict:
    return {
        "X-Api-Key": API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


async def _get(path: str, params: Optional[dict] = None) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = client.build_request("GET", path, headers=_headers(), params=params)
        r = await client.send(resp)
        r.raise_for_status()
        return r.json()


async def _post(path: str, body: dict) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = client.build_request("POST", path, headers=_headers(), json=body)
        r = await client.send(resp)
        r.raise_for_status()
        return r.json()


async def _patch(path: str, body: dict) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = client.build_request("PATCH", path, headers=_headers(), json=body)
        r = await client.send(resp)
        r.raise_for_status()
        return r.json()


def _handle_error(e: Exception) -> str:
    if isinstance(e, httpx.HTTPStatusError):
        code = e.response.status_code
        try:
            detail = e.response.json()
        except Exception:
            detail = e.response.text
        msgs = {
            400: "Bad request — check your parameters.",
            401: "Unauthorized — verify RAPID7_API_KEY is set correctly.",
            403: "Forbidden — your API key may lack the required permissions.",
            404: "Not found — the resource ID or RRN may be incorrect.",
            429: "Rate limited — back off and retry.",
        }
        hint = msgs.get(code, "")
        return json.dumps({"error": f"HTTP {code}", "hint": hint, "detail": detail}, indent=2)
    elif isinstance(e, httpx.TimeoutException):
        return json.dumps({"error": "Request timed out. Rapid7 API may be slow; retry."}, indent=2)
    return json.dumps({"error": f"{type(e).__name__}: {str(e)}"}, indent=2)


def _fmt_ts(ts: Optional[str]) -> str:
    """Pass-through; Rapid7 returns ISO strings already."""
    return ts or "N/A"


# ---------------------------------------------------------------------------
# Enums & shared models
# ---------------------------------------------------------------------------

class ResponseFormat(str, Enum):
    MARKDOWN = "markdown"
    JSON = "json"


class InvestigationStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    INVESTIGATING = "INVESTIGATING"


class InvestigationPriority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFORMATIONAL = "INFORMATIONAL"


class SortOrder(str, Enum):
    ASC = "ASC"
    DESC = "DESC"


# ---------------------------------------------------------------------------
# ========================= CONNECTIVITY ==================================
# ---------------------------------------------------------------------------

@mcp.tool(
    name="rapid7_validate_connection",
    annotations={
        "title": "Validate API Connection",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def rapid7_validate_connection() -> str:
    """Validate the Rapid7 API key and connectivity.

    Tests authentication against the Insight Platform validate endpoint.
    Returns region, base URL, and auth status. Run this first to confirm config.

    Returns:
        str: JSON with fields:
            - status (str): "Authorized" or error message
            - region (str): configured region code
            - base_url (str): resolved API base URL
    """
    try:
        r = await _get(f"{BASE_URL}/validate")
        return json.dumps({"status": r.get("message", "OK"), "region": REGION, "base_url": BASE_URL}, indent=2)
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# ========================= INVESTIGATIONS =================================
# ---------------------------------------------------------------------------

class ListInvestigationsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    statuses: Optional[List[InvestigationStatus]] = Field(
        default=None,
        description="Filter by status. Options: OPEN, CLOSED, INVESTIGATING. Leave empty for all."
    )
    priorities: Optional[List[InvestigationPriority]] = Field(
        default=None,
        description="Filter by priority: CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL."
    )
    start_time: Optional[str] = Field(
        default=None,
        description="ISO 8601 start time filter (e.g. '2024-01-01T00:00:00Z')"
    )
    end_time: Optional[str] = Field(
        default=None,
        description="ISO 8601 end time filter (e.g. '2024-12-31T23:59:59Z')"
    )
    index: int = Field(default=0, description="Pagination offset (0-based)", ge=0)
    size: int = Field(default=20, description="Page size, max 100", ge=1, le=100)
    sort: SortOrder = Field(default=SortOrder.DESC, description="Sort order for created_time: ASC or DESC")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


@mcp.tool(
    name="rapid7_list_investigations",
    annotations={
        "title": "List Investigations",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def rapid7_list_investigations(params: ListInvestigationsInput) -> str:
    """List InsightIDR investigations with optional filtering by status, priority, and time range.

    Investigations are the primary incident-response workflow in InsightIDR — aggregated
    alerts tied to a single suspected threat. This tool is your starting point for SOC triage.

    Args:
        params (ListInvestigationsInput): Filter/pagination options.

    Returns:
        str: Markdown summary or JSON with fields:
            - total (int): total matching investigations
            - investigations (list): each has id, title, status, priority, assignee,
              created_time, last_accessed, alert_type, rrn
    """
    try:
        query: dict = {
            "index": params.index,
            "size": params.size,
            "sort": [{"field": "created_time", "order": params.sort.value}],
        }
        if params.statuses:
            query["statuses"] = [s.value for s in params.statuses]
        if params.priorities:
            query["priorities"] = [p.value for p in params.priorities]
        if params.start_time:
            query["start_time"] = params.start_time
        if params.end_time:
            query["end_time"] = params.end_time

        data = await _post(f"{IDR_V2_BASE}/investigations/_search", query)

        if params.response_format == ResponseFormat.JSON:
            return json.dumps(data, indent=2)

        invs = data.get("data", [])
        total = data.get("metadata", {}).get("total_data", len(invs))
        lines = [f"## InsightIDR Investigations ({len(invs)} of {total})\n"]
        for inv in invs:
            pri = inv.get("priority", "N/A")
            status = inv.get("status", "N/A")
            assignee = inv.get("assignee", {})
            assignee_str = assignee.get("email", "Unassigned") if assignee else "Unassigned"
            lines.append(
                f"### [{inv.get('title', 'Untitled')}]"
                f"\n- **ID**: `{inv.get('id', 'N/A')}`"
                f"\n- **RRN**: `{inv.get('rrn', 'N/A')}`"
                f"\n- **Status**: {status} | **Priority**: {pri}"
                f"\n- **Assignee**: {assignee_str}"
                f"\n- **Created**: {_fmt_ts(inv.get('created_time'))}"
                f"\n- **Alerts**: {inv.get('alert_count', 0)}"
                f"\n"
            )
        return "\n".join(lines)
    except Exception as e:
        return _handle_error(e)


class GetInvestigationInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    investigation_id: str = Field(..., description="Investigation ID (UUID) or RRN")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


@mcp.tool(
    name="rapid7_get_investigation",
    annotations={
        "title": "Get Investigation Details",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def rapid7_get_investigation(params: GetInvestigationInput) -> str:
    """Get full details of a specific InsightIDR investigation by ID or RRN.

    Returns deep investigation metadata including all alerts, tags, disposition,
    and timeline info. Use after rapid7_list_investigations to drill in.

    Args:
        params (GetInvestigationInput): investigation_id (UUID or RRN).

    Returns:
        str: Markdown or JSON with full investigation fields.
    """
    try:
        data = await _get(f"{IDR_V2_BASE}/investigations/{params.investigation_id}")
        if params.response_format == ResponseFormat.JSON:
            return json.dumps(data, indent=2)

        inv = data.get("data", data)
        assignee = inv.get("assignee", {})
        assignee_str = assignee.get("email", "Unassigned") if assignee else "Unassigned"
        tags = ", ".join(inv.get("tags", [])) or "None"
        lines = [
            f"## Investigation: {inv.get('title', 'Untitled')}",
            f"- **ID**: `{inv.get('id', 'N/A')}`",
            f"- **RRN**: `{inv.get('rrn', 'N/A')}`",
            f"- **Status**: {inv.get('status', 'N/A')}",
            f"- **Priority**: {inv.get('priority', 'N/A')}",
            f"- **Disposition**: {inv.get('disposition', 'N/A')}",
            f"- **Assignee**: {assignee_str}",
            f"- **Created**: {_fmt_ts(inv.get('created_time'))}",
            f"- **Last Accessed**: {_fmt_ts(inv.get('last_accessed'))}",
            f"- **Alert Count**: {inv.get('alert_count', 0)}",
            f"- **Tags**: {tags}",
            f"- **Source**: {inv.get('source', 'N/A')}",
        ]
        return "\n".join(lines)
    except Exception as e:
        return _handle_error(e)


class UpdateInvestigationInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    investigation_id: str = Field(..., description="Investigation ID (UUID) or RRN")
    status: Optional[InvestigationStatus] = Field(default=None, description="New status: OPEN, CLOSED, INVESTIGATING")
    priority: Optional[InvestigationPriority] = Field(default=None, description="New priority")
    assignee_email: Optional[str] = Field(default=None, description="Email address to assign the investigation to")
    title: Optional[str] = Field(default=None, description="New title for the investigation", max_length=256)


@mcp.tool(
    name="rapid7_update_investigation",
    annotations={
        "title": "Update Investigation",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    }
)
async def rapid7_update_investigation(params: UpdateInvestigationInput) -> str:
    """Update an InsightIDR investigation — change status, priority, assignee, or title.

    Typical SOC workflow: after triage, set status=INVESTIGATING, assign to analyst,
    then CLOSED when resolved.

    Args:
        params (UpdateInvestigationInput): Fields to update (only provided fields are changed).

    Returns:
        str: JSON confirmation of the updated investigation.
    """
    try:
        body: dict = {}
        if params.status:
            body["status"] = params.status.value
        if params.priority:
            body["priority"] = params.priority.value
        if params.assignee_email:
            body["assignee"] = {"email": params.assignee_email}
        if params.title:
            body["title"] = params.title
        if not body:
            return json.dumps({"error": "No fields provided to update."}, indent=2)
        data = await _patch(f"{IDR_V2_BASE}/investigations/{params.investigation_id}", body)
        return json.dumps(data, indent=2)
    except Exception as e:
        return _handle_error(e)


class ListAlertsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    investigation_id: str = Field(..., description="Investigation ID to list alerts for")
    index: int = Field(default=0, ge=0)
    size: int = Field(default=25, ge=1, le=100)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


@mcp.tool(
    name="rapid7_list_investigation_alerts",
    annotations={
        "title": "List Investigation Alerts",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def rapid7_list_investigation_alerts(params: ListAlertsInput) -> str:
    """List all alerts associated with a specific InsightIDR investigation.

    Alerts are the individual detection hits that roll up into an investigation.
    Use this to understand what triggered the investigation.

    Args:
        params (ListAlertsInput): investigation_id, pagination.

    Returns:
        str: Markdown or JSON with alert list including detection rule, type, timestamp.
    """
    try:
        query_params = {"index": params.index, "size": params.size}
        data = await _get(f"{IDR_V2_BASE}/investigations/{params.investigation_id}/alerts", params=query_params)
        if params.response_format == ResponseFormat.JSON:
            return json.dumps(data, indent=2)

        alerts = data.get("data", [])
        total = data.get("metadata", {}).get("total_data", len(alerts))
        lines = [f"## Alerts for Investigation ({len(alerts)} of {total})\n"]
        for a in alerts:
            rule = a.get("detection_rule_rrn", "N/A")
            lines.append(
                f"- **{a.get('type', 'Unknown')}** — `{a.get('rrn', 'N/A')}`"
                f"\n  - Rule: `{rule}`"
                f"\n  - Created: {_fmt_ts(a.get('created_time'))}"
                f"\n  - Actor: {a.get('actor', {}).get('name', 'N/A') if a.get('actor') else 'N/A'}"
            )
        return "\n".join(lines)
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# ========================= ASSETS ========================================
# ---------------------------------------------------------------------------

class SearchAssetsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    hostname: Optional[str] = Field(default=None, description="Filter by hostname (partial match supported)")
    ip: Optional[str] = Field(default=None, description="Filter by IP address")
    index: int = Field(default=0, ge=0)
    size: int = Field(default=20, ge=1, le=100)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


@mcp.tool(
    name="rapid7_search_assets",
    annotations={
        "title": "Search Assets",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def rapid7_search_assets(params: SearchAssetsInput) -> str:
    """Search InsightIDR assets (endpoints) by hostname or IP address.

    Returns asset metadata, agent status, platform, and last seen time.
    Critical for understanding scope of an investigation.

    Args:
        params (SearchAssetsInput): hostname, ip, pagination.

    Returns:
        str: Markdown or JSON with list of matching assets and key fields:
            - hostname, ip_addresses, platform, agent_status, last_seen_time, rrn
    """
    try:
        body: dict = {"index": params.index, "size": params.size}
        if params.hostname:
            body["hostname"] = params.hostname
        if params.ip:
            body["ip"] = params.ip
        data = await _post(f"{IDR_BASE}/assets/_search", body)
        if params.response_format == ResponseFormat.JSON:
            return json.dumps(data, indent=2)

        assets = data.get("data", [])
        total = data.get("metadata", {}).get("total_data", len(assets))
        lines = [f"## Assets ({len(assets)} of {total})\n"]
        for a in assets:
            ips = ", ".join(a.get("ip_addresses", [])) or "N/A"
            lines.append(
                f"### {a.get('hostname', 'Unknown')}"
                f"\n- **RRN**: `{a.get('rrn', 'N/A')}`"
                f"\n- **IPs**: {ips}"
                f"\n- **Platform**: {a.get('platform', {}).get('os', 'N/A') if a.get('platform') else 'N/A'}"
                f"\n- **Agent**: {a.get('agent_status', 'N/A')}"
                f"\n- **Last Seen**: {_fmt_ts(a.get('last_seen_time'))}"
                f"\n"
            )
        return "\n".join(lines)
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# ========================= ACCOUNTS / USERS ==============================
# ---------------------------------------------------------------------------

class SearchAccountsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    username: Optional[str] = Field(default=None, description="Partial username to search")
    domain: Optional[str] = Field(default=None, description="Domain to filter by (e.g. CORP)")
    index: int = Field(default=0, ge=0)
    size: int = Field(default=20, ge=1, le=100)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


@mcp.tool(
    name="rapid7_search_accounts",
    annotations={
        "title": "Search Accounts/Users",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def rapid7_search_accounts(params: SearchAccountsInput) -> str:
    """Search InsightIDR user accounts by username or domain.

    Returns account metadata, lockout status, last authentication time.
    Use to investigate compromised credentials or lateral movement.

    Args:
        params (SearchAccountsInput): username, domain, pagination.

    Returns:
        str: Markdown or JSON with account list:
            - username, domain, name, locked, disabled, last_auth_time, rrn
    """
    try:
        body: dict = {"index": params.index, "size": params.size}
        if params.username:
            body["username"] = params.username
        if params.domain:
            body["domain"] = params.domain
        data = await _post(f"{IDR_BASE}/accounts/_search", body)
        if params.response_format == ResponseFormat.JSON:
            return json.dumps(data, indent=2)

        accounts = data.get("data", [])
        total = data.get("metadata", {}).get("total_data", len(accounts))
        lines = [f"## Accounts ({len(accounts)} of {total})\n"]
        for a in accounts:
            flags = []
            if a.get("locked"):
                flags.append("🔒 LOCKED")
            if a.get("disabled"):
                flags.append("🚫 DISABLED")
            flag_str = " ".join(flags) or "Active"
            lines.append(
                f"- **{a.get('domain', '')}\\{a.get('username', 'N/A')}** ({a.get('name', 'N/A')}) "
                f"— {flag_str}"
                f"\n  RRN: `{a.get('rrn', 'N/A')}` | Last Auth: {_fmt_ts(a.get('last_auth_time'))}"
            )
        return "\n".join(lines)
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# ========================= LOG SEARCH (InsightOps) ========================
# ---------------------------------------------------------------------------

class ListLogsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


@mcp.tool(
    name="rapid7_list_logs",
    annotations={
        "title": "List Log Sources",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def rapid7_list_logs(params: ListLogsInput) -> str:
    """List all available log sources in InsightOps/Log Management.

    Returns log name, ID, and logset membership. You'll need the log ID
    to run rapid7_query_log. Good starting point for any log search workflow.

    Returns:
        str: Markdown or JSON with list of logs:
            - id, name, logsets (list of logset names)
    """
    try:
        data = await _get(f"{LOG_SEARCH_BASE}/management/logs")
        if params.response_format == ResponseFormat.JSON:
            return json.dumps(data, indent=2)

        logs = data.get("logs", [])
        lines = [f"## InsightOps Log Sources ({len(logs)} total)\n"]
        for log in logs:
            logsets = [ls.get("name", "?") for ls in log.get("logsets_info", [])]
            logset_str = ", ".join(logsets) or "No logset"
            lines.append(f"- **{log.get('name', 'Unknown')}** — `{log.get('id', 'N/A')}` [{logset_str}]")
        return "\n".join(lines)
    except Exception as e:
        return _handle_error(e)


class ListLogsetsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


@mcp.tool(
    name="rapid7_list_logsets",
    annotations={
        "title": "List Logsets",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def rapid7_list_logsets(params: ListLogsetsInput) -> str:
    """List all logsets (log groupings) in InsightOps.

    Logsets group related logs together (e.g., 'Firewall Logs', 'Windows Event Logs').
    Use logset IDs to query multiple logs at once.

    Returns:
        str: Markdown or JSON listing logset names and IDs.
    """
    try:
        data = await _get(f"{LOG_SEARCH_BASE}/management/logsets")
        if params.response_format == ResponseFormat.JSON:
            return json.dumps(data, indent=2)

        logsets = data.get("logsets", [])
        lines = [f"## InsightOps Logsets ({len(logsets)} total)\n"]
        for ls in logsets:
            log_count = len(ls.get("logs_info", []))
            lines.append(f"- **{ls.get('name', 'Unknown')}** — `{ls.get('id', 'N/A')}` ({log_count} logs)")
        return "\n".join(lines)
    except Exception as e:
        return _handle_error(e)


class QueryLogInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    log_id: str = Field(..., description="Log ID (UUID) from rapid7_list_logs")
    query: str = Field(
        ...,
        description="LEQL query string (e.g. 'where(ip=10.0.0.1)' or 'calculate(count)' or '' for all events)",
        max_length=4096
    )
    start_time: int = Field(
        ...,
        description="Start of query window as Unix epoch milliseconds (e.g. 1704067200000 = 2024-01-01 UTC)"
    )
    end_time: int = Field(
        ...,
        description="End of query window as Unix epoch milliseconds"
    )
    per_page: int = Field(default=50, description="Events per page, max 500", ge=1, le=500)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


@mcp.tool(
    name="rapid7_query_log",
    annotations={
        "title": "Query Log (LEQL)",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def rapid7_query_log(params: QueryLogInput) -> str:
    """Search a specific InsightOps log using LEQL (Log Entry Query Language).

    Supports filtering (where clauses), statistical aggregations (calculate),
    and full-text search. Returns events or aggregated results.

    LEQL examples:
      - 'where(ip=192.168.1.1)' — filter by IP
      - 'where(severity=HIGH)' — filter by field
      - 'calculate(count) group by(src_ip)' — count by source IP
      - '' — return all events in time range

    Args:
        params (QueryLogInput): log_id, LEQL query, epoch-ms time range.

    Returns:
        str: Markdown or JSON with:
            - events (list of log entries) or statistics
            - links.next for pagination
    """
    try:
        body = {
            "log_keys": [params.log_id],
            "query": params.query,
            "from": params.start_time,
            "to": params.end_time,
            "per_page": params.per_page,
        }
        data = await _post(f"{LOG_SEARCH_BASE}/query/logs", body)
        if params.response_format == ResponseFormat.JSON:
            return json.dumps(data, indent=2)

        events = data.get("events", [])
        stats = data.get("statistics", {})
        lines = [f"## Log Query Results\n**Query**: `{params.query}`\n"]
        if stats:
            lines.append(f"**Statistics**: {json.dumps(stats, indent=2)}\n")
        lines.append(f"**Events returned**: {len(events)}")
        for ev in events[:50]:  # cap display at 50
            msg = ev.get("message", str(ev))
            ts = ev.get("timestamp", "")
            if ts:
                try:
                    ts_str = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                except Exception:
                    ts_str = str(ts)
            else:
                ts_str = "N/A"
            lines.append(f"- `{ts_str}` — {msg[:300]}")
        next_link = data.get("links", [{}])
        if isinstance(next_link, list) and next_link:
            href = next_link[0].get("href", "")
            if href:
                lines.append(f"\n**Next page**: `{href}`")
        return "\n".join(lines)
    except Exception as e:
        return _handle_error(e)


class QueryMultiLogInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    log_ids: List[str] = Field(
        ...,
        description="List of Log IDs (UUIDs) to query simultaneously — max 10",
        min_length=1,
        max_length=10
    )
    query: str = Field(..., description="LEQL query string", max_length=4096)
    start_time: int = Field(..., description="Start time as Unix epoch milliseconds")
    end_time: int = Field(..., description="End time as Unix epoch milliseconds")
    per_page: int = Field(default=50, ge=1, le=500)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


@mcp.tool(
    name="rapid7_query_multi_log",
    annotations={
        "title": "Query Multiple Logs (LEQL)",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def rapid7_query_multi_log(params: QueryMultiLogInput) -> str:
    """Query multiple InsightOps logs simultaneously with a single LEQL query.

    Ideal for cross-source correlation — e.g., search firewall + endpoint logs
    for the same IP in the same time window. Up to 10 log IDs at once.

    Args:
        params (QueryMultiLogInput): list of log_ids, LEQL query, time range.

    Returns:
        str: Combined Markdown or JSON events from all specified logs.
    """
    try:
        body = {
            "log_keys": params.log_ids,
            "query": params.query,
            "from": params.start_time,
            "to": params.end_time,
            "per_page": params.per_page,
        }
        data = await _post(f"{LOG_SEARCH_BASE}/query/logs", body)
        if params.response_format == ResponseFormat.JSON:
            return json.dumps(data, indent=2)

        events = data.get("events", [])
        lines = [
            f"## Multi-Log Query Results",
            f"**Logs queried**: {len(params.log_ids)} | **Query**: `{params.query}` | **Events**: {len(events)}\n"
        ]
        for ev in events[:100]:
            msg = ev.get("message", str(ev))
            ts = ev.get("timestamp", "")
            log_id = ev.get("log_id", "?")
            if ts:
                try:
                    ts_str = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                except Exception:
                    ts_str = str(ts)
            else:
                ts_str = "N/A"
            lines.append(f"- `{ts_str}` [{log_id[:8]}...] — {msg[:300]}")
        return "\n".join(lines)
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# ========================= DETECTION RULES ================================
# ---------------------------------------------------------------------------

class ListDetectionRulesInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    name: Optional[str] = Field(default=None, description="Filter by rule name (partial match)")
    enabled: Optional[bool] = Field(default=None, description="Filter by enabled status: true or false")
    index: int = Field(default=0, ge=0)
    size: int = Field(default=20, ge=1, le=100)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


@mcp.tool(
    name="rapid7_list_detection_rules",
    annotations={
        "title": "List Detection Rules",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def rapid7_list_detection_rules(params: ListDetectionRulesInput) -> str:
    """List InsightIDR detection rules with optional filtering.

    Detection rules define what triggers alerts and investigations. Use this
    to audit coverage, find disabled rules, or get rule RRNs for further ops.

    Args:
        params (ListDetectionRulesInput): name filter, enabled filter, pagination.

    Returns:
        str: Markdown or JSON with rules:
            - rrn, name, description, enabled, type, alert_count, created_time
    """
    try:
        body: dict = {"index": params.index, "size": params.size}
        if params.name:
            body["name"] = params.name
        if params.enabled is not None:
            body["enabled"] = params.enabled
        data = await _post(f"{IDR_V2_BASE}/customdetections/_search", body)
        if params.response_format == ResponseFormat.JSON:
            return json.dumps(data, indent=2)

        rules = data.get("data", [])
        total = data.get("metadata", {}).get("total_data", len(rules))
        lines = [f"## Detection Rules ({len(rules)} of {total})\n"]
        for r in rules:
            status = "✅ Enabled" if r.get("enabled") else "❌ Disabled"
            lines.append(
                f"- **{r.get('name', 'Unknown')}** — {status}"
                f"\n  RRN: `{r.get('rrn', 'N/A')}` | Type: {r.get('type', 'N/A')} | Alerts: {r.get('alert_count', 0)}"
            )
        return "\n".join(lines)
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# ========================= THREAT INDICATORS ==============================
# ---------------------------------------------------------------------------

class AddThreatIndicatorsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    threat_key: str = Field(..., description="Threat key (UUID) to add indicators to")
    ip_addresses: Optional[List[str]] = Field(default=None, description="IP addresses to add as indicators")
    hashes: Optional[List[str]] = Field(default=None, description="File hashes (MD5/SHA1/SHA256) to add")
    domain_names: Optional[List[str]] = Field(default=None, description="Domain names to add")
    urls: Optional[List[str]] = Field(default=None, description="URLs to add as indicators")


@mcp.tool(
    name="rapid7_add_threat_indicators",
    annotations={
        "title": "Add Threat Indicators",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    }
)
async def rapid7_add_threat_indicators(params: AddThreatIndicatorsInput) -> str:
    """Add IP addresses, hashes, domains, or URLs as threat indicators to an InsightIDR threat.

    Threat indicators feed into detection rules and block lists.
    Use during active incident response to block attacker infrastructure.

    Args:
        params (AddThreatIndicatorsInput): threat_key and at least one indicator type.

    Returns:
        str: JSON confirmation with updated threat indicator counts.
    """
    try:
        body: dict = {}
        if params.ip_addresses:
            body["ips"] = params.ip_addresses
        if params.hashes:
            body["hashes"] = params.hashes
        if params.domain_names:
            body["domains"] = params.domain_names
        if params.urls:
            body["urls"] = params.urls
        if not body:
            return json.dumps({"error": "At least one indicator type must be provided."}, indent=2)
        data = await _patch(f"{IDR_BASE}/threats/{params.threat_key}/indicators/add", body)
        return json.dumps(data, indent=2)
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# ========================= COMMENTS =======================================
# ---------------------------------------------------------------------------

class AddCommentInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    investigation_id: str = Field(..., description="Investigation ID or RRN")
    body: str = Field(..., description="Comment text to add", min_length=1, max_length=10000)
    target_type: str = Field(
        default="INVESTIGATION",
        description="Target type for comment. Use 'INVESTIGATION' for investigation-level comments."
    )


@mcp.tool(
    name="rapid7_add_comment",
    annotations={
        "title": "Add Investigation Comment",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    }
)
async def rapid7_add_comment(params: AddCommentInput) -> str:
    """Add a comment to an InsightIDR investigation.

    Comments are the primary collaboration mechanism in InsightIDR investigations.
    Use for documenting analyst findings, escalation notes, or IR timeline entries.

    Args:
        params (AddCommentInput): investigation_id, body text.

    Returns:
        str: JSON with created comment ID and timestamp.
    """
    try:
        body = {
            "body": params.body,
            "target": {
                "id": params.investigation_id,
                "type": params.target_type,
            }
        }
        data = await _post(f"{IDR_V2_BASE}/comments", body)
        return json.dumps(data, indent=2)
    except Exception as e:
        return _handle_error(e)


class ListCommentsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    investigation_id: str = Field(..., description="Investigation ID or RRN")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


@mcp.tool(
    name="rapid7_list_comments",
    annotations={
        "title": "List Investigation Comments",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def rapid7_list_comments(params: ListCommentsInput) -> str:
    """List all comments on a specific InsightIDR investigation.

    Returns analyst notes, timeline entries, and collaboration comments
    in chronological order.

    Args:
        params (ListCommentsInput): investigation_id.

    Returns:
        str: Markdown or JSON with comments: author, body, created_time.
    """
    try:
        data = await _get(
            f"{IDR_V2_BASE}/comments",
            params={"target_id": params.investigation_id, "target_type": "INVESTIGATION"}
        )
        if params.response_format == ResponseFormat.JSON:
            return json.dumps(data, indent=2)

        comments = data.get("data", [])
        lines = [f"## Investigation Comments ({len(comments)})\n"]
        for c in sorted(comments, key=lambda x: x.get("created_time", "")):
            author = c.get("created_by", {})
            author_str = author.get("email", "Unknown") if author else "Unknown"
            lines.append(
                f"**[{_fmt_ts(c.get('created_time'))}] {author_str}**"
                f"\n{c.get('body', '')}\n"
            )
        return "\n".join(lines)
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# ========================= AUDIT LOG ======================================
# ---------------------------------------------------------------------------

class GetAuditLogInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    start_time: Optional[str] = Field(default=None, description="ISO 8601 start time (e.g. '2024-01-01T00:00:00Z')")
    end_time: Optional[str] = Field(default=None, description="ISO 8601 end time")
    index: int = Field(default=0, ge=0)
    size: int = Field(default=25, ge=1, le=100)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


@mcp.tool(
    name="rapid7_get_audit_log",
    annotations={
        "title": "Get Audit Log",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def rapid7_get_audit_log(params: GetAuditLogInput) -> str:
    """Retrieve InsightIDR audit log entries for platform activity tracking.

    Shows user actions, configuration changes, login events, and API activity.
    Useful for compliance reporting and insider threat investigation.

    Args:
        params (GetAuditLogInput): time range and pagination.

    Returns:
        str: Markdown or JSON with audit events:
            - timestamp, actor, action, source_ip, resource
    """
    try:
        body: dict = {"index": params.index, "size": params.size}
        if params.start_time:
            body["start_time"] = params.start_time
        if params.end_time:
            body["end_time"] = params.end_time
        data = await _post(f"{IDR_BASE}/audit_log/_search", body)
        if params.response_format == ResponseFormat.JSON:
            return json.dumps(data, indent=2)

        entries = data.get("data", [])
        total = data.get("metadata", {}).get("total_data", len(entries))
        lines = [f"## Audit Log ({len(entries)} of {total})\n"]
        for entry in entries:
            actor = entry.get("actor", {})
            actor_str = actor.get("email", actor.get("name", "Unknown")) if actor else "Unknown"
            lines.append(
                f"- `{_fmt_ts(entry.get('timestamp'))}` **{actor_str}** — {entry.get('action', 'N/A')}"
                f" (Source IP: {entry.get('source_ip', 'N/A')})"
            )
        return "\n".join(lines)
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if not API_KEY:
        print("WARNING: RAPID7_API_KEY environment variable not set — all API calls will fail with 401.")
    mcp.run()
