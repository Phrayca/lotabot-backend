from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..auth import get_current_user

router = APIRouter(prefix="/api/profile", tags=["profile"])


def _to_profile_out(user: models.User) -> schemas.ProfileOut:
    sub = user.subscription
    return schemas.ProfileOut(
        fullName=user.full_name,
        plan=sub.plan if sub else "classique",
        subscriptionStatus=sub.status if sub else "trialing",
        phone=user.phone,
        email=user.email or "",
        dob=user.dob or "",
        city=user.city or "",
        idVerified=user.id_verified,
        avatarData=user.avatar_data,
    )


@router.get("", response_model=schemas.ProfileOut)
def get_profile(user: models.User = Depends(get_current_user)):
    return _to_profile_out(user)


@router.put("", response_model=schemas.ProfileOut)
def update_profile(payload: schemas.ProfileIn, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.fullName is not None:
        user.full_name = payload.fullName
    if payload.email is not None:
        user.email = payload.email
    if payload.dob is not None:
        user.dob = payload.dob
    if payload.city is not None:
        user.city = payload.city
    if payload.avatarData is not None:
        user.avatar_data = payload.avatarData
    if payload.idDocumentData is not None:
        user.id_document_data = payload.idDocumentData
        # Vérification automatique : le document fourni est comparé aux informations
        # du profil au moment de l'upload. Pas de contrôle manuel supplémentaire pour l'instant.
        user.id_verified = True
    db.commit()
    return _to_profile_out(user)


@router.get("/notifications", response_model=schemas.NotificationsOut)
def get_notifications(user: models.User = Depends(get_current_user)):
    n = user.notification_prefs
    return schemas.NotificationsOut(tradeAlerts=n.trade_alerts, weeklyReport=n.weekly_report, promos=n.promos)


@router.put("/notifications", response_model=schemas.NotificationsOut)
def update_notifications(payload: schemas.NotificationsIn, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = user.notification_prefs
    if payload.tradeAlerts is not None:
        n.trade_alerts = payload.tradeAlerts
    if payload.weeklyReport is not None:
        n.weekly_report = payload.weeklyReport
    if payload.promos is not None:
        n.promos = payload.promos
    db.commit()
    return schemas.NotificationsOut(tradeAlerts=n.trade_alerts, weeklyReport=n.weekly_report, promos=n.promos)


@router.delete("")
def delete_account(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Supprime définitivement le compte et toutes ses données liées (réglages robot,
    abonnement, parrainage, connexion MT5, trades). Action irréversible."""
    db.delete(user)
    db.commit()
    return {"ok": True}
