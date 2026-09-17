# Lotabot – Backend

API FastAPI pour l'application **Lotabot** (robot de trading auto sur XAUUSD, ex "TradeBot Sénégal").

## Stack
- FastAPI + SQLAlchemy
- PostgreSQL en production (Neon/Render), SQLite automatique en local si `DATABASE_URL` n'est pas défini
- Authentification JWT (bcrypt pour les mots de passe)

## Lancer en local

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # puis éditer si besoin
uvicorn app.main:app --reload --port 4000
```

L'API est alors disponible sur `http://localhost:4000/api`, avec la doc interactive sur `http://localhost:4000/docs`.

Un compte de démonstration est créé automatiquement au premier démarrage :
- Téléphone : `771715238`
- Mot de passe : `demo1234`

## Variables d'environnement (`.env`)

| Variable | Description |
|---|---|
| `DATABASE_URL` | URL Postgres (Neon, Render…). Si absent, SQLite local `lotabot.db`. |
| `JWT_SECRET` | Clé secrète de signature des tokens JWT — à changer en production. |
| `JWT_EXPIRE_MINUTES` | Durée de validité du token (par défaut 30 jours). |
| `FRONTEND_ORIGIN` | Origine autorisée en CORS (URL du frontend déployé). |

## Déploiement (comme Lotafinance)

- Backend → **Render** (Web Service Python), en pointant `DATABASE_URL` vers ta base Neon.
- Frontend → **Vercel**, avec `NEXT_PUBLIC_API_BASE` pointant vers l'URL Render du backend.

## Endpoints principaux

- `POST /api/auth/register`, `POST /api/auth/login`
- `GET /api/trades/dashboard`, `GET /api/trades/history`
- `GET/PUT /api/robot`, `PUT /api/robot/toggle`
- `GET /api/courses`
- `GET/PUT /api/profile`, `GET/PUT /api/profile/notifications`
- `GET /api/subscription`, `PUT /api/subscription/payment-method`, `POST /api/subscription/change-plan`, `POST /api/subscription/cancel`
- `GET /api/referral`
- `GET /api/mt5`, `POST /api/mt5/connect`, `POST /api/mt5/disconnect`

## Connexion MT5 : état actuel

Pour l'instant, `POST /mt5/connect` enregistre les identifiants du compte (le mot de passe investisseur n'est jamais stocké en clair) et marque le compte comme connecté en **mode démo**. La copie réelle des trades depuis MetaTrader 5 nécessite un pont côté serveur (EA MQL5 `EA_XAUUSD_SR_DoubleTouch` ou un service Python type MetaTrader5 package tournant sur un VPS Windows) qui écrira les trades réels dans la table `trades`. C'est la prochaine étape logique une fois l'app validée.
