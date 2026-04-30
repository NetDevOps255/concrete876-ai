from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional
from pydantic import BaseModel

from services import proxmox_service
from services.scheduler import sync_proxmox

router = APIRouter(prefix="/proxmox", tags=["proxmox"])


class ProxmoxConfig(BaseModel):
    host: str
    token_id: str
    token_secret: str
    node: str = "pve"


@router.get("/guests", response_model=list)
async def list_guests(node: Optional[str] = None):
    if not await proxmox_service.is_configured():
        raise HTTPException(400, "Proxmox not configured. Set PROXMOX_HOST, PROXMOX_TOKEN_ID, PROXMOX_TOKEN_SECRET.")
    return await proxmox_service.get_all_guests(node)


@router.post("/sync", status_code=202)
async def trigger_sync(background_tasks: BackgroundTasks):
    if not await proxmox_service.is_configured():
        raise HTTPException(400, "Proxmox not configured.")
    background_tasks.add_task(sync_proxmox)
    return {"message": "Proxmox sync queued"}


@router.get("/status", response_model=dict)
async def proxmox_status():
    configured = await proxmox_service.is_configured()
    if not configured:
        return {"configured": False}
    nodes = await proxmox_service.get_nodes()
    return {"configured": True, "nodes": nodes}
