import os
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..auth import get_current_user

router = APIRouter(prefix="/api/mt5", tags=["mt5"])

MT5_SYNC_SECRET = os.getenv("MT5_SYNC_SECRET")


@router.get("", response_model=schemas.MT5StatusOut)
def get_status(user: models.User = Depends(get_current_user)):
    m = user.mt5_connection
    if not m or not m.connected:
        return schemas.MT5StatusOut(connected=False)
    return schemas.MT5StatusOut(connected=True, brokerServer=m.broker_server, accountNumber=m.account_number)


@router.post("/connect", response_model=schemas.MT5ConnectOut)
def connect(payload: schemas.MT5ConnectIn, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    m = user.mt5_connection
    m.connected = True
    m.broker_server = payload.brokerServer
    m.account_number = payload.accountNumber
    # Le mot de passe investisseur n'est jamais stocké en clair.
    m.investor_password_enc = "•" * len(payload.investorPassword)
    # Tant que le pont MT5 réel (EA côté serveur) n'est pas branché, on reste en mode démo :
    # le robot affichera un statut connecté mais ne copiera pas encore de trades réels.
    m.demo_mode = True
    db.commit()
    return schemas.MT5ConnectOut(demoMode=m.demo_mode)


@router.post("/disconnect")
def disconnect(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    m = user.mt5_connection
    m.connected = False
    m.broker_server = None
    m.account_number = None
    m.investor_password_enc = None
    db.commit()
    return {"ok": True}


@router.post("/sync", response_model=schemas.SyncOut)
def sync(
    payload: schemas.SyncIn,
    db: Session = Depends(get_db),
    x_sync_secret: str = Header(default=None, alias="X-Sync-Secret"),
):
    """Reçoit les données envoyées par le script local (sync_mt5.py) tournant
    sur le PC de l'utilisateur, et met à jour le solde, le statut MT5 et
    l'historique des trades. Sécurisé par une clé partagée (MT5_SYNC_SECRET),
    pas par le compte de l'utilisateur connecté à l'app."""
    if not MT5_SYNC_SECRET or x_sync_secret != MT5_SYNC_SECRET:
        raise HTTPException(status_code=401, detail="Clé de synchronisation invalide")

    user = db.query(models.User).filter(models.User.phone == payload.phone).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    user.balance = payload.balance

    m = user.mt5_connection
    m.connected = True
    if payload.brokerServer:
        m.broker_server = payload.brokerServer
    if payload.accountNumber:
        m.account_number = payload.accountNumber
    m.demo_mode = False

    created = 0
    for t in payload.trades:
        existing = (
            db.query(models.Trade)
            .filter(models.Trade.user_id == user.id, models.Trade.external_id == t.externalId)
            .first()
        )
        if existing:
            existing.status = t.status
            existing.amount = t.amount
        else:
            db.add(models.Trade(
                user_id=user.id,
                pair=t.pair,
                amount=t.amount,
                opened_at=t.openedAt,
                status=t.status,
                external_id=t.externalId,
            ))
            created += 1

    db.commit()
    return schemas.SyncOut(ok=True, tradesReceived=len(payload.trades), tradesCreated=created)
