"""
Uptime Kuma MCP Server
Wraps the uptime-kuma-api Python library (Socket.IO) to expose Uptime Kuma
management capabilities to Claude Code / any MCP client.

Requirements:
    pip install mcp uptime-kuma-api

Configuration (env vars):
    UPTIME_KUMA_URL       - e.g. http://192.168.1.10:3001
    UPTIME_KUMA_USERNAME  - admin username
    UPTIME_KUMA_PASSWORD  - admin password
"""

import json
import os
import logging
from typing import Optional, List, Any, Dict
from enum import Enum

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, ConfigDict

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uptime_kuma_mcp")

KUMA_URL      = os.environ.get("UPTIME_KUMA_URL",      "http://127.0.0.1:3001")
KUMA_USERNAME = os.environ.get("UPTIME_KUMA_USERNAME", "")
KUMA_PASSWORD = os.environ.get("UPTIME_KUMA_PASSWORD", "")

mcp = FastMCP("uptime_kuma_mcp")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_api():
    """Return an authenticated UptimeKumaApi instance (caller must disconnect)."""
    from uptime_kuma_api import UptimeKumaApi
    api = UptimeKumaApi(KUMA_URL)
    api.login(KUMA_USERNAME, KUMA_PASSWORD)
    return api


def _safe_json(obj: Any) -> str:
    """Serialize objects that may contain Enum values."""
    def _default(o):
        if isinstance(o, Enum):
            return o.value
        return str(o)
    return json.dumps(obj, indent=2, default=_default)


def _handle_error(e: Exception) -> str:
    from uptime_kuma_api import UptimeKumaException
    if isinstance(e, UptimeKumaException):
        return f"Uptime Kuma error: {e}"
    return f"Unexpected error ({type(e).__name__}): {e}"


# ---------------------------------------------------------------------------
# Input Models
# ---------------------------------------------------------------------------

class MonitorIdInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    id: int = Field(..., description="Monitor ID", ge=1)


class AddMonitorInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    name: str = Field(..., description="Display name for the monitor", min_length=1, max_length=200)
    url: str = Field(..., description="URL to monitor (for HTTP type)", min_length=1)
    type: str = Field(default="http", description="Monitor type: http, ping, tcp, dns, push, steam, etc.")
    interval: int = Field(default=60, description="Check interval in seconds", ge=20, le=3600)
    retries: int = Field(default=1, description="Retries before marking down", ge=0, le=10)
    upside_down: bool = Field(default=False, description="Upside-down mode (reachable = DOWN)")
    notification_ids: Optional[List[int]] = Field(default=None, description="List of notification channel IDs to attach")


class EditMonitorInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    id: int = Field(..., description="Monitor ID to edit", ge=1)
    name: Optional[str] = Field(default=None, description="New display name")
    url: Optional[str] = Field(default=None, description="New URL")
    interval: Optional[int] = Field(default=None, description="New interval in seconds", ge=20, le=3600)
    retries: Optional[int] = Field(default=None, description="New retry count", ge=0, le=10)


class HeartbeatInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    id: int = Field(..., description="Monitor ID", ge=1)
    offset: int = Field(default=0, description="Pagination offset", ge=0)
    count: int = Field(default=50, description="Number of heartbeats to return", ge=1, le=200)


class AddNotificationInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    name: str = Field(..., description="Notification channel name")
    type: str = Field(..., description="Notification type, e.g. telegram, slack, discord, webhook, email")
    is_default: bool = Field(default=False, description="Apply to all new monitors by default")
    apply_existing: bool = Field(default=False, description="Apply to all existing monitors")
    config: Dict[str, Any] = Field(..., description="Provider-specific config dict (e.g. telegramBotToken, webhookURL)")


class StatusPageInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    slug: str = Field(..., description="Status page slug (URL path)", min_length=1)


class MaintenanceWindowInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    title: str = Field(..., description="Maintenance window title")
    description: Optional[str] = Field(default="", description="Description of the maintenance")
    strategy: str = Field(default="single", description="Strategy: single, recurring-interval, recurring-weekday, recurring-day-of-month")
    start_datetime: str = Field(..., description="Start datetime ISO 8601 e.g. 2024-01-15T02:00:00")
    end_datetime: str = Field(..., description="End datetime ISO 8601 e.g. 2024-01-15T04:00:00")
    monitor_ids: Optional[List[int]] = Field(default=None, description="Monitor IDs to attach to maintenance")


class TagInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    name: str = Field(..., description="Tag name", min_length=1, max_length=50)
    color: str = Field(default="#4B5EFA", description="Tag color hex e.g. #FF0000")


class AddTagToMonitorInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    monitor_id: int = Field(..., description="Monitor ID", ge=1)
    tag_id: int = Field(..., description="Tag ID", ge=1)
    value: Optional[str] = Field(default=None, description="Optional tag value label")


# ---------------------------------------------------------------------------
# Monitor Tools
# ---------------------------------------------------------------------------

@mcp.tool(
    name="kuma_get_monitors",
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}
)
async def kuma_get_monitors() -> str:
    """Get all monitors from Uptime Kuma.

    Returns a JSON array of all configured monitors with their full config
    including id, name, type, url, active status, interval, uptime, etc.
    """
    try:
        api = _get_api()
        monitors = api.get_monitors()
        api.disconnect()
        return _safe_json(monitors)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="kuma_get_monitor",
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}
)
async def kuma_get_monitor(params: MonitorIdInput) -> str:
    """Get a single monitor by ID.

    Returns full monitor details including configuration, current status,
    uptime percentages, and certificate info.

    Args:
        params.id: The monitor ID to retrieve.
    """
    try:
        api = _get_api()
        monitor = api.get_monitor(params.id)
        api.disconnect()
        return _safe_json(monitor)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="kuma_add_monitor",
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False}
)
async def kuma_add_monitor(params: AddMonitorInput) -> str:
    """Add a new monitor to Uptime Kuma.

    Creates a new monitor with the given configuration. Returns the new monitor ID.

    Args:
        params.name: Display name.
        params.url: URL to check (HTTP monitors).
        params.type: Monitor type (http, ping, tcp, dns, push, steam, etc.).
        params.interval: Check interval in seconds (default 60).
        params.retries: Retries before marking down (default 1).
        params.upside_down: Flip status logic.
        params.notification_ids: List of notification channel IDs.

    Returns:
        JSON with msg and monitorId on success.
    """
    try:
        from uptime_kuma_api import MonitorType
        type_map = {t.value: t for t in MonitorType}
        monitor_type = type_map.get(params.type.lower(), MonitorType.HTTP)

        kwargs: Dict[str, Any] = {
            "type": monitor_type,
            "name": params.name,
            "url": params.url,
            "interval": params.interval,
            "maxretries": params.retries,
            "upsideDown": params.upside_down,
        }
        if params.notification_ids is not None:
            kwargs["notificationIDList"] = {str(nid): True for nid in params.notification_ids}

        api = _get_api()
        result = api.add_monitor(**kwargs)
        api.disconnect()
        return _safe_json(result)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="kuma_edit_monitor",
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True}
)
async def kuma_edit_monitor(params: EditMonitorInput) -> str:
    """Edit an existing monitor.

    Only fields provided (non-None) will be updated. Fetches the current
    monitor config first and merges the changes.

    Args:
        params.id: Monitor ID to update.
        params.name: New name (optional).
        params.url: New URL (optional).
        params.interval: New interval (optional).
        params.retries: New retry count (optional).

    Returns:
        JSON with ok and msg fields.
    """
    try:
        api = _get_api()
        current = api.get_monitor(params.id)

        if params.name is not None:
            current["name"] = params.name
        if params.url is not None:
            current["url"] = params.url
        if params.interval is not None:
            current["interval"] = params.interval
        if params.retries is not None:
            current["maxretries"] = params.retries

        # Resolve enum -> value for serialization
        from uptime_kuma_api import MonitorType, AuthMethod
        for key, val in current.items():
            if isinstance(val, Enum):
                current[key] = val.value

        result = api.edit_monitor(params.id, **{k: v for k, v in current.items() if k != "id"})
        api.disconnect()
        return _safe_json(result)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="kuma_delete_monitor",
    annotations={"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False}
)
async def kuma_delete_monitor(params: MonitorIdInput) -> str:
    """Delete a monitor permanently.

    ⚠️  This is destructive and cannot be undone. The monitor and all its
    heartbeat history will be removed.

    Args:
        params.id: Monitor ID to delete.

    Returns:
        JSON with ok and msg fields.
    """
    try:
        api = _get_api()
        result = api.delete_monitor(params.id)
        api.disconnect()
        return _safe_json(result)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="kuma_pause_monitor",
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True}
)
async def kuma_pause_monitor(params: MonitorIdInput) -> str:
    """Pause (disable) a monitor. Monitoring stops but config is retained.

    Args:
        params.id: Monitor ID to pause.
    """
    try:
        api = _get_api()
        result = api.pause_monitor(params.id)
        api.disconnect()
        return _safe_json(result)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="kuma_resume_monitor",
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True}
)
async def kuma_resume_monitor(params: MonitorIdInput) -> str:
    """Resume (re-enable) a paused monitor.

    Args:
        params.id: Monitor ID to resume.
    """
    try:
        api = _get_api()
        result = api.resume_monitor(params.id)
        api.disconnect()
        return _safe_json(result)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="kuma_get_monitor_beats",
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}
)
async def kuma_get_monitor_beats(params: HeartbeatInput) -> str:
    """Get heartbeat history for a monitor (paginated).

    Returns timestamps, status, ping, and message for each recorded check.

    Args:
        params.id: Monitor ID.
        params.offset: Pagination offset (default 0).
        params.count: Number of records (default 50, max 200).

    Returns:
        JSON array of heartbeat objects sorted newest first.
    """
    try:
        api = _get_api()
        beats = api.get_heartbeats()
        api.disconnect()
        monitor_beats = beats.get(str(params.id), beats.get(params.id, []))
        # Paginate
        paginated = monitor_beats[params.offset: params.offset + params.count]
        return _safe_json({
            "monitor_id": params.id,
            "total": len(monitor_beats),
            "offset": params.offset,
            "count": len(paginated),
            "has_more": len(monitor_beats) > params.offset + params.count,
            "beats": paginated,
        })
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="kuma_get_important_heartbeats",
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}
)
async def kuma_get_important_heartbeats(params: MonitorIdInput) -> str:
    """Get only the important (status-change) heartbeats for a monitor.

    Useful for seeing outage history without the noise of every single check.

    Args:
        params.id: Monitor ID.

    Returns:
        JSON array of important heartbeat events (up/down transitions).
    """
    try:
        api = _get_api()
        beats = api.get_important_heartbeats()
        api.disconnect()
        monitor_beats = beats.get(str(params.id), beats.get(params.id, []))
        return _safe_json({"monitor_id": params.id, "beats": monitor_beats})
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="kuma_get_avg_ping",
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}
)
async def kuma_get_avg_ping(params: MonitorIdInput) -> str:
    """Get average ping / response time for a monitor.

    Args:
        params.id: Monitor ID.

    Returns:
        JSON object with average ping in ms.
    """
    try:
        api = _get_api()
        data = api.avg_ping()
        api.disconnect()
        return _safe_json({"monitor_id": params.id, "avg_ping_ms": data.get(params.id)})
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="kuma_get_uptime",
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}
)
async def kuma_get_uptime(params: MonitorIdInput) -> str:
    """Get uptime percentages (24h and 30d) for a monitor.

    Args:
        params.id: Monitor ID.

    Returns:
        JSON with uptime_24h and uptime_30d percentage values.
    """
    try:
        api = _get_api()
        data = api.uptime()
        api.disconnect()
        mid = params.id
        return _safe_json({
            "monitor_id": mid,
            "uptime_24h": data.get(f"{mid}_24"),
            "uptime_30d": data.get(f"{mid}_720"),
        })
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Notification Tools
# ---------------------------------------------------------------------------

