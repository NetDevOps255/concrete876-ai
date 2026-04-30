"""
Telegram alert service.
Reads config from DB (overrides env), sends formatted messages.
"""
import logging
import httpx
from typing import Optional
from core.config import settings

logger = logging.getLogger(__name__)

# Escape chars for MarkdownV2
_ESCAPE = str.maketrans({
    "_": r"\_", "*": r"\*", "[": r"\[", "]": r"\]",
    "(": r"\(", ")": r"\)", "~": r"\~", "`": r"\`",
    ">": r"\>", "#": r"\#", "+": r"\+", "-": r"\-",
    "=": r"\=", "|": r"\|", "{": r"\{", "}": r"\}",
    ".": r"\.", "!": r"\!",
})


def esc(text: str) -> str:
    return str(text).translate(_ESCAPE)


async def send_telegram(message: str, bot_token: str = None, chat_id: str = None) -> bool:
    """Send a Telegram message. Returns True on success."""
    token = bot_token or settings.telegram_bot_token
    chat = chat_id or settings.telegram_chat_id

    if not token or not chat:
        logger.debug("Telegram not configured, skipping alert")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat,
        "text": message,
        "parse_mode": "MarkdownV2",
        "disable_web_page_preview": True,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                logger.warning(f"Telegram API error {resp.status_code}: {resp.text}")
                return False
            return True
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")
        return False


# ─── Pre-formatted alert templates ───────────────────────────────────────────

async def alert_patches_available(hostname: str, count: int, **kwargs):
    msg = (
        f"📦 *Patches Available*\n\n"
        f"Host: `{esc(hostname)}`\n"
        f"Pending updates: *{esc(str(count))}*\n\n"
        f"Login to PatchMon to review and apply\."
    )
    return await send_telegram(msg, **kwargs)


async def alert_reboot_required(hostname: str, **kwargs):
    msg = (
        f"🔄 *Reboot Required*\n\n"
        f"Host: `{esc(hostname)}`\n"
        f"A kernel or critical package update requires a reboot\."
    )
    return await send_telegram(msg, **kwargs)


async def alert_patch_applied(hostname: str, pkg_count: int, dry_run: bool = False, **kwargs):
    kind = "Dry Run Complete" if dry_run else "Patch Applied"
    icon = "🧪" if dry_run else "✅"
    msg = (
        f"{icon} *{esc(kind)}*\n\n"
        f"Host: `{esc(hostname)}`\n"
        f"Packages: *{esc(str(pkg_count))}*"
    )
    return await send_telegram(msg, **kwargs)


async def alert_patch_failed(hostname: str, error: str, **kwargs):
    msg = (
        f"❌ *Patch Failed*\n\n"
        f"Host: `{esc(hostname)}`\n"
        f"Error: `{esc(error[:200])}`"
    )
    return await send_telegram(msg, **kwargs)


async def alert_docker_outdated(hostname: str, containers: list, **kwargs):
    names = "\n".join(f"  • `{esc(c)}`" for c in containers[:10])
    msg = (
        f"🐳 *Outdated Docker Images*\n\n"
        f"Host: `{esc(hostname)}`\n"
        f"Outdated containers:\n{names}"
    )
    return await send_telegram(msg, **kwargs)


async def alert_vm_offline(hostname: str, vmid: int = None, **kwargs):
    vmid_str = f" \(VMID: {esc(str(vmid))}\)" if vmid else ""
    msg = (
        f"🔴 *VM Offline*\n\n"
        f"Host: `{esc(hostname)}`{vmid_str}\n"
        f"VM transitioned to stopped state\."
    )
    return await send_telegram(msg, **kwargs)


async def alert_host_offline(hostname: str, **kwargs):
    msg = (
        f"🔴 *Host Unreachable*\n\n"
        f"`{esc(hostname)}` is not responding to SSH\."
    )
    return await send_telegram(msg, **kwargs)


async def send_test_alert(event_type: str, bot_token: str = None, chat_id: str = None) -> bool:
    msg = (
        f"🧪 *PatchMon Test Alert*\n\n"
        f"Event: `{esc(event_type)}`\n"
        f"This is a test message from PatchMon Lite\."
    )
    return await send_telegram(msg, bot_token=bot_token, chat_id=chat_id)
