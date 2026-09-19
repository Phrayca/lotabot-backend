from datetime import datetime

from . import models


def enforce_trial_expiry(user: models.User, db) -> None:
    """Si l'essai gratuit est dépassé sans qu'un abonnement ait été activé,
    on coupe le robot et on marque l'abonnement comme expiré. Appelé à chaque
    fois qu'on a besoin d'un état fiable (dashboard, réglages robot)."""
    sub = user.subscription
    if not sub or sub.status != "trialing":
        return
    if sub.renews_at and datetime.utcnow() > sub.renews_at:
        sub.status = "expired"
        if user.robot_settings:
            user.robot_settings.active = False
        db.commit()


def subscription_allows_robot(user: models.User) -> bool:
    sub = user.subscription
    return bool(sub and sub.status in ("active", "trialing"))
