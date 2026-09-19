import random
import string
import secrets
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from . import models
from .auth import hash_password

TRIAL_DAYS = 2

DEFAULT_COURSES = [
    {
        "title": "Bienvenue sur Lotabot",
        "duration_min": 4,
        "meta_label": "Prise en main",
        "premium": False,
        "order": 1,
        "body": (
            "Lotabot fait trader un robot automatique sur l'or (XAUUSD) à ta place. "
            "Tu n'as rien à faire au quotidien : le robot surveille le marché, ouvre et ferme "
            "les positions tout seul, avec des règles de sécurité strictes (stop loss toujours actif, "
            "limite de perte par jour, arrêt automatique en cas de problème).\n\n"
            "Ton rôle à toi : connecter ton compte MT5, choisir un niveau de risque qui te convient, "
            "et suivre tes résultats dans l'onglet Accueil. C'est tout."
        ),
    },
    {
        "title": "C'est quoi le XAUUSD ?",
        "duration_min": 6,
        "meta_label": "Fondamentaux",
        "premium": False,
        "order": 2,
        "body": (
            "XAUUSD, c'est simplement le prix de l'or (Gold) exprimé en dollars américains. "
            "\"XAU\" est le code international de l'or, \"USD\" celui du dollar.\n\n"
            "Quand le prix XAUUSD monte, ça veut dire que l'once d'or vaut plus de dollars qu'avant. "
            "C'est l'un des marchés les plus tradés au monde, avec beaucoup de mouvement (volatilité) "
            "et une bonne liquidité — ce qui en fait un terrain adapté pour un robot automatique bien réglé."
        ),
    },
    {
        "title": "Comprendre le risque, en 5 minutes",
        "duration_min": 5,
        "meta_label": "Fondamentaux",
        "premium": False,
        "order": 3,
        "body": (
            "Trader, ce n'est pas deviner si le prix va monter ou descendre — c'est gérer ce que tu risques "
            "de perdre à chaque tentative.\n\n"
            "Le robot Lotabot ne mise jamais tout ton capital sur un seul trade : il calcule une petite "
            "part de risque à chaque position (en général 1 % de ton capital), et pose toujours un "
            "stop loss automatique pour limiter la perte si le marché part dans le mauvais sens.\n\n"
            "Retiens une chose : même le meilleur robot du monde perd parfois. Ce qui compte, c'est que "
            "les pertes restent petites et contrôlées, et que les gains, sur la durée, l'emportent."
        ),
    },
    {
        "title": "Choisir son niveau de risque",
        "duration_min": 5,
        "meta_label": "Prise en main",
        "premium": False,
        "order": 4,
        "body": (
            "Dans l'onglet Robot, tu peux régler le niveau de risque : Prudent, Modéré ou Agressif.\n\n"
            "Prudent : le robot prend moins de positions, avec des tailles plus petites. Les gains sont "
            "plus lents, mais les variations de ton solde aussi.\n\n"
            "Modéré : un bon compromis pour la plupart des gens, c'est le réglage par défaut.\n\n"
            "Agressif : plus de positions et des tailles plus grandes. Les gains peuvent être plus rapides, "
            "mais les pertes aussi. Ne passe en Agressif que si tu es à l'aise avec l'idée de voir ton "
            "solde varier davantage."
        ),
    },
    {
        "title": "Lire ton historique de trades",
        "duration_min": 6,
        "meta_label": "Prise en main",
        "premium": False,
        "order": 5,
        "body": (
            "Dans l'onglet Historique, chaque ligne est un trade que le robot a passé pour toi : la paire "
            "(XAUUSD), l'heure, et le résultat (en vert si gagnant, en rouge si perdant).\n\n"
            "Ne panique pas devant une ligne rouge isolée : c'est normal et attendu, même une stratégie "
            "solide perd une partie de ses trades. Ce qui compte, c'est le résultat cumulé sur la semaine "
            "ou le mois, visible sur l'écran Accueil."
        ),
    },
    {
        "title": "Gestion du risque avancée",
        "duration_min": 12,
        "meta_label": "Stratégie",
        "premium": True,
        "order": 6,
        "body": (
            "Le robot utilise trois garde-fous en plus du stop loss classique : une limite de perte "
            "journalière (il s'arrête pour la journée s'il est touché), un objectif de gain journalier "
            "optionnel (pour sécuriser les gains du jour), et un coupe-circuit global sur le drawdown "
            "(désactivation automatique si le capital chute trop par rapport à son sommet).\n\n"
            "Ces réglages avancés sont configurés au niveau du robot lui-même par notre équipe, pour "
            "protéger ton capital même dans les pires scénarios de marché."
        ),
    },
]


def make_referral_code(full_name: str) -> str:
    base = "".join(ch for ch in full_name.upper() if ch.isalpha())[:6] or "LOTA"
    suffix = "".join(random.choices(string.digits, k=2))
    return base + suffix


def seed_courses(db: Session):
    existing_titles = {c.title for c in db.query(models.Course).all()}
    for c in DEFAULT_COURSES:
        if c["title"] not in existing_titles:
            db.add(models.Course(**c))
    db.commit()


def bootstrap_user(db: Session, user: models.User, plan: str = "classique"):
    """Crée toutes les entités liées à un nouvel utilisateur (réglages robot,
    abonnement en essai gratuit, code de parrainage, préférences de notifications, MT5)."""
    price = 15000.0 if plan == "premium" else 10000.0
    trial_end = datetime.utcnow() + timedelta(days=TRIAL_DAYS)

    user.trial_ends_at = trial_end

    db.add(models.RobotSettings(user_id=user.id))
    db.add(models.Subscription(
        user_id=user.id,
        plan=plan,
        price=price,
        status="trialing",
        payment_method="orange",
        renews_at=trial_end,
    ))
    db.add(models.Referral(user_id=user.id, code=make_referral_code(user.full_name)))
    db.add(models.NotificationPrefs(user_id=user.id))
    db.add(models.MT5Connection(user_id=user.id, connected=False, sync_token=secrets.token_hex(16)))
    db.commit()
