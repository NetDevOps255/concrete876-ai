from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select
from typing import List, Optional
import csv, io
from fastapi.responses import StreamingResponse

from core.config import get_session
from models.models import AuditLog

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/", response_model=List[dict])
def list_logs(
    limit: int = Query(100, le=500),
    hostname: Optional[str] = None,
    level: Optional[str] = None,
    db: Session = Depends(get_session)
):
    query = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    logs = db.exec(query).all()

    if hostname:
        logs = [l for l in logs if l.hostname == hostname]
    if level:
        logs = [l for l in logs if l.level.value == level.upper()]

    return [{
        "id": l.id,
        "level": l.level,
        "event": l.event,
        "hostname": l.hostname,
        "detail": l.detail,
        "created_at": l.created_at.isoformat(),
    } for l in logs]


@router.get("/export/csv")
def export_csv(db: Session = Depends(get_session)):
    logs = db.exec(select(AuditLog).order_by(AuditLog.created_at.desc())).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["timestamp", "level", "hostname", "event", "detail"])
    for l in logs:
        writer.writerow([l.created_at.isoformat(), l.level.value, l.hostname or "", l.event, l.detail or ""])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=patchmon-audit.csv"}
    )


@router.get("/summary", response_model=dict)
def log_summary(db: Session = Depends(get_session)):
    from datetime import datetime, timedelta
    from sqlmodel import func
    since = datetime.utcnow() - timedelta(hours=24)
    all_logs = db.exec(select(AuditLog).where(AuditLog.created_at >= since)).all()
    return {
        "total_24h": len(all_logs),
        "ok": sum(1 for l in all_logs if l.level.value == "OK"),
        "warn": sum(1 for l in all_logs if l.level.value == "WARN"),
        "error": sum(1 for l in all_logs if l.level.value == "ERROR"),
        "info": sum(1 for l in all_logs if l.level.value == "INFO"),
    }
