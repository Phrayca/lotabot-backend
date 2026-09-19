from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..auth import get_current_user

router = APIRouter(prefix="/api/robot", tags=["robot"])


def _to_robot_out(user: models.User) -> schemas.RobotOut:
    r = user.robot_settings
    plan = user.subscription.plan if user.subscription else "classique"
    return schemas.RobotOut(active=r.active, riskLevel=r.risk_level, lot=r.lot, maxPositions=r.max_positions, plan=plan)


@router.get("", response_model=schemas.RobotOut)
def get_robot(user: models.User = Depends(get_current_user)):
    return _to_robot_out(user)


@router.put("", response_model=schemas.RobotOut)
def update_robot(payload: schemas.RobotIn, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = user.robot_settings
    plan = user.subscription.plan if user.subscription else "classique"

    if payload.riskLevel is not None and payload.riskLevel != r.risk_level and plan != "premium":
        raise HTTPException(status_code=403, detail="Le niveau de risque personnalisé est réservé à la formule Premium")

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
    r = user.robot_settings
    r.active = not r.active
    db.commit()
    return _to_robot_out(user)
