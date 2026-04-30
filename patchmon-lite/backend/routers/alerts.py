from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List, Optional
from pydantic import BaseModel

from core.config import get_session, settings
from models.models import AlertRule, TelegramConfig
from services.telegram_service import send_test_alert, send_telegram

router = APIRouter(prefix="/alerts", tags=["alerts"])


class TelegramConfigInput(BaseModel):
    bot_token: str
    chat_id: str


class AlertRuleCreate(BaseModel):
    name: str
    description: str
    event_type: str
    enabled: bool = True
    telegram_chat_id: Optional[str] = None


@router.get("/telegram/status", response_model=dict)
def telegram_status(db: Session = Depends(get_session)):
    cfg = db.exec(select(TelegramConfig).where(TelegramConfig.is_active == True)).first()
    has_env = bool(settings.telegram_bot_token and settings.telegram_chat_id)
    return {
        "configured": bool(cfg or has_env),
        "source": "database" if cfg else ("env" if has_env else "none"),
        "chat_id": cfg.chat_id if cfg else (settings.telegram_chat_id or None),
    }


@router.post("/telegram/connect", response_model=dict)
async def connect_telegram(data: TelegramConfigInput, db: Session = Depends(get_session)):
    # Test the connection first
    ok = await send_test_alert("connection_test", bot_token=data.bot_token, chat_id=data.chat_id)
    if not ok:
        raise HTTPException(400, "Could not send test message. Check bot token and chat ID.")

    # Deactivate existing configs
    existing = db.exec(select(TelegramConfig)).all()
    for e in existing:
        e.is_active = False
        db.add(e)

    db.add(TelegramConfig(bot_token=data.bot_token, chat_id=data.chat_id, is_active=True))
    db.commit()
    return {"success": True, "message": "Telegram connected. Test message sent."}


@router.get("/rules", response_model=List[dict])
def list_rules(db: Session = Depends(get_session)):
    rules = db.exec(select(AlertRule)).all()
    return [{"id": r.id, "name": r.name, "description": r.description, "event_type": r.event_type, "enabled": r.enabled} for r in rules]


@router.post("/rules", response_model=dict, status_code=201)
def create_rule(data: AlertRuleCreate, db: Session = Depends(get_session)):
    rule = AlertRule(**data.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return {"id": rule.id, "name": rule.name}


@router.patch("/rules/{rule_id}", response_model=dict)
def toggle_rule(rule_id: int, enabled: bool, db: Session = Depends(get_session)):
    rule = db.get(AlertRule, rule_id)
    if not rule:
        raise HTTPException(404, "Rule not found")
    rule.enabled = enabled
    db.add(rule)
    db.commit()
    return {"id": rule.id, "enabled": rule.enabled}


@router.post("/test/{event_type}", response_model=dict)
async def test_alert(event_type: str, db: Session = Depends(get_session)):
    cfg = db.exec(select(TelegramConfig).where(TelegramConfig.is_active == True)).first()
    token = cfg.bot_token if cfg else settings.telegram_bot_token
    chat = cfg.chat_id if cfg else settings.telegram_chat_id

    if not token or not chat:
        raise HTTPException(400, "Telegram not configured")

    ok = await send_test_alert(event_type, bot_token=token, chat_id=chat)
    return {"success": ok, "event_type": event_type}
