"""
SSH service — executes commands on managed hosts.
Handles apt/dnf/apk/pacman/pkg package managers.
"""
import asyncssh
import asyncio
import logging
from typing import Optional, Tuple
from core.config import settings

logger = logging.getLogger(__name__)

PKG_MANAGERS = {
    "apt": {
        "detect": "command -v apt-get",
        "update": "apt-get update -qq",
        "list_upgradable": "apt list --upgradable 2>/dev/null",
        "upgrade_dry": "apt-get upgrade --dry-run -y",
        "upgrade": "DEBIAN_FRONTEND=noninteractive apt-get upgrade -y",
        "reboot_check": "[ -f /var/run/reboot-required ] && echo yes || echo no",
        "os_info": "cat /etc/os-release",
        "kernel": "uname -r",
    },
    "dnf": {
        "detect": "command -v dnf",
        "update": "dnf check-update -q || true",
        "list_upgradable": "dnf list updates 2>/dev/null",
        "upgrade_dry": "dnf upgrade --assumeno 2>&1",
        "upgrade": "dnf upgrade -y",
        "reboot_check": "needs-restarting -r > /dev/null 2>&1 && echo no || echo yes",
        "os_info": "cat /etc/os-release",
        "kernel": "uname -r",
    },
    "apk": {
        "detect": "command -v apk",
        "update": "apk update -q",
        "list_upgradable": "apk list --upgradable 2>/dev/null",
        "upgrade_dry": "apk upgrade --simulate",
        "upgrade": "apk upgrade",
        "reboot_check": "echo no",
        "os_info": "cat /etc/os-release",
        "kernel": "uname -r",
    },
    "pacman": {
        "detect": "command -v pacman",
        "update": "pacman -Sy --noconfirm -q",
        "list_upgradable": "pacman -Qu 2>/dev/null",
        "upgrade_dry": "pacman -Sup --print 2>/dev/null",
        "upgrade": "pacman -Syu --noconfirm",
        "reboot_check": "echo no",
        "os_info": "cat /etc/os-release",
        "kernel": "uname -r",
    },
    "pkg": {  # FreeBSD
        "detect": "command -v pkg",
        "update": "pkg update -q",
        "list_upgradable": "pkg version -l '<' 2>/dev/null",
        "upgrade_dry": "pkg upgrade -n",
        "upgrade": "pkg upgrade -y",
        "reboot_check": "echo no",
        "os_info": "uname -a",
        "kernel": "uname -r",
    },
}


async def run_ssh(
    host_ip: str,
    command: str,
    username: str = None,
    port: int = 22,
    key_path: str = None,
    timeout: int = None,
) -> Tuple[int, str, str]:
    """Run a single SSH command. Returns (returncode, stdout, stderr)."""
    username = username or settings.ssh_default_user
    timeout = timeout or settings.ssh_command_timeout

    connect_kwargs = dict(
        host=host_ip,
        port=port,
        username=username,
        known_hosts=None,
        connect_timeout=settings.ssh_connect_timeout,
    )
    if key_path:
        connect_kwargs["client_keys"] = [key_path]

    try:
        async with asyncssh.connect(**connect_kwargs) as conn:
            result = await asyncio.wait_for(
                conn.run(command, check=False),
                timeout=timeout,
            )
            return result.exit_status, result.stdout or "", result.stderr or ""
    except asyncssh.DisconnectError as e:
        return 1, "", f"SSH disconnect: {e}"
    except asyncio.TimeoutError:
        return 1, "", f"Command timed out after {timeout}s"
    except Exception as e:
        return 1, "", f"SSH error: {e}"


async def detect_pkg_manager(host_ip: str, username: str, port: int, key_path: str = None) -> Optional[str]:
    """Probe host to detect which package manager is present."""
    for pm, cmds in PKG_MANAGERS.items():
        rc, _, _ = await run_ssh(host_ip, cmds["detect"], username, port, key_path, timeout=8)
        if rc == 0:
            return pm
    return None


