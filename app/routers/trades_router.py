from datetime import datetime, timedelta
from collections import OrderedDict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config import EXCHANGE_RATE_USD_FCFA
from ..database import get_db
from ..auth import get_current_user
from ..plan_utils import enforce_trial_expiry

router = APIRouter(prefix="/api/trades", tags=["trades"])

JOURS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
           "août", "septembre", "octobre", "novembre", "décembre"]

SAFETY_STOP_MESSAGE = (
    "Le robot s'est arrêté automatiquement après une baisse trop importante depuis son plus haut. "
    "Il reste en pause sur ce compte ; contacte le support pour le relancer."
)


def _day_label(d: datetime, today: datetime) -> str:
    delta = (today.date() - d.date()).days
    if delta == 0:
        return "Aujourd'hui"
    if delta == 1:
        return "Hier"
    return f"{JOURS_FR[d.weekday()].capitalize()} {d.day} {MOIS_FR[d.month - 1]}"


def _week_change_pct(balance: float, week_trades: list) -> float:
    """Variation du solde sur 7 jours, en % du solde qu'il y avait au DEBUT de la semaine.

    Seuls les trades clotures comptent : le solde (balance) n'inclut pas les gains
    ou pertes des positions encore ouvertes. Le solde de depart se deduit du solde
    actuel moins ce qui a ete gagne/perdu pendant la semaine. Diviser par le solde
    actuel (comme avant) gonflait le pourcentage apres des pertes : -138 % alors
    qu'on ne peut pas perdre plus de 100 % de son solde de depart.
    """
    closed_pnl = sum(t.amount for t in week_trades if t.status == "closed")
    start_balance = balance - closed_pnl
    if start_balance <= 0:
        return 0.0
    return round(closed_pnl / start_balance * 100, 1)


ADMIN_LOCK_MESSAGE = "L'équipe Lotabot a désactivé le robot sur ce compte. Contacte le support pour en savoir plus."


def _robot_status(mt5, robot) -> tuple[str, str | None]:
    """Statut honnête affiché à l'écran d'accueil : ce que le robot FAIT vraiment,
    pas seulement le réglage que le client a choisi. Un arrêt de sécurité déclenché
    par le bridge, ou un verrou pose par l'admin, doivent se voir ici, meme si le
    client lui-meme n'a rien désactivé."""
    if not mt5 or not mt5.connected:
        return "not_connected", None
    if robot and robot.admin_disabled:
        return "admin_disabled", robot.admin_disabled_reason or ADMIN_LOCK_MESSAGE
    if mt5.bridge_status == "safety_stop":
        return "safety_stop", mt5.bridge_error or SAFETY_STOP_MESSAGE
    if mt5.bridge_status == "error":
        return "not_connected", mt5.bridge_error
    if not robot or not robot.active:
        return "paused", None
    return "active", None


@router.get("/dashboard", response_model=schemas.DashboardOut)
def dashboard(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    enforce_trial_expiry(user, db)
    robot = user.robot_settings
    sub = user.subscription
    mt5 = user.mt5_connection
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)

    week_trades = [t for t in user.trades if t.opened_at >= week_ago]
    week_change_pct = _week_change_pct(user.balance, week_trades)

    today_trades = [t for t in user.trades if t.opened_at.date() == now.date()]
    day_gain_usd = sum(t.amount for t in today_trades)
    open_trades = len([t for t in user.trades if t.status == "open"])

    balance_usd = user.balance
    profile_complete = bool(user.email and user.dob and user.city)
    robot_status, robot_status_message = _robot_status(mt5, robot)

    return schemas.DashboardOut(
        fullName=user.full_name,
        plan=sub.plan if sub else "classique",
        balance=round(balance_usd * EXCHANGE_RATE_USD_FCFA, 2),
        balanceUsd=round(balance_usd, 2),
        weekChangePct=week_change_pct,
        robotActive=robot.active if robot else False,
        mt5Connected=mt5.connected if mt5 else False,
        pair=robot.pair if robot else "XAUUSD",
        dayGain=round(day_gain_usd * EXCHANGE_RATE_USD_FCFA, 2),
        dayGainUsd=round(day_gain_usd, 2),
        openTrades=open_trades,
        profileComplete=profile_complete,
        subscriptionStatus=sub.status if sub else "trialing",
        robotStatus=robot_status,
        robotStatusMessage=robot_status_message,
    )


RANGE_DAYS = {"today": 0, "yesterday": 1, "week": 7, "month": 30}


@router.get("/history", response_model=schemas.HistoryOut)
def history(range: str = "all", user: models.User = Depends(get_current_user)):
    if range not in ("all", *RANGE_DAYS):
        raise HTTPException(status_code=400, detail="Periode invalide")

    now = datetime.utcnow()
    trades_all = user.trades
    if range == "today":
        start = datetime(now.year, now.month, now.day)
        trades_all = [t for t in trades_all if (t.closed_at or t.opened_at) >= start]
    elif range == "yesterday":
        start = datetime(now.year, now.month, now.day) - timedelta(days=1)
        end = datetime(now.year, now.month, now.day)
        trades_all = [t for t in trades_all if start <= (t.closed_at or t.opened_at) < end]
    elif range in ("week", "month"):
        start = now - timedelta(days=RANGE_DAYS[range])
        trades_all = [t for t in trades_all if (t.closed_at or t.opened_at) >= start]

    trades_sorted = sorted(trades_all, key=lambda t: t.closed_at or t.opened_at, reverse=True)

    groups = OrderedDict()
    total_profit_usd = 0.0
    total_loss_usd = 0.0
    for t in trades_sorted:
        label_time = t.closed_at or t.opened_at
        label = _day_label(label_time, now)
        groups.setdefault(label, []).append(schemas.TradeOut(
            pair=t.pair,
            time=label_time.strftime("%H:%M"),
            amount=round(t.amount * EXCHANGE_RATE_USD_FCFA, 2),
            amountUsd=round(t.amount, 2),
            status=t.status,
            openPrice=t.open_price,
            closePrice=t.close_price,
            lots=t.lots,
            sl=t.sl,
            tp=t.tp,
            openedAt=t.opened_at,
            closedAt=t.closed_at,
        ))
        if t.status == "closed":
            if t.amount >= 0:
                total_profit_usd += t.amount
            else:
                total_loss_usd += t.amount

    return schemas.HistoryOut(
        groups=[schemas.DayGroupOut(label=label, trades=trades) for label, trades in groups.items()],
        summary=schemas.HistorySummaryOut(
            balanceUsd=round(user.balance, 2),
            totalProfitUsd=round(total_profit_usd, 2),
            totalLossUsd=round(total_loss_usd, 2),
            totalNetUsd=round(total_profit_usd + total_loss_usd, 2),
        ),
    )
