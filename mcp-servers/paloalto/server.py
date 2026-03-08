#!/usr/bin/env python3
import os
import json
import urllib.parse
from typing import Optional
import httpx
from pydantic import BaseModel, Field, ConfigDict
from fastmcp import FastMCP

PA_HOST = os.getenv("PA_HOST", "")           # e.g. https://192.168.1.1
PA_API_KEY = os.getenv("PA_API_KEY", "")     # PAN-OS API key
PA_VSYS = os.getenv("PA_VSYS", "vsys1")
VERIFY_SSL = os.getenv("PA_VERIFY_SSL", "false").lower() == "true"

BASE_URL = f"{PA_HOST}/api"

mcp = FastMCP("paloalto_mcp")


# ---------------------------------------------------------------------------
# Shared HTTP helpers
# ---------------------------------------------------------------------------

async def pa_op(cmd: str, api_key: str = PA_API_KEY) -> dict:
    """Execute an operational (show) command and return parsed XML as dict."""
    import xml.etree.ElementTree as ET

    params = {
        "type": "op",
        "key": api_key,
        "cmd": cmd,
    }
    async with httpx.AsyncClient(verify=VERIFY_SSL, timeout=30.0) as client:
        r = await client.get(BASE_URL, params=params)
        r.raise_for_status()
        return _xml_to_dict(ET.fromstring(r.text))


async def pa_config_get(xpath: str, api_key: str = PA_API_KEY) -> dict:
    """Read configuration from a given XPath."""
    import xml.etree.ElementTree as ET

    params = {
        "type": "config",
        "action": "get",
        "key": api_key,
        "xpath": xpath,
    }
    async with httpx.AsyncClient(verify=VERIFY_SSL, timeout=30.0) as client:
        r = await client.get(BASE_URL, params=params)
        r.raise_for_status()
        return _xml_to_dict(ET.fromstring(r.text))


async def pa_config_set(xpath: str, element: str, api_key: str = PA_API_KEY) -> dict:
    """Set/create a configuration node."""
    import xml.etree.ElementTree as ET

    params = {
        "type": "config",
        "action": "set",
        "key": api_key,
        "xpath": xpath,
        "element": element,
    }
    async with httpx.AsyncClient(verify=VERIFY_SSL, timeout=30.0) as client:
        r = await client.get(BASE_URL, params=params)
        r.raise_for_status()
        return _xml_to_dict(ET.fromstring(r.text))


async def pa_commit(api_key: str = PA_API_KEY, description: str = "") -> dict:
    """Commit candidate config to running config."""
    import xml.etree.ElementTree as ET

    cmd = "<commit>"
    if description:
        escaped = urllib.parse.quote(description)
        cmd = f"<commit><description>{escaped}</description></commit>"

    params = {
        "type": "commit",
        "key": api_key,
        "cmd": cmd,
    }
    async with httpx.AsyncClient(verify=VERIFY_SSL, timeout=60.0) as client:
        r = await client.get(BASE_URL, params=params)
        r.raise_for_status()
        return _xml_to_dict(ET.fromstring(r.text))


def _xml_to_dict(element) -> dict:
    """Recursively convert an XML Element to a plain Python dict."""
    result: dict = {}
    result["_tag"] = element.tag
    if element.attrib:
        result["_attrib"] = dict(element.attrib)
    children = list(element)
    if children:
        child_dicts = [_xml_to_dict(c) for c in children]
        result["_children"] = child_dicts
    if element.text and element.text.strip():
        result["_text"] = element.text.strip()
    return result


def _handle_api_error(e: Exception) -> str:
    if isinstance(e, httpx.HTTPStatusError):
        if e.response.status_code == 401:
            return "Error: Authentication failed. Check PA_API_KEY env var."
        if e.response.status_code == 403:
            return "Error: Permission denied. Verify the account has API access."
        if e.response.status_code == 404:
            return "Error: Resource not found. Check PA_HOST and device reachability."
        if e.response.status_code == 429:
            return "Error: Rate limit hit. Slow down API calls."
        return f"Error: HTTP {e.response.status_code} — {e.response.text[:200]}"
    if isinstance(e, httpx.TimeoutException):
        return "Error: Request timed out. Check PA_HOST reachability."
    if isinstance(e, httpx.ConnectError):
        return f"Error: Cannot connect to {PA_HOST}. Check PA_HOST env var and network path."
    return f"Error: {type(e).__name__}: {e}"


