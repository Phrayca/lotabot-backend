"""
Lotabot Backend - Documents legaux
------------------------------------
Trois documents que chaque client doit accepter avant de connecter un compte MT5 :
conditions generales, avertissement sur les risques, autorisation de trading.

Chaque acceptation (LegalAcceptance) est une preuve : client, document, version exacte,
date et adresse IP. Publier une nouvelle version d'un document (via /api/legal/seed avec
un contenu different) redemande l'acceptation a tous les clients, sans toucher a celles
deja enregistrees (l'historique est conserve).

IMPORTANT : les textes ci-dessous sont un brouillon de depart, pas un document juridique
valide. Ils contiennent des espaces reserves ([RAISON SOCIALE], [JURIDICTION]) et doivent
etre relus par un juriste avant utilisation reelle avec des clients.
"""
import os
import secrets as _secrets
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..auth import get_current_user

router = APIRouter(prefix="/api/legal", tags=["legal"])

REQUIRED_SLUGS = ["cgu", "risques", "autorisation-mt5"]

# Brouillon de depart pour /api/legal/seed (voir l'avertissement en haut du fichier).
_DRAFT_DOCUMENTS = {
    "cgu": {"title": "Conditions générales d'utilisation", "version": "1.0", "body": """Conditions générales d'utilisation

1. Présentation du service
Lotabot est une application qui permet de connecter un compte MetaTrader 5 (MT5) chez un courtier de ton choix et de faire exécuter automatiquement, par un robot de trading, des ordres sur cette paire selon une stratégie déterminée à l'avance. [RAISON SOCIALE], ci-après « Lotabot » ou « nous », édite et exploite ce service.

2. Compte et abonnement
L'accès au robot suppose un compte utilisateur et un abonnement actif (formule Classique ou Premium), sauf pendant la période d'essai gratuite indiquée dans l'application. Les tarifs et modalités de paiement sont ceux affichés dans l'application au moment de la souscription et peuvent évoluer, moyennant information préalable.

3. Fonctionnement du robot
Le robot analyse le marché et passe des ordres pour ton compte selon les paramètres de risque que tu choisis (niveau Prudent, Modéré ou Agressif) dans l'application. Tu peux mettre le robot en pause à tout moment ; l'arrêt peut prendre quelques minutes, le temps que la mise à jour soit prise en compte par notre serveur.

4. Ce que Lotabot ne fait pas
Lotabot ne garantit aucun résultat ni aucun gain, et n'est ni un conseiller en investissement, ni une société de gestion de portefeuille agréée. Voir le document « Avertissement sur les risques » pour le détail. Lotabot ne peut ni retirer ni transférer les fonds de ton compte de trading : l'accès donné au robot ne permet que le passage d'ordres.

5. Résiliation
Tu peux annuler ton abonnement et déconnecter ton compte MT5 à tout moment depuis l'application. La déconnexion arrête le robot sur ce compte.

6. Modifications
Ces conditions peuvent être mises à jour ; toute nouvelle version te sera présentée pour acceptation avant de continuer à utiliser le service.

7. Droit applicable
[JURIDICTION]."""},
    "risques": {"title": "Avertissement sur les risques", "version": "1.0", "body": """Avertissement sur les risques

1. Le trading sur le marché des changes et des métaux (dont l'or, XAUUSD) comporte un risque réel et significatif de perte en capital, y compris la perte totale du montant déposé. Les performances passées, y compris celles du robot, ne préjugent jamais des performances futures.

2. Le robot Lotabot vise à limiter ce risque par des règles automatiques : un stop loss est toujours placé sur chaque position, une limite de perte quotidienne interrompt le trading pour la journée si elle est atteinte, et un coupe-circuit arrête le robot si la baisse du compte depuis son plus haut dépasse un seuil fixé selon le niveau de risque choisi. Ces règles limitent le risque, elles ne l'éliminent pas.

3. Sur les petits comptes (capital proche du minimum accepté de 100 $), le lot minimum imposé par les courtiers peut représenter, sur une seule position, un risque nettement supérieur à celui visé pour les autres comptes — jusqu'à environ 9 à 10 % du solde par trade au lieu de 1 à 2 %. Une seule perte peut alors déclencher la limite quotidienne, et deux pertes peuvent approcher le coupe-circuit. Nous recommandons un capital d'au moins 600 $ pour que la gestion du risque fonctionne comme prévu ; en dessous, tu acceptes un risque par trade plus élevé.

4. Le robot trade sur un compte qui t'appartient, chez le courtier de ton choix. Tu restes seul responsable des dépôts, des retraits et du choix de ton courtier. Lotabot n'est ni dépositaire, ni intermédiaire financier agréé.

5. En activant le robot, tu confirmes avoir compris que tu peux perdre une partie ou la totalité des fonds placés sur le compte connecté, et que tu ne places sur ce compte que des sommes dont la perte ne compromettrait pas ta situation financière."""},
    "autorisation-mt5": {"title": "Autorisation de trading sur ton compte MT5", "version": "1.0", "body": """Autorisation de trading sur ton compte MT5

1. En connectant un compte MetaTrader 5 dans l'application, tu autorises Lotabot à utiliser le mot de passe principal (trading) de ce compte pour s'y connecter et y passer, modifier ou clôturer des ordres, uniquement dans le but de faire fonctionner le robot selon les réglages que tu as choisis.

2. Ce mot de passe est chiffré dès son enregistrement et n'est déchiffré que par le serveur technique qui exécute le robot, au moment de la connexion. Il n'est jamais affiché en clair dans l'application, y compris pour l'équipe Lotabot.

3. Cette autorisation ne permet à aucun moment un retrait ou un virement de fonds : l'accès « trading » d'un compte MT5 ne donne techniquement pas ce pouvoir, quel que soit le courtier.

4. Tu peux révoquer cette autorisation à tout moment en déconnectant ton compte depuis l'application (Profil, Compte MT5, Déconnecter ce compte). Le robot s'arrête alors sur ce compte et le mot de passe enregistré est supprimé de nos serveurs.

5. Si tu changes le mot de passe de ton compte directement dans MetaTrader 5, la connexion avec Lotabot sera interrompue jusqu'à ce que tu la mettes à jour dans l'application."""},
}


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "inconnue"


