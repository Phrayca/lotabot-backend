"""
Lotabot Backend - Espace admin (point 1 : lecture seule)
-----------------------------------------------------------
Comptes admin totalement separes des comptes clients (table a part, jamais melangee
a models.User). Le mot de passe est hache avec scrypt (bibliotheque standard de Python,
pas de dependance supplementaire). Une connexion cree un jeton aleatoire renvoye au
navigateur ; seule son empreinte (sha256) est gardee en base, jamais le jeton lui-meme.

Creer ou changer le mot de passe d'un admin : POST /api/admin/bootstrap, protege par
BRIDGE_INTERNAL_SECRET (jamais depuis l'app, jamais un mot de passe colle dans un chat -
appelle cette route toi-meme depuis PowerShell). Rejouable : rappeler avec un nouveau
mot de passe le change.
"""
import hashlib
import os
import secrets as _secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from .legal_router import pending_documents
from .support_router import _to_detail as _to_support_detail
from .trades_router import _robot_status, _week_change_pct

router = APIRouter(prefix="/api/admin", tags=["admin"])

SESSION_LIFETIME_DAYS = 7
_SCRYPT_PARAMS = dict(n=16384, r=8, p=1, dklen=32)


def _hash_password(password: str) -> str:
    salt = _secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, **_SCRYPT_PARAMS)
    return f"scrypt${salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        algo, salt_hex, hash_hex = stored.split("$")
        if algo != "scrypt":
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, **_SCRYPT_PARAMS)
        return _secrets.compare_digest(digest, expected)
    except (ValueError, TypeError):
        return False


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def get_current_admin(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> models.AdminUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Connexion admin requise")
    token = authorization[len("Bearer "):].strip()
    session = (
        db.query(models.AdminSession)
        .filter(models.AdminSession.token_hash == _hash_token(token))
        .first()
    )
    if not session or session.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Session admin expirée, reconnecte-toi")
    return session.admin


@router.post("/bootstrap")
def bootstrap(
    payload: schemas.AdminBootstrapIn,
    x_internal_secret: str = Header(default=None, alias="X-Internal-Secret"),
    db: Session = Depends(get_db),
):
    expected = os.getenv("BRIDGE_INTERNAL_SECRET")
    if not expected or not x_internal_secret or not _secrets.compare_digest(x_internal_secret.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Clé interne invalide")

    email = payload.email.strip().lower()
    admin = db.query(models.AdminUser).filter(models.AdminUser.email == email).first()
    if admin:
        admin.password_hash = _hash_password(payload.password)
        created = False
    else:
        admin = models.AdminUser(email=email, password_hash=_hash_password(payload.password))
        db.add(admin)
        created = True
    db.commit()
    return {"ok": True, "created": created}


@router.post("/login", response_model=schemas.AdminTokenOut)
def login(payload: schemas.AdminLoginIn, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    admin = db.query(models.AdminUser).filter(models.AdminUser.email == email).first()
    # Meme message que le mot de passe soit faux ou l'e-mail inconnu : ne pas laisser deviner
    # quels e-mails sont enregistres comme admin.
    if not admin or not _verify_password(payload.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="E-mail ou mot de passe incorrect")

    token = _secrets.token_hex(32)
    db.add(models.AdminSession(
        admin_id=admin.id,
        token_hash=_hash_token(token),
        expires_at=datetime.utcnow() + timedelta(days=SESSION_LIFETIME_DAYS),
    ))
    db.commit()
    return schemas.AdminTokenOut(token=token, email=admin.email)


def _mask_account(account_number: Optional[str]) -> Optional[str]:
    if not account_number or len(account_number) < 4:
        return None
    return f"•••• {account_number[-4:]}"


@router.get("/clients", response_model=schemas.AdminClientsOut)
def list_clients(
    _admin: models.AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    clients = []
    for user in db.query(models.User).order_by(models.User.created_at.desc()).all():
        mt5 = user.mt5_connection
        robot = user.robot_settings
        sub = user.subscription
        robot_status, robot_message = _robot_status(mt5, robot)
        clients.append(schemas.AdminClientOut(
            id=user.id,
            fullName=user.full_name,
            phone=user.phone,
            plan=sub.plan if sub else "classique",
            subscriptionStatus=sub.status if sub else "trialing",
            mt5Connected=mt5.connected if mt5 else False,
            brokerServer=mt5.broker_server if mt5 else None,
            accountMasked=_mask_account(mt5.account_number if mt5 else None),
            robotStatus=robot_status,
            robotStatusMessage=robot_message,
            legalUpToDate=len(pending_documents(user, db)) == 0,
            balanceUsd=round(user.balance, 2),
            createdAt=user.created_at,
        ))
    return schemas.AdminClientsOut(clients=clients)


@router.get("/clients/{client_id}", response_model=schemas.AdminClientDetailOut)
def get_client(
    client_id: str,
    _admin: models.AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == client_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Client introuvable")

    mt5 = user.mt5_connection
    robot = user.robot_settings
    sub = user.subscription
    robot_status, robot_message = _robot_status(mt5, robot)

    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    week_trades = [t for t in user.trades if t.opened_at >= week_ago]
    week_change_pct = _week_change_pct(user.balance, week_trades)
    open_trades = len([t for t in user.trades if t.status == "open"])

    acceptances = (
        db.query(models.LegalAcceptance)
        .filter(models.LegalAcceptance.user_id == user.id)
        .order_by(models.LegalAcceptance.accepted_at.desc())
        .all()
    )
    recent = sorted(user.trades, key=lambda t: t.opened_at, reverse=True)[:30]

    return schemas.AdminClientDetailOut(
        id=user.id,
        fullName=user.full_name,
        phone=user.phone,
        email=user.email,
        city=user.city,
        createdAt=user.created_at,
        plan=sub.plan if sub else "classique",
        subscriptionStatus=sub.status if sub else "trialing",
        subscriptionRenewsAt=sub.renews_at if sub else None,
        mt5Connected=mt5.connected if mt5 else False,
        brokerServer=mt5.broker_server if mt5 else None,
        accountMasked=_mask_account(mt5.account_number if mt5 else None),
        robotStatus=robot_status,
        robotStatusMessage=robot_message,
        riskLevel=robot.risk_level if robot else 1,
        lot=robot.lot if robot else 0.01,
        maxPositions=robot.max_positions if robot else 1,
        balanceUsd=round(user.balance, 2),
        weekChangePct=week_change_pct,
        openTrades=open_trades,
        legalAcceptances=[
            schemas.AdminLegalAcceptanceOut(
                slug=a.slug, version=a.version, acceptedAt=a.accepted_at, ipAddress=a.ip_address
            )
            for a in acceptances
        ],
        recentTrades=[
            schemas.AdminTradeOut(
                externalId=t.external_id, pair=t.pair, amountUsd=round(t.amount, 2),
                status=t.status, openedAt=t.opened_at,
            )
            for t in recent
        ],
    )


def _get_client_or_404(client_id: str, db: Session) -> models.User:
    user = db.query(models.User).filter(models.User.id == client_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Client introuvable")
    return user


@router.put("/clients/{client_id}/robot", response_model=schemas.RobotOut)
def set_robot_active(
    client_id: str,
    payload: schemas.AdminRobotActionIn,
    _admin: models.AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Met le robot en pause ou le reactive, depuis l'admin. Le client peut aussi le faire
    lui-meme dans l'app : les deux ecrivent le meme reglage, le dernier gagne."""
    user = _get_client_or_404(client_id, db)
    robot = user.robot_settings
    if not robot:
        raise HTTPException(status_code=400, detail="Ce client n'a pas encore de reglages robot")
    robot.active = payload.active
    db.commit()
    plan = user.subscription.plan if user.subscription else "classique"
    return schemas.RobotOut(active=robot.active, riskLevel=robot.risk_level, lot=robot.lot,
                             maxPositions=robot.max_positions, plan=plan)


@router.post("/clients/{client_id}/mt5/restart")
def restart_mt5(
    client_id: str,
    _admin: models.AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Force le bridge a redemarrer le worker de ce compte (nouveau terminal MT5, nouvel etat
    de strategie) - c'est ce qui sort reellement un compte d'un arret de securite, puisque ce
    dernier vit en memoire dans le worker et non en base."""
    user = _get_client_or_404(client_id, db)
    m = user.mt5_connection
    if not m or not m.connected:
        raise HTTPException(status_code=400, detail="Ce client n'a pas de compte MT5 connecte")
    m.bridge_status = "pending"
    m.bridge_error = None
    m.force_restart_requested_at = datetime.utcnow()
    db.commit()
    return {"ok": True}


@router.post("/clients/{client_id}/subscription/extend", response_model=schemas.SubscriptionOut)
def extend_subscription(
    client_id: str,
    payload: schemas.AdminExtendSubscriptionIn,
    _admin: models.AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if payload.days <= 0:
        raise HTTPException(status_code=400, detail="Le nombre de jours doit etre positif")
    user = _get_client_or_404(client_id, db)
    sub = user.subscription
    if not sub:
        raise HTTPException(status_code=400, detail="Ce client n'a pas d'abonnement")
    base = sub.renews_at if sub.renews_at and sub.renews_at > datetime.utcnow() else datetime.utcnow()
    sub.renews_at = base + timedelta(days=payload.days)
    if sub.status in ("expired", "cancelled"):
        sub.status = "active"
    db.commit()
    return schemas.SubscriptionOut(plan=sub.plan, price=sub.price, renewsAt=sub.renews_at,
                                    status=sub.status, paymentMethod=sub.payment_method)


@router.get("/clients/{client_id}/notes", response_model=schemas.AdminNotesOut)
def list_notes(
    client_id: str,
    _admin: models.AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    _get_client_or_404(client_id, db)
    notes = (
        db.query(models.AdminNote)
        .filter(models.AdminNote.user_id == client_id)
        .order_by(models.AdminNote.created_at.desc())
        .all()
    )
    admins = {a.id: a.email for a in db.query(models.AdminUser).all()}
    return schemas.AdminNotesOut(notes=[
        schemas.AdminNoteOut(id=n.id, body=n.body, createdAt=n.created_at, adminEmail=admins.get(n.admin_id, "?"))
        for n in notes
    ])


@router.post("/clients/{client_id}/notes", response_model=schemas.AdminNotesOut)
def add_note(
    client_id: str,
    payload: schemas.AdminNoteIn,
    admin: models.AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    _get_client_or_404(client_id, db)
    body = payload.body.strip()
    if not body:
        raise HTTPException(status_code=400, detail="La note est vide")
    db.add(models.AdminNote(user_id=client_id, admin_id=admin.id, body=body))
    db.commit()
    return list_notes(client_id, admin, db)


# ---------------------------------------------------------------------------
# Support (cote admin) : voit toutes les conversations, repond, change le statut.
# La mise en forme des messages reutilise support_router._to_detail (cote client)
# pour ne jamais avoir deux facons differentes d'afficher la meme conversation.
# ---------------------------------------------------------------------------

def _to_admin_ticket_out(t: models.SupportTicket) -> schemas.AdminSupportTicketOut:
    last = t.messages[-1] if t.messages else None
    return schemas.AdminSupportTicketOut(
        id=t.id, clientId=t.user_id, clientName=t.user.full_name, subject=t.subject, status=t.status,
        createdAt=t.created_at, updatedAt=t.updated_at,
        lastMessage=last.body if last else None, lastSenderType=last.sender_type if last else None,
    )


@router.get("/support", response_model=schemas.AdminSupportTicketsOut)
def admin_list_support_tickets(
    status: Optional[str] = None,
    _admin: models.AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    query = db.query(models.SupportTicket)
    if status:
        query = query.filter(models.SupportTicket.status == status)
    tickets = query.order_by(models.SupportTicket.updated_at.desc()).all()
    return schemas.AdminSupportTicketsOut(tickets=[_to_admin_ticket_out(t) for t in tickets])


def _get_any_ticket_or_404(ticket_id: str, db: Session) -> models.SupportTicket:
    ticket = db.query(models.SupportTicket).filter(models.SupportTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    return ticket


@router.get("/support/{ticket_id}", response_model=schemas.SupportTicketDetailOut)
def admin_get_ticket(
    ticket_id: str,
    _admin: models.AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return _to_support_detail(_get_any_ticket_or_404(ticket_id, db))


@router.post("/support/{ticket_id}/reply", response_model=schemas.SupportTicketDetailOut)
def admin_reply(
    ticket_id: str,
    payload: schemas.SupportMessageIn,
    admin: models.AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    ticket = _get_any_ticket_or_404(ticket_id, db)
    body = payload.body.strip()
    if not body:
        raise HTTPException(status_code=400, detail="Le message est vide")

    db.add(models.SupportMessage(ticket_id=ticket.id, sender_type="admin", sender_label=admin.email, body=body))
    if ticket.status == "open":
        ticket.status = "in_progress"
    ticket.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(ticket)
    return _to_support_detail(ticket)


@router.put("/support/{ticket_id}/status", response_model=schemas.SupportTicketDetailOut)
def admin_set_ticket_status(
    ticket_id: str,
    payload: schemas.AdminSupportStatusIn,
    _admin: models.AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if payload.status not in ("open", "in_progress", "resolved"):
        raise HTTPException(status_code=400, detail="Statut invalide")
    ticket = _get_any_ticket_or_404(ticket_id, db)
    ticket.status = payload.status
    ticket.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(ticket)
    return _to_support_detail(ticket)
