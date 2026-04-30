"""
PatchMon Lite — FastAPI backend
"""
import logging
from contextlib import asynccontextmanager
from collections import defaultdict
from time import time

from fastapi import FastAPI, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import create_db_and_tables, engine, settings
from models.models import AlertRule
from routers import hosts, docker_router, proxmox, alerts, logs
from routers.auth import router as auth_router
from services.scheduler import start_scheduler
from sqlmodel import Session, select
from core.auth import require_auth

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def seed_default_alert_rules(db: Session):
    existing = db.exec(select(AlertRule)).first()
    if existing:
        return
    defaults = [
        AlertRule(name="patch_available",       description="Notify when any host has pending updates",        event_type="patch_available", enabled=True),
        AlertRule(name="reboot_required",        description="Critical alert when kernel update needs reboot", event_type="reboot_required", enabled=True),
        AlertRule(name="docker_image_outdated",  description="Daily digest of outdated container images",      event_type="docker_outdated", enabled=True),
        AlertRule(name="patch_applied",          description="Success confirmation after each patch run",      event_type="patch_applied",   enabled=True),
        AlertRule(name="proxmox_vm_offline",     description="Alert when a VM/CT goes to stopped state",      event_type="vm_offline",      enabled=True),
    ]
    for rule in defaults:
        db.add(rule)
    db.commit()
    logger.info("Seeded default alert rules")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting PatchMon Lite...")
    if settings.secret_key in ("change-me", ""):
        logger.warning("SECRET_KEY not set — generate one: openssl rand -hex 32")
    if not settings.admin_password_hash:
        logger.warning("ADMIN_PASSWORD_HASH not set — run: python3 scripts/hash_password.py")
    if not settings.api_key:
        logger.warning("API_KEY not set — API key auth disabled")

    create_db_and_tables()
    with Session(engine) as db:
        seed_default_alert_rules(db)
    start_scheduler()
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="PatchMon Lite",
    description="Self-hosted patch management, Docker monitoring, Proxmox integration, Telegram alerting",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — only configured origins, not wildcard
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers.pop("server", None)
    return response


_rate_store: dict = defaultdict(list)

@app.middleware("http")
async def rate_limit_auth(request: Request, call_next):
    if request.url.path == "/auth/login":
        ip = request.client.host
        now = time()
        window = 60
        _rate_store[ip] = [t for t in _rate_store[ip] if now - t < window]
        if len(_rate_store[ip]) >= settings.auth_rate_limit:
            return JSONResponse(
                status_code=429,
                content={"detail": f"Too many login attempts. Try again in {window}s."},
                headers={"Retry-After": str(window)},
            )
        _rate_store[ip].append(now)
    return await call_next(request)


# Auth router is public
app.include_router(auth_router)

# All other routers require auth
app.include_router(hosts.router,         dependencies=[Depends(require_auth)])
app.include_router(docker_router.router, dependencies=[Depends(require_auth)])
app.include_router(proxmox.router,       dependencies=[Depends(require_auth)])
app.include_router(alerts.router,        dependencies=[Depends(require_auth)])
app.include_router(logs.router,          dependencies=[Depends(require_auth)])


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/stats", dependencies=[Depends(require_auth)])
def stats():
    from sqlmodel import func
    from models.models import Host, DockerContainer, HostStatus
    with Session(engine) as db:
        hosts_total   = db.exec(select(func.count()).select_from(Host)).one()
        hosts_online  = db.exec(select(func.count()).select_from(Host).where(Host.status == HostStatus.online)).one()
        pending       = db.exec(select(func.sum(Host.pending_count)).select_from(Host)).one() or 0
        reboot_req    = db.exec(select(func.count()).select_from(Host).where(Host.reboot_required == True)).one()
        outdated_dock = db.exec(select(func.count()).select_from(DockerContainer).where(DockerContainer.is_outdated == True)).one()
        return {
            "hosts_total": hosts_total,
            "hosts_online": hosts_online,
            "pending_updates": int(pending),
            "reboot_required": reboot_req,
            "outdated_containers": outdated_dock,
        }