async def get_os_info(host_ip: str, username: str, port: int, key_path: str = None) -> dict:
    """Fetch OS name, version, codename, kernel, pkg manager."""
    pm = await detect_pkg_manager(host_ip, username, port, key_path)
    if not pm:
        return {}

    cmds = PKG_MANAGERS[pm]
    _, os_raw, _ = await run_ssh(host_ip, cmds["os_info"], username, port, key_path)
    _, kernel, _ = await run_ssh(host_ip, cmds["kernel"], username, port, key_path)

    info = {"pkg_manager": pm, "kernel": kernel.strip()}
    for line in os_raw.splitlines():
        if line.startswith("PRETTY_NAME="):
            info["os_name"] = line.split("=", 1)[1].strip('"')
        elif line.startswith("VERSION_ID="):
            info["os_version"] = line.split("=", 1)[1].strip('"')
        elif line.startswith("VERSION_CODENAME="):
            info["os_codename"] = line.split("=", 1)[1].strip('"')
        elif line.startswith("ID=") and "os_name" not in info:
            info["os_name"] = line.split("=", 1)[1].strip('"')

    return info


async def list_upgradable(host_ip: str, username: str, port: int, pkg_manager: str, key_path: str = None) -> list:
    """Return list of dicts: {name, current_version, available_version}."""
    cmds = PKG_MANAGERS.get(pkg_manager, {})
    if not cmds:
        return []

    # Run update first (refresh package lists)
    await run_ssh(host_ip, cmds["update"], username, port, key_path, timeout=60)

    rc, stdout, _ = await run_ssh(host_ip, cmds["list_upgradable"], username, port, key_path, timeout=60)
    if rc != 0:
        return []

    packages = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("Listing..."):
            continue

        if pkg_manager == "apt":
            # format: "pkg/suite version arch [upgradable from: old]"
            parts = line.split()
            if len(parts) >= 2 and "/" in parts[0]:
                name = parts[0].split("/")[0]
                new_ver = parts[1]
                old_ver = ""
                if "upgradable from:" in line:
                    old_ver = line.split("upgradable from:")[-1].strip().rstrip("]")
                packages.append({"name": name, "current_version": old_ver, "available_version": new_ver})

        elif pkg_manager in ("dnf", "yum"):
            parts = line.split()
            if len(parts) >= 3 and not line.startswith("Last") and not line.startswith("Available"):
                packages.append({"name": parts[0], "current_version": "", "available_version": parts[1]})

        elif pkg_manager == "apk":
            # "pkg-1.2.3 < 1.2.4"
            parts = line.split(" < ")
            if len(parts) == 2:
                name_ver = parts[0].rsplit("-", 2)
                name = name_ver[0] if len(name_ver) > 1 else parts[0]
                packages.append({"name": name, "current_version": parts[0], "available_version": parts[1].strip()})

        elif pkg_manager == "pacman":
            # "pkg old -> new"
            parts = line.split()
            if len(parts) >= 4 and parts[2] == "->":
                packages.append({"name": parts[0], "current_version": parts[1], "available_version": parts[3]})

        elif pkg_manager == "pkg":
            # "pkg-old-ver <"
            parts = line.split()
            if parts:
                name = parts[0]
                packages.append({"name": name, "current_version": "", "available_version": "available"})

    return packages


async def check_reboot_required(host_ip: str, username: str, port: int, pkg_manager: str, key_path: str = None) -> bool:
    cmds = PKG_MANAGERS.get(pkg_manager, {})
    if not cmds:
        return False
    _, stdout, _ = await run_ssh(host_ip, cmds["reboot_check"], username, port, key_path, timeout=10)
    return stdout.strip().lower() == "yes"


async def run_upgrade(
    host_ip: str, username: str, port: int, pkg_manager: str, dry_run: bool = False, key_path: str = None
) -> Tuple[bool, str, int]:
    """Run upgrade (or dry-run). Returns (success, output, pkg_count)."""
    cmds = PKG_MANAGERS.get(pkg_manager, {})
    if not cmds:
        return False, "Unknown package manager", 0

    cmd_key = "upgrade_dry" if dry_run else "upgrade"
    rc, stdout, stderr = await run_ssh(host_ip, cmds[cmd_key], username, port, key_path, timeout=300)

    output = stdout + ("\n" + stderr if stderr else "")
    pkg_count = 0

    if not dry_run:
        for line in output.splitlines():
            l = line.lower()
            if "upgraded" in l or "newly installed" in l or "upgrade" in l:
                import re
                nums = re.findall(r"\d+", line)
                if nums:
                    pkg_count = max(pkg_count, int(nums[0]))

    return rc == 0, output[:8000], pkg_count
