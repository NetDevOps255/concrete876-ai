#!/usr/bin/env python3
import os
import json
import httpx
from fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# OBSERVIUM_URL = os.getenv("OBSERVIUM_URL", "")
# OBSERVIUM_USER = os.getenv("OBSERVIUM_USER", "")
# OBSERVIUM_PASS = os.getenv("OBSERVIUM_PASS", "")

OBSERVIUM_URL="http://10.17.1.32"
OBSERVIUM_USER="concrete-ai"
OBSERVIUM_PASS="mX$fyJz9w5ts9b*!!w*T"

if not OBSERVIUM_URL.endswith('/'):
    OBSERVIUM_URL += '/'

BASE_URL = f"{OBSERVIUM_URL}api/v0"

mcp = FastMCP("observium-mcp")

async def obs_request(endpoint, method="GET", data=None, params=None):
    url = f"{BASE_URL}{endpoint}"
    auth = httpx.BasicAuth(OBSERVIUM_USER, OBSERVIUM_PASS)
    
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        if method == "GET":
            r = await client.get(url, auth=auth, params=params)
        elif method == "POST":
            r = await client.post(url, auth=auth, json=data)
        elif method == "PUT":
            r = await client.put(url, auth=auth, json=data)
        elif method == "DELETE":
            r = await client.delete(url, auth=auth)
        
        r.raise_for_status()
        if not r.content:
            return {"status": "success", "http_status": r.status_code}
        return r.json()

@mcp.tool()
async def get_devices(hostname: str = "", os: str = "", location: str = "", status: str = "") -> str:
    """Get network devices from Observium"""
    params = {}
    if hostname:
        params["hostname"] = hostname
    if os:
        params["os"] = os
    if location:
        params["location"] = location
    if status:
        params["status"] = status
    
    result = await obs_request("/devices/", params=params)
    
    devices = []
    for dev_id, dev in result.get("devices", {}).items():
        devices.append({
            "id": dev.get("device_id"),
            "hostname": dev.get("hostname"),
            "os": dev.get("os"),
            "version": dev.get("version"),
            "hardware": dev.get("hardware"),
            "location": dev.get("location"),
            "status": dev.get("status"),
            "uptime": dev.get("uptime")
        })
    
    return json.dumps({"count": result.get("count", 0), "devices": devices}, indent=2)

@mcp.tool()
async def get_device(device_id: str) -> str:
    """Get details for a specific device by ID or hostname"""
    result = await obs_request(f"/devices/{device_id}/")
    return json.dumps(result, indent=2)

@mcp.tool()
async def get_ports(device_id: str = "", ifAlias: str = "", state: str = "", errors: str = "") -> str:
    """Get network ports/interfaces"""
    params = {}
    if device_id:
        params["device_id"] = device_id
    if ifAlias:
        params["ifAlias"] = ifAlias
    if state:
        params["state"] = state
    if errors:
        params["errors"] = errors
    
    result = await obs_request("/ports/", params=params)
    
    ports = []
    for port_id, port in result.get("ports", {}).items():
        ports.append({
            "id": port.get("port_id"),
            "device_id": port.get("device_id"),
            "ifName": port.get("ifName"),
            "ifAlias": port.get("ifAlias"),
            "ifDescr": port.get("ifDescr"),
            "ifSpeed": port.get("ifSpeed"),
            "ifOperStatus": port.get("ifOperStatus"),
            "ifAdminStatus": port.get("ifAdminStatus")
        })
    
    return json.dumps({"count": result.get("count", 0), "ports": ports}, indent=2)

@mcp.tool()
async def get_alerts(device_id: str = "", status: str = "", entity_type: str = "") -> str:
    """Get alerts from Observium"""
    params = {}
    if device_id:
        params["device_id"] = device_id
    if status:
        params["status"] = status
    if entity_type:
        params["entity_type"] = entity_type
    
    result = await obs_request("/alerts/", params=params)
    
    alerts = []
    for alert_id, alert in result.get("alerts", {}).items():
        alerts.append({
            "id": alert.get("alert_table_id"),
            "device_id": alert.get("device_id"),
            "entity_type": alert.get("entity_type"),
            "alert_status": alert.get("alert_status"),
            "alert_message": alert.get("alert_message"),
            "last_changed": alert.get("last_changed"),
            "last_checked": alert.get("last_checked")
        })
    
    return json.dumps({"count": result.get("count", 0), "alerts": alerts}, indent=2)

