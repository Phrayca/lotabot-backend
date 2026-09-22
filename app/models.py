import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from .database import Base


def gen_id():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_id)
    full_name = Column(String, nullable=False)
    phone = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, nullable=True)
    dob = Column(String, nullable=True)
    city = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    id_verified = Column(Boolean, default=False)
    id_document_data = Column(Text, nullable=True)  # scan/photo de la pièce d'identité (data URL base64)
    avatar_data = Column(Text, nullable=True)  # image de profil en data URL (base64)
    balance = Column(Float, default=250000.0)
    trial_ends_at = Column(DateTime, nullable=True)
    referred_by_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    robot_settings = relationship("RobotSettings", uselist=False, back_populates="user", cascade="all, delete-orphan")
    subscription = relationship("Subscription", uselist=False, back_populates="user", cascade="all, delete-orphan")
    referral = relationship("Referral", uselist=False, back_populates="user", cascade="all, delete-orphan")
    mt5_connection = relationship("MT5Connection", uselist=False, back_populates="user", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="user", cascade="all, delete-orphan")
    notification_prefs = relationship("NotificationPrefs", uselist=False, back_populates="user", cascade="all, delete-orphan")
    legal_acceptances = relationship("LegalAcceptance", back_populates="user", cascade="all, delete-orphan")


class RobotSettings(Base):
    __tablename__ = "robot_settings"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    active = Column(Boolean, default=True)
    risk_level = Column(Integer, default=1)  # 0=prudent 1=modere 2=agressif
    lot = Column(Float, default=0.01)
    max_positions = Column(Integer, default=1)
    pair = Column(String, default="XAUUSD")

    user = relationship("User", back_populates="robot_settings")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    plan = Column(String, default="classique")  # classique | premium
    price = Column(Float, default=10000.0)
    status = Column(String, default="trialing")  # trialing | active | cancelled
    payment_method = Column(String, default="orange")  # orange | wave
    renews_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="subscription")


class Referral(Base):
    __tablename__ = "referrals"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    code = Column(String, unique=True, nullable=False)
    referred_count = Column(Integer, default=0)
    credit_fcfa = Column(Float, default=0.0)  # crédit accumulé (1000 F par filleul qui s'abonne), déduit au paiement

    user = relationship("User", back_populates="referral")


class MT5Connection(Base):
    __tablename__ = "mt5_connections"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    connected = Column(Boolean, default=False)
    broker_server = Column(String, nullable=True)
    account_number = Column(String, nullable=True)
    trading_password_enc = Column(String, nullable=True)  # mot de passe MT5 (droits de trading), chiffré
    demo_mode = Column(Boolean, default=True)
    sync_token = Column(String, unique=True, nullable=True)  # code personnel pour /mt5/sync (EA ou bridge)
    bridge_status = Column(String, default="disconnected")  # disconnected | pending | running | safety_stop | error
    bridge_error = Column(String, nullable=True)
    # Change ce champ (date/heure) = signal au bridge de redemarrer le worker de ce compte,
    # meme si identifiants et reglages n'ont pas change (ex: sortir d'un arret de securite).
    force_restart_requested_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="mt5_connection")


class Trade(Base):
    __tablename__ = "trades"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    pair = Column(String, default="XAUUSD")
    amount = Column(Float, nullable=False)
    opened_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="closed")  # open | closed
    external_id = Column(String, nullable=True)  # ticket MT5 d'origine, pour éviter les doublons à la synchro

    user = relationship("User", back_populates="trades")


class Course(Base):
    __tablename__ = "courses"

    id = Column(String, primary_key=True, default=gen_id)
    title = Column(String, nullable=False)
    duration_min = Column(Integer, nullable=False)
    meta_label = Column(String, nullable=False)
    premium = Column(Boolean, default=False)
    body = Column(Text, nullable=True)
    order = Column(Integer, default=0)


class NotificationPrefs(Base):
    __tablename__ = "notification_prefs"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    trade_alerts = Column(Boolean, default=True)
    weekly_report = Column(Boolean, default=True)
    promos = Column(Boolean, default=False)

    user = relationship("User", back_populates="notification_prefs")


class AdminUser(Base):
    """Compte de l'equipe Lotabot pour l'espace admin (distinct des comptes clients)."""
    __tablename__ = "admin_users"

    id = Column(String, primary_key=True, default=gen_id)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    sessions = relationship("AdminSession", back_populates="admin", cascade="all, delete-orphan")


class AdminSession(Base):
    """Une session de connexion admin (jeton envoye au navigateur, seul son empreinte est stockee)."""
    __tablename__ = "admin_sessions"

    id = Column(String, primary_key=True, default=gen_id)
    admin_id = Column(String, ForeignKey("admin_users.id"), nullable=False)
    token_hash = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    admin = relationship("AdminUser", back_populates="sessions")


class AdminNote(Base):
    """Note interne sur un client, ecrite par un admin, jamais visible du client."""
    __tablename__ = "admin_notes"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    admin_id = Column(String, ForeignKey("admin_users.id"), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class LegalDocument(Base):
    """Un document (CGU, avertissement sur les risques, autorisation de trading MT5).
    Une nouvelle ligne = une nouvelle version publiée ; l'ancienne reste en base pour l'historique."""
    __tablename__ = "legal_documents"

    id = Column(String, primary_key=True, default=gen_id)
    slug = Column(String, nullable=False, index=True)  # cgu | risques | autorisation-mt5
    title = Column(String, nullable=False)
    version = Column(String, nullable=False)  # ex: "1.0"
    body = Column(Text, nullable=False)
    published_at = Column(DateTime, default=datetime.utcnow)


class LegalAcceptance(Base):
    """Une acceptation d'un client pour UNE version précise d'UN document : la preuve."""
    __tablename__ = "legal_acceptances"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    slug = Column(String, nullable=False)
    version = Column(String, nullable=False)
    accepted_at = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String, nullable=True)

    user = relationship("User", back_populates="legal_acceptances")
