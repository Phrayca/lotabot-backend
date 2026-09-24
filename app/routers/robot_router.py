from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..auth import get_current_user
from ..plan_utils import enforce_trial_expiry, subscription_allows_robot

router = APIRouter(prefix="/api/robot", tags=["robot"])

LOCKED_MESSAGE = "Le robot a été désactivé par l'équipe Lotabot sur ce compte. Contacte le support pour en savoir plus."


def effective_active(robot: models.RobotSettings) -> bool:
    """Ce que le bridge doit VRAIMENT faire : le reglage du client, sauf si l'admin a pose
    un verrou, auquel cas le robot ne trade jamais, quel que soit "active"."""
    return bool(robot and robot.active and not robot.admin_disabled)


def _to_robot_out(user: models.User) -> schemas.RobotOut:
    r = user.robot_settings
    plan = user.subscription.plan if user.subscription else "classique"
    return schemas.RobotOut(
        active=r.active, riskLevel=r.risk_level, lot=r.lot, maxPositions=r.max_positions,
        plan=plan, pair=r.pair, adminDisabled=r.admin_disabled, adminDisabledReason=r.admin_disabled_reason,
    )


@router.get("", response_model=schemas.RobotOut)
def get_robot(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    enforce_trial_expiry(user, db)
    return _to_robot_out(user)


@router.put("", response_model=schemas.RobotOut)
def update_robot(payload: schemas.RobotIn, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    enforce_trial_expiry(user, db)
    r = user.robot_settings
    plan = user.subscription.plan if user.subscription else "classique"

    if payload.riskLevel is not None and payload.riskLevel != r.risk_level and plan != "premium":
        raise HTTPException(status_code=403, detail="Le niveau de risque personnalisé est réservé à la formule Premium")

    if payload.active is True:
        if r.admin_disabled:
            raise HTTPException(status_code=403, detail=r.admin_disabled_reason or LOCKED_MESSAGE)
        if not subscription_allows_robot(user):
            raise HTTPException(status_code=403, detail="Ton essai est terminé : active ton abonnement pour réactiver le robot")

    if payload.active is not None:
        r.active = payload.active
    if payload.riskLevel is not None:
        r.risk_level = payload.riskLevel
    if payload.lot is not None:
        r.lot = payload.lot
    if payload.maxPositions is not None:
        r.max_positions = payload.maxPositions
    db.commit()
    return _to_robot_out(user)


@router.put("/toggle", response_model=schemas.RobotOut)
def toggle_robot(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    enforce_trial_expiry(user, db)
    r = user.robot_settings
    new_state = not r.active
    if new_state:
        if r.admin_disabled:
            raise HTTPException(status_code=403, detail=r.admin_disabled_reason or LOCKED_MESSAGE)
        if not subscription_allows_robot(user):
            raise HTTPException(status_code=403, detail="Ton essai est terminé : active ton abonnement pour réactiver le robot")
    r.active = new_state
    db.commit()
    return _to_robot_out(user)