@mcp.tool()
async def get_sensors(device_id: str = "", sensor_class: str = "", event: str = "") -> str:
    """Get sensors (temperature, voltage, etc)"""
    params = {}
    if device_id:
        params["device_id"] = device_id
    if sensor_class:
        params["sensor_class"] = sensor_class
    if event:
        params["event"] = event
    
    result = await obs_request("/sensors/", params=params)
    
    sensors = []
    for sensor_id, sensor in result.get("sensors", {}).items():
        sensors.append({
            "id": sensor.get("sensor_id"),
            "device_id": sensor.get("device_id"),
            "sensor_descr": sensor.get("sensor_descr"),
            "sensor_class": sensor.get("sensor_class"),
            "sensor_value": sensor.get("sensor_value"),
            "sensor_event": sensor.get("sensor_event")
        })
    
    return json.dumps({"count": result.get("count", 0), "sensors": sensors}, indent=2)

@mcp.tool()
async def get_inventory(device_id: str = "", model: str = "", serial: str = "") -> str:
    """Get hardware inventory (entPhysical)"""
    params = {}
    if device_id:
        params["device_id"] = device_id
    if model:
        params["entPhysicalModelName"] = model
    if serial:
        params["entPhysicalSerialNum"] = serial
    
    result = await obs_request("/inventory/", params=params)
    
    inventory = []
    for item_id, item in result.get("inventory", {}).items():
        inventory.append({
            "id": item.get("entPhysical_id"),
            "device_id": item.get("device_id"),
            "descr": item.get("entPhysicalDescr"),
            "class": item.get("entPhysicalClass"),
            "name": item.get("entPhysicalName"),
            "model": item.get("entPhysicalModelName"),
            "serial": item.get("entPhysicalSerialNum")
        })
    
    return json.dumps({"count": result.get("count", 0), "inventory": inventory}, indent=2)

@mcp.tool()
async def add_device(hostname: str, snmp_version: str = "v2c", snmp_community: str = "", 
                     snmp_port: int = 161, ping_skip: str = "off") -> str:
    """Add a new device to Observium"""
    data = {
        "hostname": hostname,
        "snmp_version": snmp_version,
        "snmp_port": snmp_port,
        "ping_skip": ping_skip
    }
    
    if snmp_community:
        data["snmp_community"] = snmp_community
    
    result = await obs_request("/devices/", method="POST", data=data)
    return json.dumps(result, indent=2)

@mcp.tool()
async def delete_device(device_id: str) -> str:
    """Delete a device from Observium"""
    result = await obs_request(f"/devices/{device_id}/", method="DELETE")
    return json.dumps(result, indent=2)

@mcp.tool()
async def update_device(device_id: str, ignore: int = None, disabled: int = None, 
                       purpose: str = None, ignore_until: str = None) -> str:
    """Update device settings"""
    data = {}
    if ignore is not None:
        data["ignore"] = ignore
    if disabled is not None:
        data["disabled"] = disabled
    if purpose is not None:
        data["purpose"] = purpose
    if ignore_until is not None:
        data["ignore_until"] = ignore_until
    
    result = await obs_request(f"/devices/{device_id}/", method="PUT", data=data)
    return json.dumps(result, indent=2)

@mcp.tool()
async def ignore_alert(alert_id: str, ignore_until_ok: int = None, ignore_until: str = None) -> str:
    """Ignore/acknowledge an alert"""
    data = {}
    if ignore_until_ok is not None:
        data["ignore_until_ok"] = ignore_until_ok
    if ignore_until is not None:
        data["ignore_until"] = ignore_until
    
    result = await obs_request(f"/alerts/{alert_id}/", method="PUT", data=data)
    return json.dumps(result, indent=2)

