"""
Lotabot Backend - Support (cote client)
------------------------------------------
Chaque client ne voit et n'ecrit que dans SES PROPRES conversations (filtre
systematique sur user_id). Le cote admin (lecture de tout, reponses, changement
de statut) vit dans admin_router.py, qui reutilise les fonctions _to_ticket_out
et _to_detail definies ici plutot que de dupliquer la mise en forme.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..auth import get_current_user

router = APIRouter(prefix="/api/support", tags=["support"])


def _last_message_time(ticket: models.SupportTicket, sender_type: str):
    times = [m.created_at for m in ticket.messages if m.sender_type == sender_type]
    return max(times) if times else None


def _has_unread(last_read_at, last_other_time) -> bool:
    if last_other_time is None:
        return False
    return last_read_at is None or last_other_time > last_read_at


def _to_ticket_out(t: models.SupportTicket) -> schemas.SupportTicketOut:
    last = t.messages[-1] if t.messages else None
    return schemas.SupportTicketOut(
        id=t.id, subject=t.subject, status=t.status,
        createdAt=t.created_at, updatedAt=t.updated_at,
        lastMessage=last.body if last else None,
        hasUnread=_has_unread(t.client_last_read_at, _last_message_time(t, "admin")),
    )


def _to_detail(t: models.SupportTicket) -> schemas.SupportTicketDetailOut:
    return schemas.SupportTicketDetailOut(
        id=t.id, subject=t.subject, status=t.status, createdAt=t.created_at,
        messages=[
            schemas.SupportMessageOut(
                id=m.id, senderType=m.sender_type, senderLabel=m.sender_label,
                body=m.body, createdAt=m.created_at,
            )
            for m in t.messages
        ],
    )


@router.get("", response_model=schemas.SupportTicketsOut)
def list_my_tickets(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    tickets = (
        db.query(models.SupportTicket)
        .filter(models.SupportTicket.user_id == user.id)
        .order_by(models.SupportTicket.updated_at.desc())
        .all()
    )
    return schemas.SupportTicketsOut(tickets=[_to_ticket_out(t) for t in tickets])


@router.post("", response_model=schemas.SupportTicketDetailOut)
def create_ticket(
    payload: schemas.SupportTicketCreateIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    subject = payload.subject.strip()
    body = payload.body.strip()
    if not subject or not body:
        raise HTTPException(status_code=400, detail="Le sujet et le message sont requis")

    ticket = models.SupportTicket(user_id=user.id, subject=subject)
    db.add(ticket)
    db.flush()
    db.add(models.SupportMessage(ticket_id=ticket.id, sender_type="client", sender_label=user.full_name, body=body))
    db.commit()
    db.refresh(ticket)
    return _to_detail(ticket)


def _get_own_ticket_or_404(ticket_id: str, user: models.User, db: Session) -> models.SupportTicket:
    ticket = (
        db.query(models.SupportTicket)
        .filter(models.SupportTicket.id == ticket_id, models.SupportTicket.user_id == user.id)
        .first()
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    return ticket


@router.get("/unread-count", response_model=schemas.UnreadCountOut)
def unread_count(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    tickets = db.query(models.SupportTicket).filter(models.SupportTicket.user_id == user.id).all()
    count = sum(1 for t in tickets if _has_unread(t.client_last_read_at, _last_message_time(t, "admin")))
    return schemas.UnreadCountOut(count=count)


@router.get("/{ticket_id}", response_model=schemas.SupportTicketDetailOut)
def get_ticket(ticket_id: str, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    ticket = _get_own_ticket_or_404(ticket_id, user, db)
    # Ouvrir la conversation = l'avoir lue : efface le badge "non lu" cote client.
    ticket.client_last_read_at = datetime.utcnow()
    db.commit()
    db.refresh(ticket)
    return _to_detail(ticket)


@router.post("/{ticket_id}/messages", response_model=schemas.SupportTicketDetailOut)
def add_message(
    ticket_id: str,
    payload: schemas.SupportMessageIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = _get_own_ticket_or_404(ticket_id, user, db)
    body = payload.body.strip()
    if not body:
        raise HTTPException(status_code=400, detail="Le message est vide")

    db.add(models.SupportMessage(ticket_id=ticket.id, sender_type="client", sender_label=user.full_name, body=body))
    # Un client qui ecrit a nouveau dans une conversation "resolue" la rouvre automatiquement.
    if ticket.status == "resolved":
        ticket.status = "open"
    ticket.updated_at = datetime.utcnow()
    ticket.client_last_read_at = ticket.updated_at
    db.commit()
    db.refresh(ticket)
    return _to_detail(ticket)
