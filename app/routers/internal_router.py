import os
import secrets
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..crypto_utils import decrypt_secret
from .robot_router import effective_active

router = APIRouter(prefix="/api/internal", tags=["internal"])

BRIDGE_INTERNAL_SECRET = os.getenv("BRIDGE_INTERNAL_SECRET")


def _check_secret(x_internal_secret: str = Header(default=None, alias="X-Internal-Secret")):
    # Comparaison en temps constant : ne laisse pas deviner la clé caractère par caractère
    if (
        not BRIDGE_INTERNAL_SECRET
        or not x_internal_secret
        or not secrets.compare_digest(x_internal_secret.encode(), BRIDGE_INTERNAL_SECRET.encode())
    ):
        raise HTTPException(status_code=401, detail="Clé interne invalide")


@router.post("/migrate", include_in_schema=False)
def migrate(db: Session = Depends(get_db), _=Depends(_check_secret)):
    """A appeler UNE FOIS apres ce deploiement (puis a nouveau seulement si une future mise a
    jour ajoute une colonne a une table qui existe deja : create_all ne le fait jamais tout
    seul, contrairement a la creation d'une table entierement nouvelle)."""
    statements = [
        "ALTER TABLE mt5_connections ADD COLUMN IF NOT EXISTS force_restart_requested_at TIMESTAMP",
        "ALTER TABLE support_tickets ADD COLUMN IF NOT EXISTS client_last_read_at TIMESTAMP",
        "ALTER TABLE support_tickets ADD COLUMN IF NOT EXISTS admin_last_read_at TIMESTAMP",
        "ALTER TABLE support_messages ALTER COLUMN body DROP NOT NULL",
        "ALTER TABLE support_messages ADD COLUMN IF NOT EXISTS attachment_data TEXT",
        "ALTER TABLE support_messages ADD COLUMN IF NOT EXISTS attachment_name VARCHAR",
        "ALTER TABLE support_messages ADD COLUMN IF NOT EXISTS attachment_is_image BOOLEAN DEFAULT FALSE",
        "ALTER TABLE robot_settings ADD COLUMN IF NOT EXISTS admin_disabled BOOLEAN DEFAULT FALSE",
        "ALTER TABLE robot_settings ADD COLUMN IF NOT EXISTS admin_disabled_reason VARCHAR",
        "ALTER TABLE robot_settings ADD COLUMN IF NOT EXISTS admin_disabled_at TIMESTAMP",
    ]
    applied = []
    for stmt in statements:
        db.execute(text(stmt))
        applied.append(stmt)
    db.commit()
    return {"ok": True, "applied": applied}


@router.get("/accounts", response_model=list[schemas.BridgeAccountOut])
def list_accounts(db: Session = Depends(get_db), _=Depends(_check_secret)):
    """Utilisé uniquement par le serveur de trading (le bridge), jamais par l'app
    ni par un client. Renvoie les comptes MT5 à faire tourner, avec leur mot de
    passe déchiffré à la volée pour cet usage précis."""
    connections = (
        db.query(models.MT5Connection)
        .filter(models.MT5Connection.connected == True)  # noqa: E712
        .filter(models.MT5Connection.trading_password_enc.isnot(None))
        .all()
    )
    out = []
    for m in connections:
        if not m.sync_token or not m.broker_server or not m.account_number:
            continue
        try:
            password = decrypt_secret(m.trading_password_enc)
        except RuntimeError:
            continue
        robot = m.user.robot_settings
        out.append(schemas.BridgeAccountOut(
            syncToken=m.sync_token,
            brokerServer=m.broker_server,
            accountNumber=m.account_number,
            password=password,
            desiredActive=effective_active(robot),
            riskLevel=robot.risk_level if robot else None,
            lot=robot.lot if robot else None,
            maxPositions=robot.max_positions if robot else None,
            pair=robot.pair if robot else "XAUUSD",
            restartNonce=m.force_restart_requested_at.isoformat() if m.force_restart_requested_at else None,
        ))
    return out


@router.post("/accounts/{sync_token}/status")
def report_status(sync_token: str, payload: schemas.BridgeStatusIn, db: Session = Depends(get_db), _=Depends(_check_secret)):
    m = db.query(models.MT5Connection).filter(models.MT5Connection.sync_token == sync_token).first()
    if not m:
        raise HTTPException(status_code=404, detail="Compte introuvable")
    m.bridge_status = payload.status
    m.bridge_error = payload.error
    db.commit()
    return {"ok": True}
