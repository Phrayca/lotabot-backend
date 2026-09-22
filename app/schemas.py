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
    # Statut affiché à l'écran d'accueil : active | paused | safety_stop | not_connected
    robotStatus: str = "not_connected"
    robotStatusMessage: Optional[str] = None


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
    # Change de valeur = signal au bridge de redemarrer ce worker (ex: sortir d'un arret de securite)
    restartNonce: Optional[str] = None


class BridgeStatusIn(BaseModel):
    status: str  # pending | running | safety_stop | error
    error: Optional[str] = None


class AdminBootstrapIn(BaseModel):
    email: str
    password: str


class AdminLoginIn(BaseModel):
    email: str
    password: str


class AdminTokenOut(BaseModel):
    token: str
    email: str


class AdminClientOut(BaseModel):
    id: str
    fullName: str
    phone: str
    plan: str
    subscriptionStatus: str
    mt5Connected: bool
    brokerServer: Optional[str] = None
    accountMasked: Optional[str] = None
    robotStatus: str
    robotStatusMessage: Optional[str] = None
    legalUpToDate: bool
    balanceUsd: float
    createdAt: datetime


class AdminClientsOut(BaseModel):
    clients: List[AdminClientOut]


class AdminLegalAcceptanceOut(BaseModel):
    slug: str
    version: str
    acceptedAt: datetime
    ipAddress: Optional[str] = None


class AdminTradeOut(BaseModel):
    externalId: Optional[str] = None
    pair: str
    amountUsd: float
    status: str
    openedAt: datetime


class AdminClientDetailOut(BaseModel):
    id: str
    fullName: str
    phone: str
    email: Optional[str] = None
    city: Optional[str] = None
    createdAt: datetime
    plan: str
    subscriptionStatus: str
    subscriptionRenewsAt: Optional[datetime] = None
    mt5Connected: bool
    brokerServer: Optional[str] = None
    accountMasked: Optional[str] = None
    robotStatus: str
    robotStatusMessage: Optional[str] = None
    riskLevel: int
    lot: float
    maxPositions: int
    balanceUsd: float
    weekChangePct: float
    openTrades: int
    legalAcceptances: List[AdminLegalAcceptanceOut]
    recentTrades: List[AdminTradeOut]


class AdminRobotActionIn(BaseModel):
    active: bool


class AdminExtendSubscriptionIn(BaseModel):
    days: int


class AdminNoteIn(BaseModel):
    body: str


class AdminNoteOut(BaseModel):
    id: str
    body: str
    createdAt: datetime
    adminEmail: str


class AdminNotesOut(BaseModel):
    notes: List[AdminNoteOut]


class LegalDocumentOut(BaseModel):
    slug: str
    title: str
    version: str
    body: str


class LegalStatusOut(BaseModel):
    pending: List[LegalDocumentOut]
    allAccepted: bool


class LegalAcceptIn(BaseModel):
    slugs: List[str]


class LegalAcceptOut(BaseModel):
    ok: bool
    accepted: List[str]
