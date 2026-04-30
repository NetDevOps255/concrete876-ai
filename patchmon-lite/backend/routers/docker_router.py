from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session, select
from typing import List

from core.config import get_session
from models.models import Host, DockerContainer
from services.scheduler import run_docker_scans, log_event
from services import docker_service
from models.models import LogLevel

router = APIRouter(prefix="/docker", tags=["docker"])


@router.get("/", response_model=List[dict])
def list_all_containers(db: Session = Depends(get_session)):
    containers = db.exec(select(DockerContainer)).all()
    result = []
    for c in containers:
        host = db.get(Host, c.host_id)
        result.append({
            "id": c.id,
            "host_id": c.host_id,
            "hostname": host.hostname if host else None,
            "container_id": c.container_id,
            "name": c.name,
            "image": c.image,
            "state": c.state,
            "ports": c.ports,
            "is_outdated": c.is_outdated,
            "image_digest": c.image_digest,
            "remote_digest": c.remote_digest,
            "updated_at": c.updated_at.isoformat(),
        })
    return result


@router.post("/scan", status_code=202)
async def trigger_docker_scan(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_docker_scans)
    return {"message": "Docker scan queued for all hosts"}


@router.get("/summary", response_model=dict)
def docker_summary(db: Session = Depends(get_session)):
    containers = db.exec(select(DockerContainer)).all()
    return {
        "total": len(containers),
        "running": sum(1 for c in containers if c.state == "running"),
        "stopped": sum(1 for c in containers if c.state == "stopped"),
        "outdated": sum(1 for c in containers if c.is_outdated),
    }
