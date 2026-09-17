from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, seed
from ..database import get_db
from ..auth import hash_password, verify_password, create_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=schemas.TokenOut)
def register(payload: schemas.RegisterIn, db: Session = Depends(get_db)):
    phone = payload.phone.strip()
    if db.query(models.User).filter(models.User.phone == phone).first():
        raise HTTPException(status_code=400, detail="Ce numéro est déjà utilisé")
    if len(payload.password) < 4:
        raise HTTPException(status_code=400, detail="Mot de passe trop court (4 caractères min)")
    plan = payload.plan if payload.plan in ("classique", "premium") else "classique"

    user = models.User(
        full_name=payload.fullName.strip(),
        phone=phone,
        password_hash=hash_password(payload.password),
        balance=0.0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    seed.bootstrap_user(db, user, plan=plan)

    return {"token": create_token(user.id)}


@router.post("/login", response_model=schemas.TokenOut)
def login(payload: schemas.LoginIn, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.phone == payload.phone.strip()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Numéro ou mot de passe incorrect")
    return {"token": create_token(user.id)}