def _latest_documents(db: Session) -> dict:
    """Pour chaque document requis, sa version la plus recente (ou rien s'il n'a jamais
    ete publie, ce qui bloque volontairement la connexion MT5 tant que /api/legal/seed
    n'a pas ete appele au moins une fois)."""
    docs = {}
    for slug in REQUIRED_SLUGS:
        doc = (
            db.query(models.LegalDocument)
            .filter(models.LegalDocument.slug == slug)
            .order_by(models.LegalDocument.published_at.desc())
            .first()
        )
        if doc:
            docs[slug] = doc
    return docs


def legal_gate_ok(user: models.User, db: Session) -> bool:
    """Utilise par la connexion MT5 : refuse tant que les 3 documents ne sont pas TOUS publies
    (echec ferme si /api/legal/seed n'a jamais ete appele : mieux vaut bloquer par prudence que
    laisser connecter un compte sans aucune acceptation possible a montrer au client)."""
    docs = _latest_documents(db)
    if len(docs) < len(REQUIRED_SLUGS):
        return False
    return len(pending_documents(user, db)) == 0


def pending_documents(user: models.User, db: Session) -> list:
    """Documents dont la derniere version n'a pas encore ete acceptee par ce client."""
    docs = _latest_documents(db)
    accepted = {
        (a.slug, a.version)
        for a in db.query(models.LegalAcceptance).filter(models.LegalAcceptance.user_id == user.id).all()
    }
    return [doc for slug, doc in docs.items() if (slug, doc.version) not in accepted]


@router.get("/documents", response_model=list[schemas.LegalDocumentOut])
def list_documents(db: Session = Depends(get_db)):
    docs = _latest_documents(db)
    return [
        schemas.LegalDocumentOut(slug=d.slug, title=d.title, version=d.version, body=d.body)
        for d in docs.values()
    ]


@router.get("/status", response_model=schemas.LegalStatusOut)
def status(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    pending = pending_documents(user, db)
    return schemas.LegalStatusOut(
        pending=[schemas.LegalDocumentOut(slug=d.slug, title=d.title, version=d.version, body=d.body) for d in pending],
        allAccepted=len(pending) == 0,
    )


@router.post("/accept", response_model=schemas.LegalAcceptOut)
def accept(
    payload: schemas.LegalAcceptIn,
    request: Request,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    docs = _latest_documents(db)
    ip = _client_ip(request)
    accepted = []
    for slug in payload.slugs:
        doc = docs.get(slug)
        if not doc:
            continue
        already = (
            db.query(models.LegalAcceptance)
            .filter(
                models.LegalAcceptance.user_id == user.id,
                models.LegalAcceptance.slug == slug,
                models.LegalAcceptance.version == doc.version,
            )
            .first()
        )
        if not already:
            db.add(models.LegalAcceptance(user_id=user.id, slug=slug, version=doc.version, ip_address=ip))
        accepted.append(slug)
    db.commit()
    return schemas.LegalAcceptOut(ok=True, accepted=accepted)


@router.post("/seed", include_in_schema=False)
def seed_legal_documents(
    x_internal_secret: str = Header(default=None, alias="X-Internal-Secret"),
    db: Session = Depends(get_db),
):
    """A appeler UNE FOIS (puis a nouveau seulement pour publier une nouvelle version)
    avec le meme secret que le bridge (BRIDGE_INTERNAL_SECRET), jamais depuis l'app."""
    expected = os.getenv("BRIDGE_INTERNAL_SECRET")
    if not expected or not x_internal_secret or not _secrets.compare_digest(x_internal_secret.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Cle interne invalide")

    created = []
    for slug, doc in _DRAFT_DOCUMENTS.items():
        existing = (
            db.query(models.LegalDocument)
            .filter(models.LegalDocument.slug == slug, models.LegalDocument.version == doc["version"])
            .first()
        )
        if existing:
            continue
        db.add(models.LegalDocument(slug=slug, title=doc["title"], version=doc["version"], body=doc["body"]))
        created.append(slug)
    db.commit()
    return {"ok": True, "created": created}