@mcp.tool(
    name="kuma_get_notifications",
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}
)
async def kuma_get_notifications() -> str:
    """Get all configured notification channels.

    Returns a JSON array of notification objects with id, name, type, and config.
    """
    try:
        api = _get_api()
        notifications = api.get_notifications()
        api.disconnect()
        return _safe_json(notifications)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="kuma_add_notification",
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False}
)
async def kuma_add_notification(params: AddNotificationInput) -> str:
    """Add a new notification channel.

    The config dict is provider-specific. Common examples:
      - Telegram: {"telegramBotToken": "...", "telegramChatID": "..."}
      - Slack: {"slackwebhookURL": "https://hooks.slack.com/..."}
      - Discord: {"discordWebhookUrl": "https://discord.com/api/webhooks/..."}
      - Email: {"smtpHost": "smtp.gmail.com", "smtpPort": 587, ...}
      - Webhook: {"webhookURL": "https://...", "webhookContentType": "json"}

    Args:
        params.name: Channel name.
        params.type: Provider type string.
        params.is_default: Apply to all new monitors.
        params.apply_existing: Apply to all existing monitors now.
        params.config: Provider-specific configuration dict.

    Returns:
        JSON with ok, msg, and id of the new notification.
    """
    try:
        api = _get_api()
        result = api.add_notification(
            name=params.name,
            type=params.type,
            isDefault=params.is_default,
            applyExisting=params.apply_existing,
            **params.config,
        )
        api.disconnect()
        return _safe_json(result)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="kuma_delete_notification",
    annotations={"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False}
)
async def kuma_delete_notification(params: MonitorIdInput) -> str:
    """Delete a notification channel by ID.

    Args:
        params.id: Notification ID to delete.

    Returns:
        JSON with ok and msg.
    """
    try:
        api = _get_api()
        result = api.delete_notification(params.id)
        api.disconnect()
        return _safe_json(result)
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Status Page Tools
# ---------------------------------------------------------------------------

