"""
Background scheduler — runs patch checks, docker scans, proxmox sync.
Uses APScheduler with AsyncIO.
"""
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlmodel import Session, select

from core.config import settings, engine
from models.models import Host, Package, DockerContainer, AuditLog, AlertRule, LogLevel, PatchStatus, HostStatus
from services import ssh_service, docker_service, proxmox_service, telegram_service

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


def log_event(level: LogLevel, event: str, hostname: str = None, host_id: int = None, detail: str = None):
    with Session(engine) as db:
        db.add(AuditLog(level=level, event=event, hostname=hostname, host_id=host_id, detail=detail))
        db.commit()


async def check_host_patches(host: Host):
    """Refresh patch status for a single host."""
    logger.info(f"Checking patches for {host.hostname}")

    # Test connectivity
    rc, _, _ = await ssh_service.run_ssh(host.ip_address, "echo ok", host.ssh_user, host.ssh_port, host.ssh_key_path, timeout=8)
    with Session(engine) as db:
        db_host = db.get(Host, host.id)
        if not db_host:
            return
        if rc != 0:
            db_host.status = HostStatus.offline
            db.commit()
            log_event(LogLevel.warn, "Host unreachable", hostname=host.hostname, host_id=host.id)
            await telegram_service.alert_host_offline(host.hostname)
            return

        db_host.status = HostStatus.online
        db_host.last_seen = datetime.utcnow()

        # Detect pkg manager if missing
        if not db_host.pkg_manager:
            info = await ssh_service.get_os_info(host.ip_address, host.ssh_user, host.ssh_port, host.ssh_key_path)
            db_host.pkg_manager = info.get("pkg_manager")
            db_host.os_name = info.get("os_name")
            db_host.os_version = info.get("os_version")
            db_host.kernel = info.get("kernel")

        if not db_host.pkg_manager:
            db.commit()
            return

        # Get upgradable packages
        pkgs = await ssh_service.list_upgradable(
            host.ip_address, host.ssh_user, host.ssh_port,
            db_host.pkg_manager, host.ssh_key_path
        )

        # Clear old pending packages, insert new
        existing = db.exec(select(Package).where(Package.host_id == host.id)).all()
        for ep in existing:
            db.delete(ep)

        for p in pkgs:
            db.add(Package(
                host_id=host.id,
                name=p["name"],
                current_version=p.get("current_version", ""),
                available_version=p.get("available_version", ""),
            ))

        db_host.pending_count = len(pkgs)

        # Reboot check
        if db_host.pkg_manager:
            db_host.reboot_required = await ssh_service.check_reboot_required(
                host.ip_address, host.ssh_user, host.ssh_port,
                db_host.pkg_manager, host.ssh_key_path
            )

        # Update patch status
        if db_host.reboot_required:
            db_host.patch_status = PatchStatus.reboot_required
        elif db_host.pending_count > 0:
            db_host.patch_status = PatchStatus.pending
        else:
            db_host.patch_status = PatchStatus.current

        db.commit()

    log_event(LogLevel.info, f"Patch check complete: {len(pkgs)} pending", hostname=host.hostname, host_id=host.id)

    # Fire alert if patches available
    if pkgs:
        await telegram_service.alert_patches_available(host.hostname, len(pkgs))
    if host.reboot_required:
        await telegram_service.alert_reboot_required(host.hostname)


async def run_patch_checks():
    """Run patch check for all hosts."""
    with Session(engine) as db:
        hosts = db.exec(select(Host)).all()
    for host in hosts:
        try:
            await check_host_patches(host)
        except Exception as e:
            logger.error(f"Patch check failed for {host.hostname}: {e}")
            log_event(LogLevel.error, f"Patch check error: {e}", hostname=host.hostname, host_id=host.id)


