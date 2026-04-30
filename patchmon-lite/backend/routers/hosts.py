from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session, select
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from core.config import get_session
from models.models import Host, Package, PatchJob, DockerContainer, JobStatus, PatchStatus, HostStatus
from services import ssh_service, docker_service
from services.scheduler import check_host_patches, log_event
from models.models import LogLevel
import logging

router = APIRouter(prefix="/hosts", tags=["hosts"])
logger = logging.getLogger(__name__)


class HostCreate(BaseModel):
    hostname: str
    ip_address: str
    ssh_user: str = "root"
    ssh_port: int = 22
    ssh_key_path: Optional[str] = None


class HostUpdate(BaseModel):
    ip_address: Optional[str] = None
    ssh_user: Optional[str] = None
    ssh_port: Optional[int] = None
    ssh_key_path: Optional[str] = None


@router.get("/", response_model=List[dict])
def list_hosts(db: Session = Depends(get_session)):
    hosts = db.exec(select(Host)).all()
    result = []
    for h in hosts:
        result.append({
            "id": h.id,
            "hostname": h.hostname,
            "ip_address": h.ip_address,
            "ssh_user": h.ssh_user,
            "ssh_port": h.ssh_port,
            "os_name": h.os_name,
            "os_version": h.os_version,
            "kernel": h.kernel,
            "pkg_manager": h.pkg_manager,
            "status": h.status,
            "patch_status": h.patch_status,
            "pending_count": h.pending_count,
            "reboot_required": h.reboot_required,
            "proxmox_vmid": h.proxmox_vmid,
            "proxmox_type": h.proxmox_type,
            "last_seen": h.last_seen.isoformat() if h.last_seen else None,
            "last_patched": h.last_patched.isoformat() if h.last_patched else None,
            "created_at": h.created_at.isoformat(),
        })
    return result


@router.post("/", response_model=dict, status_code=201)
def create_host(data: HostCreate, db: Session = Depends(get_session)):
    existing = db.exec(select(Host).where(Host.hostname == data.hostname)).first()
    if existing:
        raise HTTPException(400, "Hostname already exists")
    host = Host(**data.model_dump())
    db.add(host)
    db.commit()
    db.refresh(host)
    log_event(LogLevel.ok, f"Host added: {host.hostname}", hostname=host.hostname, host_id=host.id)
    return {"id": host.id, "hostname": host.hostname}


@router.delete("/{host_id}", status_code=204)
def delete_host(host_id: int, db: Session = Depends(get_session)):
    host = db.get(Host, host_id)
    if not host:
        raise HTTPException(404, "Host not found")
    db.delete(host)
    db.commit()


@router.get("/{host_id}/packages", response_model=List[dict])
def get_packages(host_id: int, db: Session = Depends(get_session)):
    pkgs = db.exec(select(Package).where(Package.host_id == host_id)).all()
    return [{"id": p.id, "name": p.name, "current_version": p.current_version, "available_version": p.available_version} for p in pkgs]


@router.post("/{host_id}/check", status_code=202)
async def trigger_patch_check(host_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_session)):
    host = db.get(Host, host_id)
    if not host:
        raise HTTPException(404, "Host not found")
    background_tasks.add_task(check_host_patches, host)
    return {"message": f"Patch check queued for {host.hostname}"}


@router.post("/{host_id}/patch", response_model=dict)
async def apply_patches(
    host_id: int,
    dry_run: bool = False,
    db: Session = Depends(get_session),
):
    host = db.get(Host, host_id)
    if not host:
        raise HTTPException(404, "Host not found")

    if not host.pkg_manager:
        raise HTTPException(400, "Package manager not detected. Run a patch check first.")

    # Create job record
    job = PatchJob(host_id=host.id, triggered_by="manual", is_dry_run=dry_run, status=JobStatus.running)
    db.add(job)
    db.commit()
    db.refresh(job)

    # Update host status
    host.patch_status = PatchStatus.patching
    db.add(host)
    db.commit()

    # Run upgrade
    success, output, pkg_count = await ssh_service.run_upgrade(
        host.ip_address, host.ssh_user, host.ssh_port,
        host.pkg_manager, dry_run=dry_run, key_path=host.ssh_key_path
    )

    # Update job
    with Session(db.bind) as db2:
        job2 = db2.get(PatchJob, job.id)
        host2 = db2.get(Host, host_id)
        if success:
            job2.status = JobStatus.dry_run if dry_run else JobStatus.success
            job2.packages_updated = pkg_count
            if not dry_run:
                host2.last_patched = datetime.utcnow()
                host2.pending_count = 0
                host2.patch_status = PatchStatus.current
            else:
                host2.patch_status = PatchStatus.pending
        else:
            job2.status = JobStatus.failed
            job2.error = output[-500:]
            host2.patch_status = PatchStatus.failed

        job2.output = output
        job2.finished_at = datetime.utcnow()
        db2.add(job2)
        db2.add(host2)
        db2.commit()

    level = LogLevel.ok if success else LogLevel.error
    action = "Dry run complete" if dry_run else "Patch applied"
    log_event(level, f"{action}: {host.hostname} · {pkg_count} packages", hostname=host.hostname, host_id=host.id)

    # Telegram
    from services.telegram_service import alert_patch_applied, alert_patch_failed
    if success:
        await alert_patch_applied(host.hostname, pkg_count, dry_run=dry_run)
    else:
        await alert_patch_failed(host.hostname, output[-200:])

    return {
        "job_id": job.id,
        "success": success,
        "dry_run": dry_run,
        "packages_updated": pkg_count,
        "output": output[:3000],
    }


@router.get("/{host_id}/jobs", response_model=List[dict])
def get_jobs(host_id: int, db: Session = Depends(get_session)):
    jobs = db.exec(select(PatchJob).where(PatchJob.host_id == host_id).order_by(PatchJob.started_at.desc()).limit(20)).all()
    return [{
        "id": j.id, "status": j.status, "is_dry_run": j.is_dry_run,
        "packages_updated": j.packages_updated, "triggered_by": j.triggered_by,
        "started_at": j.started_at.isoformat(), "finished_at": j.finished_at.isoformat() if j.finished_at else None,
        "output": j.output,
    } for j in jobs]


@router.get("/{host_id}/containers", response_model=List[dict])
def get_containers(host_id: int, db: Session = Depends(get_session)):
    cs = db.exec(select(DockerContainer).where(DockerContainer.host_id == host_id)).all()
    return [{
        "id": c.id, "container_id": c.container_id, "name": c.name,
        "image": c.image, "state": c.state, "ports": c.ports,
        "is_outdated": c.is_outdated, "updated_at": c.updated_at.isoformat(),
    } for c in cs]