@mcp.tool(
    name="kuma_get_status_pages",
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}
)
async def kuma_get_status_pages() -> str:
    """Get all public status pages.

    Returns a JSON array of status page objects with slug, title, and config.
    """
    try:
        api = _get_api()
        pages = api.get_status_pages()
        api.disconnect()
        return _safe_json(pages)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="kuma_get_status_page",
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}
)
async def kuma_get_status_page(params: StatusPageInput) -> str:
    """Get full details of a status page by slug.

    Args:
        params.slug: The URL slug for the status page.

    Returns:
        JSON object with all status page config and monitor groups.
    """
    try:
        api = _get_api()
        page = api.get_status_page(params.slug)
        api.disconnect()
        return _safe_json(page)
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Maintenance Tools
# ---------------------------------------------------------------------------

@mcp.tool(
    name="kuma_get_maintenances",
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}
)
async def kuma_get_maintenances() -> str:
    """Get all scheduled maintenance windows.

    Returns JSON array of maintenance objects with title, schedule, and linked monitors.
    """
    try:
        api = _get_api()
        maintenances = api.get_maintenances()
        api.disconnect()
        return _safe_json(maintenances)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="kuma_add_maintenance",
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False}
)
async def kuma_add_maintenance(params: MaintenanceWindowInput) -> str:
    """Schedule a new maintenance window.

    During maintenance, monitors are paused and no alerts are sent.

    Args:
        params.title: Window title.
        params.description: Optional description.
        params.strategy: single | recurring-interval | recurring-weekday | recurring-day-of-month
        params.start_datetime: ISO 8601 start (e.g. 2024-01-15T02:00:00).
        params.end_datetime: ISO 8601 end.
        params.monitor_ids: List of monitor IDs to include.

    Returns:
        JSON with ok, msg, and maintenanceID.
    """
    try:
        from uptime_kuma_api import MaintenanceStrategy
        strategy_map = {s.value: s for s in MaintenanceStrategy}
        strategy = strategy_map.get(params.strategy, MaintenanceStrategy.SINGLE)

        api = _get_api()
        result = api.add_maintenance(
            title=params.title,
            description=params.description or "",
            strategy=strategy,
            active=True,
            intervalDay=1,
            dateRange=[params.start_datetime, params.end_datetime],
            timeRange=[
                {"hours": 0, "minutes": 0},
                {"hours": 23, "minutes": 59},
            ],
            weekdays=[],
            daysOfMonth=[],
        )
        maintenance_id = result.get("maintenanceID")

        if maintenance_id and params.monitor_ids:
            api.add_monitor_maintenance(maintenance_id, params.monitor_ids)

        api.disconnect()
        return _safe_json(result)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="kuma_delete_maintenance",
    annotations={"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False}
)
async def kuma_delete_maintenance(params: MonitorIdInput) -> str:
    """Delete a maintenance window by ID.

    Args:
        params.id: Maintenance window ID to delete.

    Returns:
        JSON with ok and msg.
    """
    try:
        api = _get_api()
        result = api.delete_maintenance(params.id)
        api.disconnect()
        return _safe_json(result)
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Tag Tools
# ---------------------------------------------------------------------------

