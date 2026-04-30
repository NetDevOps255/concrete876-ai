from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from enum import Enum


class HostStatus(str, Enum):
    online = "online"
    offline = "offline"
    unknown = "unknown"


class PatchStatus(str, Enum):
    pending = "pending"
    scheduled = "scheduled"
    patching = "patching"
    current = "current"
    failed = "failed"
    reboot_required = "reboot_required"


class JobStatus(str, Enum):
    running = "running"
    success = "success"
    failed = "failed"
    dry_run = "dry_run"


class ContainerState(str, Enum):
    running = "running"
    stopped = "stopped"
    paused = "paused"
    restarting = "restarting"


# ─── Host ────────────────────────────────────────────────────────────────────

class Host(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hostname: str = Field(index=True, unique=True)
    ip_address: str
    ssh_user: str = "root"
    ssh_port: int = 22
    ssh_key_path: Optional[str] = None

    os_name: Optional[str] = None
    os_version: Optional[str] = None
    os_codename: Optional[str] = None
    kernel: Optional[str] = None
    pkg_manager: Optional[str] = None  # apt, dnf, apk, pacman, pkg

    status: HostStatus = HostStatus.unknown
    patch_status: PatchStatus = PatchStatus.unknown
    pending_count: int = 0
    reboot_required: bool = False

    # Proxmox metadata
    proxmox_vmid: Optional[int] = None
    proxmox_type: Optional[str] = None  # qemu, lxc
    proxmox_node: Optional[str] = None

    last_seen: Optional[datetime] = None
    last_patched: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    packages: List["Package"] = Relationship(back_populates="host")
    jobs: List["PatchJob"] = Relationship(back_populates="host")
    containers: List["DockerContainer"] = Relationship(back_populates="host")


# ─── Package ─────────────────────────────────────────────────────────────────

class Package(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    host_id: int = Field(foreign_key="host.id")
    name: str
    current_version: str
    available_version: Optional[str] = None
    is_security: bool = False
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    host: Optional[Host] = Relationship(back_populates="packages")


# ─── PatchJob ────────────────────────────────────────────────────────────────

class PatchJob(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    host_id: int = Field(foreign_key="host.id")
    triggered_by: str = "scheduler"
    status: JobStatus = JobStatus.running
    is_dry_run: bool = False
    packages_updated: int = 0
    output: Optional[str] = None
    error: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None

    host: Optional[Host] = Relationship(back_populates="jobs")


# ─── DockerContainer ─────────────────────────────────────────────────────────

class DockerContainer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    host_id: int = Field(foreign_key="host.id")
    container_id: str
    name: str
    image: str
    image_digest: Optional[str] = None
    remote_digest: Optional[str] = None
    state: ContainerState = ContainerState.stopped
    ports: Optional[str] = None
    is_outdated: bool = False
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    host: Optional[Host] = Relationship(back_populates="containers")


# ─── AuditLog ────────────────────────────────────────────────────────────────

class LogLevel(str, Enum):
    info = "INFO"
    ok = "OK"
    warn = "WARN"
    error = "ERROR"


class AuditLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    level: LogLevel = LogLevel.info
    event: str
    host_id: Optional[int] = None
    hostname: Optional[str] = None
    detail: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ─── AlertRule ────────────────────────────────────────────────────────────────

class AlertRule(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: str
    event_type: str   # patch_available, reboot_required, docker_outdated, patch_applied, vm_offline
    enabled: bool = True
    telegram_chat_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ─── TelegramConfig ───────────────────────────────────────────────────────────

class TelegramConfig(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    bot_token: str
    chat_id: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
