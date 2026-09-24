import secrets
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..auth import get_current_user
from ..crypto_utils import encrypt_secret
from .legal_router import legal_gate_ok

ALLOWED_PAIRS = ("XAUUSD", "EURUSD", "BTCUSD")

router = APIRouter(prefix="/api/mt5", tags=["mt5"])


@router.get("", response_model=schemas.MT5StatusOut)
def get_status(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    m = user.mt5_connection
    if not m:
        return schemas.MT5StatusOut(connected=False)
    if not m.sync_token:
        # Compte créé avant l'ajout du token personnel : on en génère un à la volée.
        m.sync_token = secrets.token_hex(16)
        db.commit()
    if not m.connected:
        return schemas.MT5StatusOut(connected=False, syncToken=m.sync_token)
    return schemas.MT5StatusOut(
        connected=True, brokerServer=m.broker_server, accountNumber=m.account_number,
        syncToken=m.sync_token, bridgeStatus=m.bridge_status, bridgeError=m.bridge_error,
    )


@router.post("/connect", response_model=schemas.MT5ConnectOut)
def connect(payload: schemas.MT5ConnectIn, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Les 3 documents (CGU, risques, autorisation MT5) doivent être acceptés à leur
    # dernière version avant de donner à Lotabot le mot de passe du compte de trading.
    if not legal_gate_ok(user, db):
        raise HTTPException(
            status_code=403,
            detail="Merci d'abord d'accepter les conditions d'utilisation avant de connecter ton compte MT5.",
        )
    if payload.pair not in ALLOWED_PAIRS:
        raise HTTPException(status_code=400, detail="Paire invalide")

    m = user.mt5_connection
    m.connected = True
    m.broker_server = payload.brokerServer
    m.account_number = payload.accountNumber
    # Chiffré, jamais stocké en clair. Seul le futur serveur de trading (le "bridge"),
    # via sa clé interne dédiée, pourra le déchiffrer pour se connecter au compte.
    m.trading_password_enc = encrypt_secret(payload.password)
    m.demo_mode = True
    m.bridge_status = "pending"
    m.bridge_error = None

    # Dès la connexion d'un compte, on repart sur un réglage prudent par défaut
    # (lot 0.01, 1 position), quel que soit ce qui était configuré avant.
    # La paire est choisie a la connexion : c'est elle qui determine le profil de
    # strategie que le bridge appliquera (voir PAIR_PROFILES cote bridge).
    robot = user.robot_settings
    if robot:
        robot.lot = 0.01
        robot.max_positions = 1
        robot.pair = payload.pair

    db.commit()
    return schemas.MT5ConnectOut(demoMode=m.demo_mode)


@router.post("/disconnect")
def disconnect(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    m = user.mt5_connection
    m.connected = False
    m.broker_server = None
    m.account_number = None
    m.trading_password_enc = None
    m.bridge_status = "disconnected"
    m.bridge_error = None
    db.commit()
    return {"ok": True}


@router.post("/sync/{sync_token}", response_model=schemas.SyncOut)
def sync(sync_token: str, payload: schemas.SyncIn, db: Session = Depends(get_db)):
    """Reçoit les données envoyées par l'EA ou le futur bridge d'UN client précis,
    identifié par son token personnel (visible dans l'app, écran Compte MT5).
    Chaque client ne peut mettre à jour que son propre compte : le token ne donne
    accès à rien d'autre, contrairement à une clé secrète partagée globale."""
    m = db.query(models.MT5Connection).filter(models.MT5Connection.sync_token == sync_token).first()
    if not m:
        raise HTTPException(status_code=401, detail="Code de synchronisation invalide")

    user = m.user
    user.balance = payload.balance

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
            existing.opened_at = t.openedAt  # corrige aussi les anciennes dates (heure serveur -> UTC)
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

    # Une position ouverte est enregistrée sous "pos-<numéro>". Quand elle se ferme, son
    # résultat arrive sous un AUTRE identifiant (le trade clôturé). Sans ce nettoyage,
    # l'ancienne ligne "ouverte" resterait indéfiniment : elle gonflerait le compteur
    # "Trades ouverts", le gain du jour, et apparaîtrait en double dans l'historique.
    open_ids = {t.externalId for t in payload.trades if t.status == "open"}
    stale_open = (
        db.query(models.Trade)
        .filter(
            models.Trade.user_id == user.id,
            models.Trade.status == "open",
            models.Trade.external_id.like("pos-%"),
        )
        .all()
    )
    for stale in stale_open:
        if stale.external_id not in open_ids:
            db.delete(stale)

    db.commit()
    robot = user.robot_settings
    return schemas.SyncOut(
        ok=True,
        tradesReceived=len(payload.trades),
        tradesCreated=created,
        desiredActive=robot.active if robot else False,
        riskLevel=robot.risk_level if robot else None,
        lot=robot.lot if robot else None,
        maxPositions=robot.max_positions if robot else None,
    )