async def run_docker_scans():
    """Scan docker containers on all hosts."""
    with Session(engine) as db:
        hosts = db.exec(select(Host)).all()

    for host in hosts:
        try:
            containers = await docker_service.scan_host_containers(
                host.ip_address, host.ssh_user, host.ssh_port, host.ssh_key_path
            )
            if not containers:
                continue

            with Session(engine) as db:
                # Clear old container records for this host
                old = db.exec(select(DockerContainer).where(DockerContainer.host_id == host.id)).all()
                for oc in old:
                    db.delete(oc)

                outdated = []
                for c in containers:
                    db.add(DockerContainer(
                        host_id=host.id,
                        container_id=c["container_id"],
                        name=c["name"],
                        image=c["image"],
                        image_digest=c.get("image_digest"),
                        remote_digest=c.get("remote_digest"),
                        state=c["state"],
                        ports=c.get("ports"),
                        is_outdated=c.get("is_outdated", False),
                    ))
                    if c.get("is_outdated"):
                        outdated.append(c["name"])
                db.commit()

            if outdated:
                log_event(LogLevel.warn, f"Outdated images: {', '.join(outdated)}", hostname=host.hostname, host_id=host.id)
                await telegram_service.alert_docker_outdated(host.hostname, outdated)
            else:
                log_event(LogLevel.ok, "Docker scan complete, all images current", hostname=host.hostname, host_id=host.id)
        except Exception as e:
            logger.error(f"Docker scan failed for {host.hostname}: {e}")


async def sync_proxmox():
    """Sync VM/LXC list from Proxmox API, auto-enroll new LXCs."""
    if not await proxmox_service.is_configured():
        return

    guests = await proxmox_service.get_all_guests()
    if not guests:
        return

    log_event(LogLevel.info, f"Proxmox sync: {len(guests)} VMs/CTs discovered")

    with Session(engine) as db:
        for g in guests:
            vmid = g["vmid"]
            name = g.get("name", f"vm-{vmid}")

            # Check if host already exists
            existing = db.exec(select(Host).where(Host.proxmox_vmid == vmid)).first()
            if existing:
                existing.status = HostStatus.online if g["status"] == "running" else HostStatus.offline
                # Send alert if VM went offline
                if g["status"] != "running" and existing.status == HostStatus.online:
                    await telegram_service.alert_vm_offline(name, vmid)
                db.commit()
                continue

            # Auto-enroll LXCs (we can get their IP via API)
            if g["type"] == "lxc":
                ip = await proxmox_service.get_lxc_ip(vmid)
                if ip:
                    db.add(Host(
                        hostname=name,
                        ip_address=ip,
                        ssh_user=settings.ssh_default_user,
                        proxmox_vmid=vmid,
                        proxmox_type="lxc",
                        proxmox_node=settings.proxmox_node,
                        status=HostStatus.online if g["status"] == "running" else HostStatus.offline,
                    ))
                    log_event(LogLevel.ok, f"Auto-enrolled LXC: {name} ({ip})")
            else:
                # VMs: try guest agent for IP
                ip = await proxmox_service.get_vm_agent_ip(vmid)
                db.add(Host(
                    hostname=name,
                    ip_address=ip or "",
                    ssh_user=settings.ssh_default_user,
                    proxmox_vmid=vmid,
                    proxmox_type="qemu",
                    proxmox_node=settings.proxmox_node,
                    status=HostStatus.online if g["status"] == "running" else HostStatus.offline,
                ))
            db.commit()


def start_scheduler():
    scheduler.add_job(run_patch_checks, "interval", seconds=settings.patch_check_interval, id="patch_checks", replace_existing=True)
    scheduler.add_job(run_docker_scans, "interval", seconds=settings.docker_check_interval, id="docker_scans", replace_existing=True)
    scheduler.add_job(sync_proxmox, "interval", seconds=settings.proxmox_sync_interval, id="proxmox_sync", replace_existing=True)
    scheduler.start()
    logger.info("Scheduler started")
