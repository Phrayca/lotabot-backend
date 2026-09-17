import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .database import Base, engine, SessionLocal
from . import seed
from .routers import (
    auth_router,
    trades_router,
    robot_router,
    courses_router,
    profile_router,
    subscription_router,
    referral_router,
    mt5_router,
)

load_dotenv()

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Lotabot API", version="1.0.0")

origins = [os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != [""] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(trades_router.router)
app.include_router(robot_router.router)
app.include_router(courses_router.router)
app.include_router(profile_router.router)
app.include_router(subscription_router.router)
app.include_router(referral_router.router)
app.include_router(mt5_router.router)


@app.on_event("startup")
def on_startup():
    db = SessionLocal()
    try:
        seed.seed_courses(db)
        seed.seed_demo_account(db)
    finally:
        db.close()


@app.get("/")
def root():
    return {"status": "ok", "service": "Lotabot API"}


@app.get("/api/health")
def health():
    return {"status": "ok"}