if __name__ == "__main__":
    if not OBSERVIUM_URL or not OBSERVIUM_USER or not OBSERVIUM_PASS:
        print("Error: Set OBSERVIUM_URL, OBSERVIUM_USER, and OBSERVIUM_PASS")
        exit(1)
    mcp.run()



# #!/usr/bin/env python3
# import os
# import json
# import httpx
# from fastmcp import FastMCP

# OBSERVIUM_URL = os.getenv("OBSERVIUM_URL", "")
# OBSERVIUM_USER = os.getenv("OBSERVIUM_USER", "")
# OBSERVIUM_PASS = os.getenv("OBSERVIUM_PASS", "")

# if not OBSERVIUM_URL.endswith('/'):
#     OBSERVIUM_URL += '/'

# BASE_URL = f"{OBSERVIUM_URL}api/v0"

# # Create persistent client with cookie jar
# _client = None
# _authenticated = False

# async def get_client():
#     global _client, _authenticated
#     if _client is None:
#         _client = httpx.AsyncClient(
#             timeout=30.0, 
#             verify=False,
#             follow_redirects=True
#         )
    
#     # Authenticate if not already done
#     if not _authenticated:
#         auth = httpx.BasicAuth(OBSERVIUM_USER, OBSERVIUM_PASS)
#         # Make an initial auth request to establish session
#         try:
#             r = await _client.get(f"{BASE_URL}/devices/", auth=auth, params={"limit": 1})
#             if r.status_code == 200:
#                 _authenticated = True
#         except:
#             pass
    
#     return _client

# mcp = FastMCP("observium-mcp")

# @mcp.tool()
# async def debug_config() -> str:
#     """Debug configuration - check if credentials are loaded"""
#     return json.dumps({
#         "url": OBSERVIUM_URL,
#         "base_url": BASE_URL,
#         "user": OBSERVIUM_USER,
#         "pass_set": "yes" if OBSERVIUM_PASS else "no",
#         "pass_length": len(OBSERVIUM_PASS) if OBSERVIUM_PASS else 0
#     }, indent=2)

# @mcp.tool()
# async def test_connection() -> str:
#     """Test API connection and authentication"""
#     import base64
    
#     url = f"{BASE_URL}/devices/"
#     auth = httpx.BasicAuth(OBSERVIUM_USER, OBSERVIUM_PASS)
    
#     # Manual auth header
#     auth_string = f"{OBSERVIUM_USER}:{OBSERVIUM_PASS}"
#     auth_bytes = auth_string.encode('utf-8')
#     auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
    
#     client = await get_client()
    
#     try:
#         # Test with httpx auth
#         r = await client.get(url, auth=auth)
        
#         # Test with manual header
#         test_client = httpx.AsyncClient(timeout=30.0, verify=False)
#         r2 = await test_client.get(url, headers={"Authorization": f"Basic {auth_b64}"})
#         await test_client.aclose()
        
#         return json.dumps({
#             "httpx_auth": {
#                 "status_code": r.status_code,
#                 "response": r.text[:200]
#             },
#             "manual_auth": {
#                 "status_code": r2.status_code,
#                 "response": r2.text[:200]
#             },
#             "config": {
#                 "base_url": BASE_URL,
#                 "user": OBSERVIUM_USER,
#                 "user_length": len(OBSERVIUM_USER),
#                 "pass_length": len(OBSERVIUM_PASS)
#             }
#         }, indent=2)
#     except Exception as e:
#         return json.dumps({"error": str(e)}, indent=2)

# async def obs_request(endpoint, method="GET", data=None, params=None):
#     url = f"{BASE_URL}{endpoint}"
#     auth = httpx.BasicAuth(OBSERVIUM_USER, OBSERVIUM_PASS)
#     client = await get_client()
    
