from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..auth import get_current_user

router = APIRouter(prefix="/api/mt5", tags=["mt5"])


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
