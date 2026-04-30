"""
Docker service — inspects containers on remote hosts via SSH.
Uses `docker inspect` + `docker pull --dry-run` for digest comparison.
"""
import json
import logging
from typing import List, Optional
from services.ssh_service import run_ssh

logger = logging.getLogger(__name__)


async def get_containers(host_ip: str, username: str, port: int, key_path: str = None) -> List[dict]:
    """
    Returns list of containers with state, image, digest info.
    """
    cmd = (
        "docker ps -a --format "
        "'{{.ID}}|{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}' 2>/dev/null"
    )
    rc, stdout, _ = await run_ssh(host_ip, cmd, username, port, key_path, timeout=20)
    if rc != 0 or not stdout.strip():
        return []

    containers = []
    for line in stdout.strip().splitlines():
        parts = line.split("|")
        if len(parts) < 4:
            continue
        container_id, name, image, status_raw, ports = (parts + [""])[:5]
        state = "running" if status_raw.lower().startswith("up") else \
                "paused" if "paused" in status_raw.lower() else \
                "restarting" if "restarting" in status_raw.lower() else "stopped"
        containers.append({
            "container_id": container_id[:12],
            "name": name.lstrip("/"),
            "image": image,
            "state": state,
            "ports": ports[:200] if ports else None,
        })
    return containers


async def get_local_digest(host_ip: str, username: str, port: int, image: str, key_path: str = None) -> Optional[str]:
    """Get the local image digest (RepoDigest)."""
    cmd = f"docker inspect --format '{{{{index .RepoDigests 0}}}}' {image} 2>/dev/null"
    rc, stdout, _ = await run_ssh(host_ip, cmd, username, port, key_path, timeout=15)
    if rc == 0 and stdout.strip():
        return stdout.strip()
    return None


async def get_remote_digest(host_ip: str, username: str, port: int, image: str, key_path: str = None) -> Optional[str]:
    """
    Pull image metadata (not the full image) to get remote digest.
    Uses `docker pull --dry-run` (Docker 25+) or `skopeo` fallback.
    """
    # Try docker pull --dry-run first (Docker 25+)
    cmd = f"docker pull --dry-run {image} 2>&1 | grep 'Digest:' | awk '{{print $2}}'"
    rc, stdout, _ = await run_ssh(host_ip, cmd, username, port, key_path, timeout=30)
    if rc == 0 and stdout.strip():
        return stdout.strip()

    # Fallback: skopeo (if available)
    cmd2 = f"command -v skopeo && skopeo inspect docker://{image} 2>/dev/null | python3 -c \"import sys,json; print(json.load(sys.stdin).get('Digest',''))\" || true"
    _, stdout2, _ = await run_ssh(host_ip, cmd2, username, port, key_path, timeout=20)
    if stdout2.strip():
        return stdout2.strip()

    return None


async def check_docker_available(host_ip: str, username: str, port: int, key_path: str = None) -> bool:
    rc, _, _ = await run_ssh(host_ip, "docker version -f '{{.Server.Version}}' 2>/dev/null", username, port, key_path, timeout=10)
    return rc == 0


async def scan_host_containers(host_ip: str, username: str, port: int, key_path: str = None) -> List[dict]:
    """
    Full scan: get containers + check each for outdated images.
    Returns enriched container list.
    """
    if not await check_docker_available(host_ip, username, port, key_path):
        return []

    containers = await get_containers(host_ip, username, port, key_path)

    for c in containers:
        if c["state"] != "running":
            c["image_digest"] = None
            c["remote_digest"] = None
            c["is_outdated"] = False
            continue

        local = await get_local_digest(host_ip, username, port, c["image"], key_path)
        remote = await get_remote_digest(host_ip, username, port, c["image"], key_path)

        c["image_digest"] = local
        c["remote_digest"] = remote
        c["is_outdated"] = bool(local and remote and local != remote)

    return containers