#     # Always send auth credentials with every request
#     if method == "GET":
#         r = await client.get(url, auth=auth, params=params)
#     elif method == "POST":
#         r = await client.post(url, auth=auth, json=data)
#     elif method == "PUT":
#         r = await client.put(url, auth=auth, json=data)
#     elif method == "DELETE":
#         r = await client.delete(url, auth=auth)
    
#     if r.status_code == 401:
#         return {
#             "error": "Authentication failed",
#             "message": "Check: 1) API is enabled in config.php ($config['api']['enable'] = TRUE;), 2) Username/password are correct, 3) User has API access permissions",
#             "url": url,
#             "status_code": 401,
#             "response": r.text
#         }
    
#     r.raise_for_status()
#     return r.json()

# @mcp.tool()
# async def get_devices(hostname: str = "", os: str = "", location: str = "", status: str = "") -> str:
#     """Get network devices from Observium"""
#     params = {}
#     if hostname:
#         params["hostname"] = hostname
#     if os:
#         params["os"] = os
#     if location:
#         params["location"] = location
#     if status:
#         params["status"] = status
    
#     result = await obs_request("/devices/", params=params)
    
#     devices = []
#     for dev_id, dev in result.get("devices", {}).items():
#         devices.append({
#             "id": dev.get("device_id"),
#             "hostname": dev.get("hostname"),
#             "os": dev.get("os"),
#             "version": dev.get("version"),
#             "hardware": dev.get("hardware"),
#             "location": dev.get("location"),
#             "status": dev.get("status"),
#             "uptime": dev.get("uptime")
#         })
    
#     return json.dumps({"count": result.get("count", 0), "devices": devices}, indent=2)

# @mcp.tool()
# async def get_device(device_id: str) -> str:
#     """Get details for a specific device by ID or hostname"""
#     result = await obs_request(f"/devices/{device_id}/")
#     return json.dumps(result, indent=2)

# @mcp.tool()
# async def get_ports(device_id: str = "", ifAlias: str = "", state: str = "", errors: str = "") -> str:
#     """Get network ports/interfaces"""
#     params = {}
#     if device_id:
#         params["device_id"] = device_id
#     if ifAlias:
#         params["ifAlias"] = ifAlias
#     if state:
#         params["state"] = state
#     if errors:
#         params["errors"] = errors
    
#     result = await obs_request("/ports/", params=params)
    
#     ports = []
#     for port_id, port in result.get("ports", {}).items():
#         ports.append({
#             "id": port.get("port_id"),
#             "device_id": port.get("device_id"),
#             "ifName": port.get("ifName"),
#             "ifAlias": port.get("ifAlias"),
#             "ifDescr": port.get("ifDescr"),
#             "ifSpeed": port.get("ifSpeed"),
#             "ifOperStatus": port.get("ifOperStatus"),
#             "ifAdminStatus": port.get("ifAdminStatus")
#         })
    
#     return json.dumps({"count": result.get("count", 0), "ports": ports}, indent=2)

# @mcp.tool()
# async def get_alerts(device_id: str = "", status: str = "", entity_type: str = "") -> str:
#     """Get alerts from Observium"""
#     params = {}
#     if device_id:
#         params["device_id"] = device_id
#     if status:
#         params["status"] = status
#     if entity_type:
#         params["entity_type"] = entity_type
    
#     result = await obs_request("/alerts/", params=params)
    
#     alerts = []
#     for alert_id, alert in result.get("alerts", {}).items():
#         alerts.append({
#             "id": alert.get("alert_table_id"),
#             "device_id": alert.get("device_id"),
#             "entity_type": alert.get("entity_type"),
#             "alert_status": alert.get("alert_status"),
#             "alert_message": alert.get("alert_message"),
#             "last_changed": alert.get("last_changed"),
#             "last_checked": alert.get("last_checked")
#         })
    
#     return json.dumps({"count": result.get("count", 0), "alerts": alerts}, indent=2)

# @mcp.tool()
# async def get_sensors(device_id: str = "", sensor_class: str = "", event: str = "") -> str:
#     """Get sensors (temperature, voltage, etc)"""
#     params = {}
#     if device_id:
#         params["device_id"] = device_id
#     if sensor_class:
#         params["sensor_class"] = sensor_class
#     if event:
#         params["event"] = event
    
