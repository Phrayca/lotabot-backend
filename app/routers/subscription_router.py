from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..auth import get_current_user

router = APIRouter(prefix="/api/subscription", tags=["subscription"])

PLAN_PRICES = {"classique": 10000.0, "premium": 15000.0}


@router.get("", response_model=schemas.SubscriptionOut)
def get_subscription(user: models.User = Depends(get_current_user)):
    s = user.subscription
    return schemas.SubscriptionOut(
        plan=s.plan, price=s.price, renewsAt=s.renews_at, status=s.status, paymentMethod=s.payment_method,
    )


@router.put("/payment-method", response_model=schemas.SubscriptionOut)
def set_payment_method(payload: schemas.PaymentMethodIn, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.paymentMethod not in ("orange", "wave"):
        raise HTTPException(status_code=400, detail="Moyen de paiement invalide")
    s = user.subscription
    s.payment_method = payload.paymentMethod
    db.commit()
    return schemas.SubscriptionOut(
        plan=s.plan, price=s.price, renewsAt=s.renews_at, status=s.status, paymentMethod=s.payment_method,
    )


@router.post("/change-plan", response_model=schemas.SubscriptionOut)
def change_plan(payload: schemas.ChangePlanIn, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.plan not in PLAN_PRICES:
        raise HTTPException(status_code=400, detail="Formule invalide")
    s = user.subscription
    s.plan = payload.plan
    s.price = PLAN_PRICES[payload.plan]
    s.status = "active"
    db.commit()
    return schemas.SubscriptionOut(
        plan=s.plan, price=s.price, renewsAt=s.renews_at, status=s.status, paymentMethod=s.payment_method,
    )


@router.post("/cancel", response_model=schemas.CancelOut)
def cancel_subscription(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = user.subscription
    s.status = "cancelled"
    db.commit()
    return schemas.CancelOut(activeUntil=s.renews_at)