@mcp.tool(
    name="kuma_get_tags",
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}
)
async def kuma_get_tags() -> str:
    """Get all tags defined in Uptime Kuma.

    Returns JSON array of tag objects with id, name, and color.
    """
    try:
        api = _get_api()
        tags = api.get_tags()
        api.disconnect()
        return _safe_json(tags)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="kuma_add_tag",
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False}
)
async def kuma_add_tag(params: TagInput) -> str:
    """Create a new tag.

    Args:
        params.name: Tag name.
        params.color: Hex color code (e.g. #FF5733).

    Returns:
        JSON with tag id, name, and color.
    """
    try:
        api = _get_api()
        result = api.add_tag(name=params.name, color=params.color)
        api.disconnect()
        return _safe_json(result)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="kuma_add_monitor_tag",
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True}
)
async def kuma_add_monitor_tag(params: AddTagToMonitorInput) -> str:
    """Attach a tag to a monitor.

    Args:
        params.monitor_id: Monitor ID.
        params.tag_id: Tag ID to attach.
        params.value: Optional tag value/label.

    Returns:
        JSON confirmation.
    """
    try:
        api = _get_api()
        result = api.add_monitor_tag(
            tag_id=params.tag_id,
            monitor_id=params.monitor_id,
            value=params.value or "",
        )
        api.disconnect()
        return _safe_json(result)
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# System / Info Tools
# ---------------------------------------------------------------------------

@mcp.tool(
    name="kuma_get_info",
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}
)
async def kuma_get_info() -> str:
    """Get Uptime Kuma server information.

    Returns version, latestVersion, primaryBaseURL, serverTimezone, etc.
    """
    try:
        api = _get_api()
        info = api.info()
        api.disconnect()
        return _safe_json(info)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="kuma_get_settings",
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}
)
async def kuma_get_settings() -> str:
    """Get Uptime Kuma global settings.

    Returns server-wide settings like check frequency, timezone, DNS servers, etc.
    """
    try:
        api = _get_api()
        settings = api.get_settings()
        api.disconnect()
        return _safe_json(settings)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="kuma_get_proxies",
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}
)
async def kuma_get_proxies() -> str:
    """Get all configured proxies.

    Returns JSON array of proxy objects with id, host, port, protocol, etc.
    """
    try:
        api = _get_api()
        proxies = api.get_proxies()
        api.disconnect()
        return _safe_json(proxies)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="kuma_get_docker_hosts",
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}
)
async def kuma_get_docker_hosts() -> str:
    """Get all configured Docker hosts (for container monitors).

    Returns JSON array of Docker host connection configs.
    """
    try:
        api = _get_api()
        hosts = api.get_docker_hosts()
        api.disconnect()
        return _safe_json(hosts)
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    if not KUMA_USERNAME or not KUMA_PASSWORD:
        print(
            "ERROR: Set UPTIME_KUMA_URL, UPTIME_KUMA_USERNAME, UPTIME_KUMA_PASSWORD env vars",
            file=sys.stderr,
        )
        sys.exit(1)
    logger.info(f"Starting Uptime Kuma MCP server → {KUMA_URL}")
    mcp.run()