# ---------------------------------------------------------------------------
# Pydantic input models
# ---------------------------------------------------------------------------

class InterfaceQueryInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    interface: Optional[str] = Field(
        default="",
        description="Filter by interface name (e.g. 'ethernet1/1'). Leave blank for all.",
    )
    vsys: Optional[str] = Field(
        default="",
        description="vsys to query (e.g. 'vsys1'). Defaults to PA_VSYS env var if blank.",
    )


class RouteQueryInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    virtual_router: str = Field(
        default="default",
        description="Virtual router name to query (default: 'default').",
    )
    destination: Optional[str] = Field(
        default="",
        description="Filter routes by destination prefix (e.g. '10.0.0.0/8').",
    )


class SessionQueryInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    source_ip: Optional[str] = Field(default="", description="Filter by source IP.")
    dest_ip: Optional[str] = Field(default="", description="Filter by destination IP.")
    application: Optional[str] = Field(default="", description="Filter by application name (e.g. 'ssl', 'dns').")
    limit: int = Field(default=50, description="Max sessions to return.", ge=1, le=500)


class PolicyQueryInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    vsys: Optional[str] = Field(default="", description="vsys to query (e.g. 'vsys1'). Defaults to PA_VSYS.")
    name_filter: Optional[str] = Field(default="", description="Filter rules containing this string in their name.")
    policy_type: str = Field(
        default="security",
        description="Policy type: 'security', 'nat', or 'pbf'.",
    )


class AddressObjectInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    vsys: Optional[str] = Field(default="", description="vsys (e.g. 'vsys1'). Defaults to PA_VSYS.")
    name_filter: Optional[str] = Field(default="", description="Filter by name substring.")


class BGPPeerInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    virtual_router: str = Field(default="default", description="Virtual router name.")
    peer_filter: Optional[str] = Field(default="", description="Filter by peer name or IP substring.")


class ThreatLogInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    log_type: str = Field(
        default="threat",
        description="Log type: 'threat', 'traffic', 'system', or 'url'.",
    )
    query: Optional[str] = Field(
        default="",
        description="PAN-OS log filter query (e.g. '(addr.src in 10.0.0.0/8)').",
    )
    limit: int = Field(default=50, description="Max log entries to return.", ge=1, le=500)


class CommitInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    description: Optional[str] = Field(
        default="",
        description="Commit description/comment (optional).",
        max_length=255,
    )


class AddressObjectCreateInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    name: str = Field(..., description="Address object name.", min_length=1, max_length=63)
    ip_netmask: str = Field(..., description="IP/mask (e.g. '192.168.1.0/24' or '10.1.1.1/32').")
    description: Optional[str] = Field(default="", description="Object description.", max_length=255)
    vsys: Optional[str] = Field(default="", description="vsys (e.g. 'vsys1'). Defaults to PA_VSYS.")
    tag: Optional[str] = Field(default="", description="Tag name to apply.")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool(
    name="pa_overview",
    annotations={
        "title": "Palo Alto System Overview",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def pa_overview() -> str:
    """Get a high-level overview of the Palo Alto firewall: system info, HA state, active sessions,
    and interface count.

    Returns:
        str: JSON with keys:
            - system_info (dict): hostname, model, sw-version, serial, uptime
            - ha_state (dict): enabled, state, peer info
            - session_summary (dict): active, max, tcp, udp, icmp
            - interface_count (int)
    """
    try:
        sys_info = await pa_op("<show><system><info></info></system></show>")
        ha_info = await pa_op("<show><high-availability><state></state></high-availability></show>")
        session_info = await pa_op("<show><session><info></info></session></show>")
        iface_info = await pa_op("<show><interface>all</interface></show>")

        # Extract useful bits from raw XML dicts
        def _find_text(d: dict, tag: str) -> str:
            if d.get("_tag") == tag:
                return d.get("_text", "")
            for child in d.get("_children", []):
                val = _find_text(child, tag)
                if val:
                    return val
            return ""

        result = {
            "system_info": {
                "hostname": _find_text(sys_info, "hostname"),
                "model": _find_text(sys_info, "model"),
                "sw_version": _find_text(sys_info, "sw-version"),
                "serial": _find_text(sys_info, "serial"),
                "uptime": _find_text(sys_info, "uptime"),
            },
            "ha_state": {
                "raw": ha_info,
            },
            "session_summary": {
                "active": _find_text(session_info, "num-active"),
                "max": _find_text(session_info, "num-max"),
                "tcp": _find_text(session_info, "num-tcp"),
                "udp": _find_text(session_info, "num-udp"),
                "icmp": _find_text(session_info, "num-icmp"),
            },
            "interface_raw": iface_info,
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="pa_check_interfaces",
    annotations={
        "title": "Check Palo Alto Interfaces",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def pa_check_interfaces(params: InterfaceQueryInput) -> str:
    """Check interface status on the Palo Alto firewall.

    Args:
        params (InterfaceQueryInput):
            - interface (str): Optional filter by interface name.
            - vsys (str): vsys to query.

    Returns:
        str: JSON with keys:
            - total (int)
            - interfaces (list[dict]): name, state, ip, speed, duplex
    """
    try:
        data = await pa_op("<show><interface>all</interface></show>")

        def _collect_interfaces(d: dict, results: list):
            if d.get("_tag") == "entry":
                attrib = d.get("_attrib", {})
                name = attrib.get("name", "")
                if not params.interface or params.interface.lower() in name.lower():
                    children = {c["_tag"]: c.get("_text", "") for c in d.get("_children", []) if "_tag" in c}
                    results.append({
                        "name": name,
                        "state": children.get("state", "unknown"),
                        "ip": children.get("ip", ""),
                        "speed": children.get("speed", ""),
                        "duplex": children.get("duplex", ""),
                        "mac": children.get("mac", ""),
                    })
            for child in d.get("_children", []):
                _collect_interfaces(child, results)

        interfaces = []
        _collect_interfaces(data, interfaces)
        return json.dumps({"total": len(interfaces), "interfaces": interfaces}, indent=2)
    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="pa_check_routes",
    annotations={
        "title": "Check Palo Alto Routing Table",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def pa_check_routes(params: RouteQueryInput) -> str:
    """Query the routing table for a given virtual router.

    Args:
        params (RouteQueryInput):
            - virtual_router (str): Virtual router name (default: 'default').
            - destination (str): Optional prefix filter.

    Returns:
        str: JSON with keys:
            - total (int)
            - virtual_router (str)
            - routes (list[dict]): destination, nexthop, metric, flags, interface, age
    """
    try:
        cmd = f"<show><routing><route></route></routing></show>"
        data = await pa_op(cmd)

        def _collect_routes(d: dict, results: list):
            if d.get("_tag") == "entry":
                children = {c["_tag"]: c.get("_text", "") for c in d.get("_children", []) if "_tag" in c}
                dest = children.get("destination", "")
                if not params.destination or params.destination in dest:
                    results.append({
                        "destination": dest,
                        "nexthop": children.get("nexthop", ""),
                        "metric": children.get("metric", ""),
                        "flags": children.get("flags", ""),
                        "interface": children.get("interface", ""),
                        "route_table": children.get("route-table", ""),
                        "age": children.get("age", ""),
                    })
            for child in d.get("_children", []):
                _collect_routes(child, results)

        routes = []
        _collect_routes(data, routes)
        return json.dumps({
            "total": len(routes),
            "virtual_router": params.virtual_router,
            "routes": routes,
        }, indent=2)
    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="pa_check_sessions",
    annotations={
        "title": "Check Active Sessions",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def pa_check_sessions(params: SessionQueryInput) -> str:
    """Query active firewall sessions with optional filtering.

    Args:
        params (SessionQueryInput):
            - source_ip (str): Filter by source IP.
            - dest_ip (str): Filter by destination IP.
            - application (str): Filter by application.
            - limit (int): Max results (default 50).

    Returns:
        str: JSON with keys:
            - total (int)
            - sessions (list[dict]): idx, application, state, src, dst, sport, dport, proto, vsys
    """
    try:

        # Build filter XML for PAN-OS session browser
        filter_parts = []
        if params.source_ip:
            filter_parts.append(f"<source>{params.source_ip}</source>")
        if params.dest_ip:
            filter_parts.append(f"<destination>{params.dest_ip}</destination>")
        if params.application:
            filter_parts.append(f"<application>{params.application}</application>")

        filter_xml = "".join(filter_parts)
        cmd = f"<show><session><all>{filter_xml}</all></session></show>"
        data = await pa_op(cmd)

        def _collect_sessions(d: dict, results: list):
            if len(results) >= params.limit:
                return
            if d.get("_tag") == "entry":
                children = {c["_tag"]: c.get("_text", "") for c in d.get("_children", []) if "_tag" in c}
                results.append({
                    "idx": d.get("_attrib", {}).get("idx", ""),
                    "application": children.get("application", ""),
                    "state": children.get("state", ""),
                    "src": children.get("source", ""),
                    "dst": children.get("dst", ""),
                    "sport": children.get("sport", ""),
                    "dport": children.get("dport", ""),
                    "proto": children.get("proto", ""),
                    "vsys": children.get("vsys", ""),
                    "start_time": children.get("start-time", ""),
                })
            for child in d.get("_children", []):
                if len(results) < params.limit:
                    _collect_sessions(child, results)

        sessions = []
        _collect_sessions(data, sessions)
        return json.dumps({"total": len(sessions), "sessions": sessions}, indent=2)
    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="pa_check_policies",
    annotations={
        "title": "Check Security/NAT/PBF Policies",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def pa_check_policies(params: PolicyQueryInput) -> str:
    """Read security, NAT, or PBF policies from the candidate config.

    Args:
        params (PolicyQueryInput):
            - vsys (str): vsys to query (default: PA_VSYS env var).
            - name_filter (str): Substring to match against rule names.
            - policy_type (str): 'security', 'nat', or 'pbf'.

    Returns:
        str: JSON with keys:
            - total (int)
            - policy_type (str)
            - vsys (str)
            - rules (list[dict]): name, from_zone, to_zone, source, destination, application, action, ...
    """
    try:
        vsys = params.vsys or PA_VSYS

        policy_map = {
            "security": "security",
            "nat": "nat",
            "pbf": "pbf",
        }
        pol = policy_map.get(params.policy_type, "security")
        xpath = f"/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='{vsys}']/rulebase/{pol}/rules"
        data = await pa_config_get(xpath)

        def _child_texts(d: dict, tag: str) -> list:
            """Collect all _text values from child entries matching tag."""
            results = []
            for child in d.get("_children", []):
                if child.get("_tag") == tag:
                    for member in child.get("_children", []):
                        if member.get("_text"):
                            results.append(member.get("_text"))
            return results

        def _collect_rules(d: dict, results: list):
            if d.get("_tag") == "entry":
                name = d.get("_attrib", {}).get("name", "")
                if params.name_filter and params.name_filter.lower() not in name.lower():
                    for child in d.get("_children", []):
                        _collect_rules(child, results)
                    return
                rule = {"name": name}
                for child in d.get("_children", []):
                    tag = child.get("_tag", "")
                    members = [m.get("_text", "") for m in child.get("_children", []) if m.get("_text")]
                    if members:
                        rule[tag] = members if len(members) > 1 else members[0]
                    elif child.get("_text"):
                        rule[tag] = child.get("_text")
                results.append(rule)
            for child in d.get("_children", []):
                _collect_rules(child, results)

        rules = []
        _collect_rules(data, rules)
        return json.dumps({
            "total": len(rules),
            "policy_type": pol,
            "vsys": vsys,
            "rules": rules,
        }, indent=2)
    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="pa_check_address_objects",
    annotations={
        "title": "Check Address Objects",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def pa_check_address_objects(params: AddressObjectInput) -> str:
    """List address objects defined in a vsys.

    Args:
        params (AddressObjectInput):
            - vsys (str): vsys to query (default: PA_VSYS).
            - name_filter (str): Filter by name substring.

    Returns:
        str: JSON with keys:
            - total (int)
            - vsys (str)
            - objects (list[dict]): name, ip_netmask, description, tags
    """
    try:
        vsys = params.vsys or PA_VSYS
        xpath = f"/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='{vsys}']/address"
        data = await pa_config_get(xpath)

        def _collect_objects(d: dict, results: list):
            if d.get("_tag") == "entry":
                name = d.get("_attrib", {}).get("name", "")
                if params.name_filter and params.name_filter.lower() not in name.lower():
                    return
                children = {c["_tag"]: c.get("_text", "") for c in d.get("_children", []) if "_tag" in c}
                tags = [m.get("_text", "") for c in d.get("_children", []) if c.get("_tag") == "tag"
                        for m in c.get("_children", [])]
                results.append({
                    "name": name,
                    "ip_netmask": children.get("ip-netmask", children.get("ip-range", children.get("fqdn", ""))),
                    "description": children.get("description", ""),
                    "tags": tags,
                })
            for child in d.get("_children", []):
                _collect_objects(child, results)

        objects = []
        _collect_objects(data, objects)
        return json.dumps({"total": len(objects), "vsys": vsys, "objects": objects}, indent=2)
    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="pa_check_bgp_peers",
    annotations={
        "title": "Check BGP Peer State",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def pa_check_bgp_peers(params: BGPPeerInput) -> str:
    """Check BGP peer state on the firewall.

    Args:
        params (BGPPeerInput):
            - virtual_router (str): Virtual router name (default: 'default').
            - peer_filter (str): Filter by peer name or IP substring.

    Returns:
        str: JSON with keys:
            - total (int)
            - virtual_router (str)
            - peers (list[dict]): peer_name, peer_address, local_address, state, status_duration, msg_in, msg_out
    """
    try:
        cmd = f"<show><routing><protocol><bgp><peer></peer></bgp></protocol></routing></show>"
        data = await pa_op(cmd)

        def _collect_peers(d: dict, results: list):
            if d.get("_tag") == "entry":
                name = d.get("_attrib", {}).get("name", "")
                children = {c["_tag"]: c.get("_text", "") for c in d.get("_children", []) if "_tag" in c}
                peer_addr = children.get("peer-address", "")
                if params.peer_filter and params.peer_filter.lower() not in name.lower() \
                        and params.peer_filter not in peer_addr:
                    for child in d.get("_children", []):
                        _collect_peers(child, results)
                    return
                results.append({
                    "peer_name": name,
                    "peer_address": peer_addr,
                    "local_address": children.get("local-address", ""),
                    "state": children.get("state", "unknown"),
                    "status_duration": children.get("status-duration", ""),
                    "msg_in": children.get("msg-in", ""),
                    "msg_out": children.get("msg-out", ""),
                    "prefixes_received": children.get("prefixes-received", ""),
                })
            for child in d.get("_children", []):
                _collect_peers(child, results)

        peers = []
        _collect_peers(data, peers)
        return json.dumps({
            "total": len(peers),
            "virtual_router": params.virtual_router,
            "peers": peers,
        }, indent=2)
    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="pa_query_logs",
    annotations={
        "title": "Query PAN-OS Logs",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def pa_query_logs(params: ThreatLogInput) -> str:
    """Query threat, traffic, system, or URL logs from PAN-OS.

    Args:
        params (ThreatLogInput):
            - log_type (str): 'threat', 'traffic', 'system', or 'url'.
            - query (str): PAN-OS log filter (e.g. '(addr.src in 10.0.0.0/8)').
            - limit (int): Max entries to return (default 50).

    Returns:
        str: JSON with keys:
            - total (int)
            - log_type (str)
            - entries (list[dict]): varies by log type; common fields: time, src, dst, app, action, threat_name
    """
    try:

        query_part = f"<query>{params.query}</query>" if params.query else ""
        cmd = (
            f"<show><log><{params.log_type}>"
            f"<match-any>{query_part}"
            f"<direction>backward</direction>"
            f"<max-count>{params.limit}</max-count>"
            f"</match-any></{params.log_type}></log></show>"
        )
        data = await pa_op(cmd)

        def _collect_entries(d: dict, results: list):
            if len(results) >= params.limit:
                return
            if d.get("_tag") == "entry":
                children = {c["_tag"]: c.get("_text", "") for c in d.get("_children", []) if "_tag" in c}
                results.append({
                    "time": children.get("time_generated", ""),
                    "src": children.get("src", ""),
                    "dst": children.get("dst", ""),
                    "app": children.get("app", ""),
                    "action": children.get("action", ""),
                    "rule": children.get("rule", ""),
                    "threat_name": children.get("threatid", children.get("type", "")),
                    "severity": children.get("severity", ""),
                    "category": children.get("category", ""),
                    "srczone": children.get("from", ""),
                    "dstzone": children.get("to", ""),
                })
            for child in d.get("_children", []):
                if len(results) < params.limit:
                    _collect_entries(child, results)

        entries = []
        _collect_entries(data, entries)
        return json.dumps({"total": len(entries), "log_type": params.log_type, "entries": entries}, indent=2)
    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="pa_create_address_object",
    annotations={
        "title": "Create Address Object",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def pa_create_address_object(params: AddressObjectCreateInput) -> str:
    """Create a new address object in the candidate config (does NOT auto-commit).

    Args:
        params (AddressObjectCreateInput):
            - name (str): Address object name.
            - ip_netmask (str): IP/mask (e.g. '10.1.1.0/24').
            - description (str): Optional description.
            - vsys (str): vsys (default: PA_VSYS).
            - tag (str): Optional tag name.

    Returns:
        str: JSON with keys:
            - status (str): 'success' or error message
            - name (str)
            - ip_netmask (str)
            - vsys (str)
            - note (str): reminder to commit
    """
    try:
        vsys = params.vsys or PA_VSYS
        xpath = (
            f"/config/devices/entry[@name='localhost.localdomain']"
            f"/vsys/entry[@name='{vsys}']/address"
        )
        desc_xml = f"<description>{params.description}</description>" if params.description else ""
        tag_xml = f"<tag><member>{params.tag}</member></tag>" if params.tag else ""
        element = (
            f"<entry name='{params.name}'>"
            f"<ip-netmask>{params.ip_netmask}</ip-netmask>"
            f"{desc_xml}{tag_xml}"
            f"</entry>"
        )
        result = await pa_config_set(xpath, element)
        status = result.get("_attrib", {}).get("status", "unknown")
        return json.dumps({
            "status": status,
            "name": params.name,
            "ip_netmask": params.ip_netmask,
            "vsys": vsys,
            "note": "Candidate config updated. Run pa_commit to push changes.",
        }, indent=2)
    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="pa_commit",
    annotations={
        "title": "Commit Candidate Config",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def pa_commit_config(params: CommitInput) -> str:
    """Commit the candidate configuration to the running config on the firewall.

    Args:
        params (CommitInput):
            - description (str): Optional commit description.

    Returns:
        str: JSON with keys:
            - status (str): 'success' or error message
            - job_id (str): commit job ID for tracking
            - description (str)
    """
    try:
        result = await pa_commit(description= params.description)

        def _find_text(d: dict, tag: str) -> str:
            if d.get("_tag") == tag:
                return d.get("_text", "")
            for child in d.get("_children", []):
                val = _find_text(child, tag)
                if val:
                    return val
            return ""

        status = result.get("_attrib", {}).get("status", "unknown")
        job_id = _find_text(result, "job")
        return json.dumps({
            "status": status,
            "job_id": job_id,
            "description": params.description,
        }, indent=2)
    except Exception as e:
        return _handle_api_error(e)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if not PA_HOST or not PA_API_KEY:
        print("Error: Set PA_HOST and PA_API_KEY environment variables.")
        exit(1)
    mcp.run()
