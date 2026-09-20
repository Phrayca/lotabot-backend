import os
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..crypto_utils import decrypt_secret

router = APIRouter(prefix="/api/internal", tags=["internal"])

BRIDGE_INTERNAL_SECRET = os.getenv("BRIDGE_INTERNAL_SECRET")


def _check_secret(x_internal_secret: str = Header(default=None, alias="X-Internal-Secret")):
    if not BRIDGE_INTERNAL_SECRET or x_internal_secret != BRIDGE_INTERNAL_SECRET:
        raise HTTPException(status_code=401, detail="Clé interne invalide")


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
        out.append(schemas.BridgeAccountOut(
            syncToken=m.sync_token,
            brokerServer=m.broker_server,
            accountNumber=m.account_number,
            password=password,
            desiredActive=m.user.robot_settings.active if m.user.robot_settings else False,
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