#     result = await obs_request("/sensors/", params=params)
    
#     sensors = []
#     for sensor_id, sensor in result.get("sensors", {}).items():
#         sensors.append({
#             "id": sensor.get("sensor_id"),
#             "device_id": sensor.get("device_id"),
#             "sensor_descr": sensor.get("sensor_descr"),
#             "sensor_class": sensor.get("sensor_class"),
#             "sensor_value": sensor.get("sensor_value"),
#             "sensor_event": sensor.get("sensor_event")
#         })
    
#     return json.dumps({"count": result.get("count", 0), "sensors": sensors}, indent=2)

# @mcp.tool()
# async def get_inventory(device_id: str = "", model: str = "", serial: str = "") -> str:
#     """Get hardware inventory (entPhysical)"""
#     params = {}
#     if device_id:
#         params["device_id"] = device_id
#     if model:
#         params["entPhysicalModelName"] = model
#     if serial:
#         params["entPhysicalSerialNum"] = serial
    
#     result = await obs_request("/inventory/", params=params)
    
#     inventory = []
#     for item_id, item in result.get("inventory", {}).items():
#         inventory.append({
#             "id": item.get("entPhysical_id"),
#             "device_id": item.get("device_id"),
#             "descr": item.get("entPhysicalDescr"),
#             "class": item.get("entPhysicalClass"),
#             "name": item.get("entPhysicalName"),
#             "model": item.get("entPhysicalModelName"),
#             "serial": item.get("entPhysicalSerialNum")
#         })
    
#     return json.dumps({"count": result.get("count", 0), "inventory": inventory}, indent=2)

# @mcp.tool()
# async def add_device(hostname: str, snmp_version: str = "v2c", snmp_community: str = "", 
#                      snmp_port: int = 161, ping_skip: str = "off") -> str:
#     """Add a new device to Observium"""
#     data = {
#         "hostname": hostname,
#         "snmp_version": snmp_version,
#         "snmp_port": snmp_port,
#         "ping_skip": ping_skip
#     }
    
#     if snmp_community:
#         data["snmp_community"] = snmp_community
    
#     result = await obs_request("/devices/", method="POST", data=data)
#     return json.dumps(result, indent=2)

# @mcp.tool()
# async def delete_device(device_id: str) -> str:
#     """Delete a device from Observium"""
#     result = await obs_request(f"/devices/{device_id}/", method="DELETE")
#     return json.dumps(result, indent=2)

# @mcp.tool()
# async def update_device(device_id: str, ignore: int = None, disabled: int = None, 
#                        purpose: str = None, ignore_until: str = None) -> str:
#     """Update device settings"""
#     data = {}
#     if ignore is not None:
#         data["ignore"] = ignore
#     if disabled is not None:
#         data["disabled"] = disabled
#     if purpose is not None:
#         data["purpose"] = purpose
#     if ignore_until is not None:
#         data["ignore_until"] = ignore_until
    
#     result = await obs_request(f"/devices/{device_id}/", method="PUT", data=data)
#     return json.dumps(result, indent=2)

# @mcp.tool()
# async def ignore_alert(alert_id: str, ignore_until_ok: int = None, ignore_until: str = None) -> str:
#     """Ignore/acknowledge an alert"""
#     data = {}
#     if ignore_until_ok is not None:
#         data["ignore_until_ok"] = ignore_until_ok
#     if ignore_until is not None:
#         data["ignore_until"] = ignore_until
    
#     result = await obs_request(f"/alerts/{alert_id}/", method="PUT", data=data)
#     return json.dumps(result, indent=2)

# if __name__ == "__main__":
#     if not OBSERVIUM_URL or not OBSERVIUM_USER or not OBSERVIUM_PASS:
#         print("Error: Set OBSERVIUM_URL, OBSERVIUM_USER, and OBSERVIUM_PASS")
#         exit(1)
#     mcp.run()