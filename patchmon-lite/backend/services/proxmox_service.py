"""
Proxmox API service.
Uses API token auth (no password needed).
Auto-enrolls LXC containers and discovers VMs.
"""
import httpx
import logging
from typing import List, Optional
from core.config import settings

logger = logging.getLogger(__name__)


def _headers() -> dict:
    if not settings.proxmox_token_id or not settings.proxmox_token_secret:
        return {}
    return {
        "Authorization": f"PVEAPIToken={settings.proxmox_token_id}={settings.proxmox_token_secret}"
    }


def _base_url() -> str:
    host = settings.proxmox_host
    if not host.startswith("http"):
        host = f"https://{host}"
    return f"{host}/api2/json"


async def get_nodes() -> List[dict]:
    """List Proxmox cluster nodes."""
    try:
        async with httpx.AsyncClient(verify=False, timeout=10) as client:
            r = await client.get(f"{_base_url()}/nodes", headers=_headers())
            r.raise_for_status()
            return r.json().get("data", [])
    except Exception as e:
        logger.error(f"Proxmox get_nodes failed: {e}")
        return []


async def get_vms(node: str = None) -> List[dict]:
    """Get all QEMU VMs on a node."""
    node = node or settings.proxmox_node
    try:
        async with httpx.AsyncClient(verify=False, timeout=10) as client:
            r = await client.get(f"{_base_url()}/nodes/{node}/qemu", headers=_headers())
            r.raise_for_status()
            vms = r.json().get("data", [])
            return [{"vmid": v["vmid"], "name": v.get("name",""), "status": v.get("status",""), "type": "qemu"} for v in vms]
    except Exception as e:
        logger.error(f"Proxmox get_vms failed: {e}")
        return []


async def get_lxcs(node: str = None) -> List[dict]:
    """Get all LXC containers on a node."""
    node = node or settings.proxmox_node
    try:
        async with httpx.AsyncClient(verify=False, timeout=10) as client:
            r = await client.get(f"{_base_url()}/nodes/{node}/lxc", headers=_headers())
            r.raise_for_status()
            lxcs = r.json().get("data", [])
            return [{"vmid": l["vmid"], "name": l.get("name",""), "status": l.get("status",""), "type": "lxc"} for l in lxcs]
    except Exception as e:
        logger.error(f"Proxmox get_lxcs failed: {e}")
        return []


async def get_all_guests(node: str = None) -> List[dict]:
    """Return combined list of all VMs and LXCs."""
    vms = await get_vms(node)
    lxcs = await get_lxcs(node)
    return vms + lxcs


async def get_lxc_ip(vmid: int, node: str = None) -> Optional[str]:
    """Try to get the IP of an LXC container via network interfaces."""
    node = node or settings.proxmox_node
    try:
        async with httpx.AsyncClient(verify=False, timeout=10) as client:
            r = await client.get(
                f"{_base_url()}/nodes/{node}/lxc/{vmid}/interfaces",
                headers=_headers()
            )
            r.raise_for_status()
            ifaces = r.json().get("data", [])
            for iface in ifaces:
                if iface.get("name") != "lo":
                    for addr in iface.get("inet", "").split(","):
                        addr = addr.strip()
                        if addr and "/" in addr:
                            return addr.split("/")[0]
    except Exception as e:
        logger.debug(f"Could not get LXC {vmid} IP: {e}")
    return None


async def get_vm_agent_ip(vmid: int, node: str = None) -> Optional[str]:
    """Get VM IP via QEMU guest agent (requires agent installed)."""
    node = node or settings.proxmox_node
    try:
        async with httpx.AsyncClient(verify=False, timeout=10) as client:
            r = await client.get(
                f"{_base_url()}/nodes/{node}/qemu/{vmid}/agent/network-get-interfaces",
                headers=_headers()
            )
            r.raise_for_status()
            data = r.json().get("data", {}).get("result", [])
            for iface in data:
                if iface.get("name") in ("lo",):
                    continue
                for addr in iface.get("ip-addresses", []):
                    if addr.get("ip-address-type") == "ipv4":
                        return addr["ip-address"]
    except Exception as e:
        logger.debug(f"Could not get VM {vmid} agent IP: {e}")
    return None


async def is_configured() -> bool:
    return bool(settings.proxmox_host and settings.proxmox_token_id and settings.proxmox_token_secret)
