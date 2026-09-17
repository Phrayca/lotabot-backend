import random
import string
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from . import models
from .auth import hash_password

DEFAULT_COURSES = [
    {"title": "Gestion du risque", "duration_min": 12, "meta_label": "Fondamentaux", "premium": True, "order": 1},
    {"title": "Comprendre le XAUUSD", "duration_min": 9, "meta_label": "Fondamentaux", "premium": False, "order": 2},
    {"title": "Support et résistance", "duration_min": 15, "meta_label": "Stratégie", "premium": True, "order": 3},
    {"title": "Psychologie du trader", "duration_min": 11, "meta_label": "Mindset", "premium": True, "order": 4},
    {"title": "Lire une bougie japonaise", "duration_min": 8, "meta_label": "Fondamentaux", "premium": False, "order": 5},
    {"title": "Régler son robot Lotabot", "duration_min": 6, "meta_label": "Prise en main", "premium": False, "order": 6},
]


def make_referral_code(full_name: str) -> str:
    base = "".join(ch for ch in full_name.upper() if ch.isalpha())[:6] or "LOTA"
    suffix = "".join(random.choices(string.digits, k=2))
    return base + suffix


def seed_courses(db: Session):
    if db.query(models.Course).count() > 0:
        return
    for c in DEFAULT_COURSES:
        db.add(models.Course(**c))
    db.commit()


def bootstrap_user(db: Session, user: models.User, plan: str = "classique"):
    """Crée toutes les entités liées à un nouvel utilisateur (réglages robot,
    abonnement, code de parrainage, préférences de notifications, MT5)."""
    price = 15000.0 if plan == "premium" else 10000.0

    db.add(models.RobotSettings(user_id=user.id))
    db.add(models.Subscription(
        user_id=user.id,
        plan=plan,
        price=price,
        status="trialing",
        payment_method="orange",
        renews_at=datetime.utcnow() + timedelta(days=30),
    ))
    db.add(models.Referral(user_id=user.id, code=make_referral_code(user.full_name)))
    db.add(models.NotificationPrefs(user_id=user.id))
    db.add(models.MT5Connection(user_id=user.id, connected=False))
    db.commit()


def seed_demo_account(db: Session):
    """Compte de démonstration correspondant aux valeurs pré-remplies de la maquette
    (téléphone 771715238 / mot de passe demo1234)."""
    existing = db.query(models.User).filter(models.User.phone == "771715238").first()
    if existing:
        return

    user = models.User(
        full_name="Amadou Diop",
        phone="771715238",
        email="amadou.diop@email.com",
        dob="14/03/1990",
        city="Dakar",
        password_hash=hash_password("demo1234"),
        id_verified=True,
        selfie_verified=False,
        balance=284500.0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    bootstrap_user(db, user, plan="premium")

    sub = db.query(models.Subscription).filter(models.Subscription.user_id == user.id).first()
    sub.status = "active"
    sub.payment_method = "orange"

    robot = db.query(models.RobotSettings).filter(models.RobotSettings.user_id == user.id).first()
    robot.active = True
    robot.risk_level = 1

    mt5 = db.query(models.MT5Connection).filter(models.MT5Connection.user_id == user.id).first()
    mt5.connected = True
    mt5.broker_server = "JustMarkets-MT5Real"
    mt5.account_number = "10025821"
    mt5.demo_mode = True

    ref = db.query(models.Referral).filter(models.Referral.user_id == user.id).first()
    ref.referred_count = 3
    ref.months_earned = 2

    now = datetime.utcnow()
    demo_trades = [
        (0, "XAUUSD", 18500), (0, "XAUUSD", -4200), (0, "XAUUSD", 9800),
        (1, "XAUUSD", 12300), (1, "XAUUSD", -3100),
        (2, "XAUUSD", 6700), (2, "XAUUSD", 5400), (2, "XAUUSD", -2200),
    ]
    for days_ago, pair, amount in demo_trades:
        db.add(models.Trade(
            user_id=user.id, pair=pair, amount=amount,
            opened_at=now - timedelta(days=days_ago, hours=random.randint(1, 10)),
            status="closed",
        ))
    db.commit()
