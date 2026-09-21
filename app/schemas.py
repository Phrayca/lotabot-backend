from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class RegisterIn(BaseModel):
    fullName: str
    phone: str
    password: str
    plan: str = "classique"
    referralCode: Optional[str] = None


class LoginIn(BaseModel):
    phone: str
    password: str


class ChangePasswordIn(BaseModel):
    currentPassword: str
    newPassword: str


class TokenOut(BaseModel):
    token: str


class DashboardOut(BaseModel):
    fullName: str
    plan: str
    balance: float
    balanceUsd: float
    weekChangePct: float
    robotActive: bool
    mt5Connected: bool
    pair: str
    dayGain: float
    dayGainUsd: float
    openTrades: int
    profileComplete: bool
    subscriptionStatus: str


class RobotOut(BaseModel):
    active: bool
    riskLevel: int
    lot: float
    maxPositions: int
    plan: str


class RobotIn(BaseModel):
    active: Optional[bool] = None
    riskLevel: Optional[int] = None
    lot: Optional[float] = None
    maxPositions: Optional[int] = None


class TradeOut(BaseModel):
    pair: str
    time: str
    amount: float
    amountUsd: float


class DayGroupOut(BaseModel):
    label: str
    trades: List[TradeOut]


class HistoryOut(BaseModel):
    groups: List[DayGroupOut]


class CourseOut(BaseModel):
    id: str
    title: str
    durationMin: int
    metaLabel: str
    premium: bool


class CoursesOut(BaseModel):
    courses: List[CourseOut]


class CourseDetailOut(BaseModel):
    id: str
    title: str
    durationMin: int
    metaLabel: str
    premium: bool
    body: str


class ProfileOut(BaseModel):
    fullName: str
    plan: str
    subscriptionStatus: str
    phone: str
    email: Optional[str] = ""
    dob: Optional[str] = ""
    city: Optional[str] = ""
    idVerified: bool
    avatarData: Optional[str] = None


class ProfileIn(BaseModel):
    fullName: Optional[str] = None
    email: Optional[str] = None
    dob: Optional[str] = None
    city: Optional[str] = None
    avatarData: Optional[str] = None
    idDocumentData: Optional[str] = None


class NotificationsOut(BaseModel):
    tradeAlerts: bool
    weeklyReport: bool
    promos: bool


class NotificationsIn(BaseModel):
    tradeAlerts: Optional[bool] = None
    weeklyReport: Optional[bool] = None
    promos: Optional[bool] = None


class SubscriptionOut(BaseModel):
    plan: str
    price: float
    renewsAt: datetime
    status: str
    paymentMethod: str


class PaymentMethodIn(BaseModel):
    paymentMethod: str


class ChangePlanIn(BaseModel):
    plan: str


class CancelOut(BaseModel):
    activeUntil: datetime


class ReferralOut(BaseModel):
    code: str
    referredCount: int
    creditFcfa: float


class MT5ConnectIn(BaseModel):
    brokerServer: str
    accountNumber: str
    password: str


class MT5ConnectOut(BaseModel):
    demoMode: bool


class MT5StatusOut(BaseModel):
    connected: bool
    brokerServer: Optional[str] = None
    accountNumber: Optional[str] = None
    syncToken: Optional[str] = None
    bridgeStatus: Optional[str] = None
    bridgeError: Optional[str] = None


class SyncTradeIn(BaseModel):
    externalId: str
    pair: str = "XAUUSD"
    amount: float
    openedAt: datetime
    status: str = "closed"  # open | closed


class SyncIn(BaseModel):
    balance: float
    brokerServer: Optional[str] = None
    accountNumber: Optional[str] = None
    trades: List[SyncTradeIn] = []


class SyncOut(BaseModel):
    ok: bool
    tradesReceived: int
    tradesCreated: int
    desiredActive: bool
    # Réglages du robot choisis par le client : le bridge les applique (l'EA les ignore).
    riskLevel: Optional[int] = None  # 0=prudent 1=modéré 2=agressif
    lot: Optional[float] = None
    maxPositions: Optional[int] = None


class BridgeAccountOut(BaseModel):
    syncToken: str
    brokerServer: str
    accountNumber: str
    password: str
    desiredActive: bool
    riskLevel: Optional[int] = None
    lot: Optional[float] = None
    maxPositions: Optional[int] = None


class BridgeStatusIn(BaseModel):
    status: str  # pending | running | error
    error: Optional[str] = None
