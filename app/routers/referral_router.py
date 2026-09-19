from fastapi import APIRouter, Depends

from .. import models, schemas
from ..auth import get_current_user

router = APIRouter(prefix="/api/referral", tags=["referral"])


@router.get("", response_model=schemas.ReferralOut)
def get_referral(user: models.User = Depends(get_current_user)):
    r = user.referral
    return schemas.ReferralOut(code=r.code, referredCount=r.referred_count, creditFcfa=r.credit_fcfa)
