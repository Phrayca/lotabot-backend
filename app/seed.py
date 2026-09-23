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
        "duration_min": 8,
        "meta_label": "Prise en main",
        "premium": False,
        "order": 1,
        "body": (
            "Lotabot fait trader un robot automatique sur l'or (XAUUSD) à ta place, chez le courtier "
            "de ton choix. Concrètement, voici comment ça marche : tu connectes ton compte MetaTrader 5 "
            "(MT5) dans l'application, avec ton numéro de compte, le nom du serveur de ton courtier et "
            "ton mot de passe de trading. Ce mot de passe est chiffré dès qu'il arrive sur nos serveurs, "
            "et personne, pas même l'équipe Lotabot, ne peut le lire en clair.\n\n"
            "Une fois ton compte connecté, un serveur dédié à Lotabot se connecte à ton compte MT5 et "
            "fait tourner le robot pour toi, 24h/24 pendant les heures où le marché de l'or est actif. "
            "Tu n'as rien à installer sur ton téléphone ou ton ordinateur : tout tourne côté serveur. Le "
            "robot surveille les prix, cherche des occasions d'entrée selon sa stratégie, ouvre des "
            "positions, place systématiquement un stop loss (un ordre de sécurité qui limite la perte si "
            "le marché part dans le mauvais sens), et gère la sortie au fil du temps.\n\n"
            "Ce que tu dois faire, toi : d'abord, compléter ton profil (nom, ville, date de naissance) — "
            "c'est nécessaire pour que ton compte soit valide. Ensuite, connecter ton compte MT5. Enfin, "
            "choisir un niveau de risque qui te convient dans l'onglet Robot : Prudent, Modéré ou "
            "Agressif. Tu peux changer ce réglage à tout moment, autant de fois que tu veux.\n\n"
            "Après la connexion, ne t'inquiète pas si rien ne se passe tout de suite : le robot attend "
            "une vraie occasion d'entrée selon sa stratégie, et ne force jamais un trade juste pour "
            "\"faire quelque chose\". Certains jours, il ne prend aucune position. D'autres jours, il en "
            "prend plusieurs. C'est normal et voulu : le robot est construit pour attendre les bonnes "
            "conditions plutôt que trader en permanence.\n\n"
            "Tu peux suivre ton solde et tes résultats sur l'écran Accueil, consulter chaque trade en "
            "détail dans Historique, ajuster les réglages du robot dans l'onglet Robot, et nous écrire "
            "à tout moment depuis Profil puis Support si tu as une question ou un problème. On te "
            "répond dès qu'on peut, en général le jour même.\n\n"
            "Une dernière chose importante avant de démarrer : lis bien l'avertissement sur les risques "
            "et les conditions générales, qu'on te fait accepter avant la connexion de ton compte MT5. "
            "Le trading comporte un vrai risque de perte, même avec un robot bien construit. On revient "
            "sur ce point en détail dans les prochaines leçons."
        ),
    },
    {
        "title": "C'est quoi le XAUUSD ?",
        "duration_min": 9,
        "meta_label": "Fondamentaux",
        "premium": False,
        "order": 2,
        "body": (
            "XAUUSD, c'est simplement le prix de l'or (Gold) exprimé en dollars américains. \"XAU\" est "
            "le code international de l'or (comme \"EUR\" pour l'euro ou \"USD\" pour le dollar), et "
            "\"USD\" celui du dollar américain. Quand tu vois \"XAUUSD = 4 344,66\", ça veut dire qu'une "
            "once d'or (environ 31,1 grammes) vaut 4 344,66 dollars à cet instant précis.\n\n"
            "Pourquoi l'or, et pas une autre paire ? L'or est l'un des marchés les plus tradés au monde. "
            "Il bouge beaucoup au cours d'une journée (on dit qu'il est \"volatil\"), ce qui crée des "
            "occasions régulières pour une stratégie automatique. Il est aussi très liquide : il y a "
            "toujours quelqu'un pour acheter ou vendre, donc les ordres passent facilement, sans grand "
            "écart entre le prix demandé et le prix obtenu.\n\n"
            "Ce qui fait bouger le prix de l'or : les décisions des banques centrales (en particulier la "
            "Réserve fédérale américaine), l'inflation, la force ou la faiblesse du dollar, les tensions "
            "géopolitiques et les crises économiques. En période d'incertitude, beaucoup d'investisseurs "
            "achètent de l'or car il est perçu comme une valeur refuge — ce qui fait souvent monter son "
            "prix quand les marchés boursiers sont nerveux.\n\n"
            "Deux mots techniques que tu croiseras : le \"point\" (ou \"pip\"), qui est la plus petite "
            "variation de prix mesurable sur XAUUSD, et le \"spread\", qui est le petit écart entre le "
            "prix d'achat et le prix de vente à un instant donné — c'est en quelque sorte la commission "
            "implicite du courtier. Le robot Lotabot vérifie toujours que ce spread reste raisonnable "
            "avant d'entrer en position : si le marché est trop instable, il attend plutôt que de trader "
            "dans de mauvaises conditions.\n\n"
            "L'or se trade quasiment en continu du dimanche soir au vendredi soir (heure de Paris), avec "
            "des variations d'activité selon les sessions : la session de Londres, puis celle de New "
            "York, sont généralement les plus actives. Le robot Lotabot ne trade que pendant certaines "
            "heures définies à l'avance, pour éviter les périodes creuses où le marché est peu liquide "
            "et où les mouvements de prix sont moins fiables."
        ),
    },
    {
        "title": "Comprendre le risque, en 5 minutes",
        "duration_min": 8,
        "meta_label": "Fondamentaux",
        "premium": False,
        "order": 3,
        "body": (
            "Trader, ce n'est pas deviner si le prix va monter ou descendre — c'est gérer ce que tu "
            "risques de perdre à chaque tentative. C'est la différence entre un joueur de casino et un "
            "professionnel : le professionnel sait qu'il va perdre certains coups, et organise son "
            "capital pour que ça n'ait jamais d'importance grave.\n\n"
            "Voici comment le robot Lotabot applique ce principe, concrètement. Sur chaque position, il "
            "calcule une petite part de ton capital à risquer — en général entre 0,5 % et 2 % selon le "
            "niveau choisi. Si ton compte fait 1 000 $ et que le robot risque 1 % par trade, ça veut "
            "dire qu'il accepte de perdre au maximum 10 $ sur ce trade précis, jamais plus. Cette limite "
            "est fixée à l'avance par un stop loss automatique, posé au moment même où la position "
            "s'ouvre.\n\n"
            "Pourquoi une si petite part ? Parce que les mathématiques du risque sont impitoyables : si "
            "tu perds 50 % de ton capital, il te faut ensuite un gain de 100 % rien que pour revenir à "
            "ton point de départ. Alors que si tu perds seulement 10 %, un gain de 11 % suffit à te "
            "refaire. Plus une perte est grosse, plus il est difficile — voire impossible — de s'en "
            "remettre. Limiter chaque perte individuelle, c'est ce qui permet de rester dans le jeu sur "
            "la durée.\n\n"
            "Une autre idée essentielle : même la meilleure stratégie du monde perd une partie de ses "
            "trades. Ce n'est pas un défaut, c'est la nature du trading. Une stratégie peut très bien "
            "gagner 4 trades sur 10, et rester rentable sur la durée — à condition que les 4 trades "
            "gagnants rapportent en moyenne plus que ce que coûtent les 6 perdants. C'est pour ça que le "
            "robot vise un ratio gain/risque d'au moins 2 pour 1 : quand il gagne, il vise à gagner deux "
            "fois plus que ce qu'il risque de perdre.\n\n"
            "Ce que ça veut dire pour toi, concrètement : ne panique pas devant une perte isolée, même "
            "deux ou trois d'affilée. Ce qui compte, c'est le résultat cumulé sur plusieurs semaines, "
            "pas un trade pris isolément. Et surtout : ne place jamais sur ton compte de trading une "
            "somme dont la perte compromettrait ta situation financière. C'est la règle numéro un, avant "
            "toute stratégie, avant tout robot."
        ),
    },
    {
        "title": "Choisir son niveau de risque",
        "duration_min": 9,
        "meta_label": "Prise en main",
        "premium": False,
        "order": 4,
        "body": (
            "Dans l'onglet Robot, tu peux régler le niveau de risque du robot : Prudent, Modéré ou "
            "Agressif. Ce choix change trois choses en même temps : le pourcentage de ton capital "
            "risqué à chaque trade, la limite de perte journalière (le seuil à partir duquel le robot "
            "s'arrête pour le reste de la journée), et le seuil de baisse maximale avant l'arrêt de "
            "sécurité complet (le \"coupe-circuit\", qui désactive le robot si ton solde chute trop par "
            "rapport à son plus haut).\n\n"
            "Prudent : environ 0,5 % du capital risqué par trade, arrêt de la journée si tu perds 2 %, "
            "coupe-circuit à 10 % de baisse. C'est le réglage le plus doux : les gains sont plus lents, "
            "mais les variations de ton solde aussi. Un bon choix si tu débutes ou si tu préfères dormir "
            "tranquille.\n\n"
            "Modéré : environ 1 % par trade, arrêt à 3 % dans la journée, coupe-circuit à 15 %. C'est le "
            "réglage par défaut, pensé comme un compromis raisonnable pour la plupart des gens.\n\n"
            "Agressif : environ 2 % par trade, arrêt à 5 % dans la journée, coupe-circuit à 25 %. Les "
            "gains peuvent être plus rapides, mais les pertes aussi, et les variations de ton solde "
            "seront nettement plus visibles au quotidien. Ne choisis ce réglage que si tu es vraiment à "
            "l'aise avec l'idée de voir ton capital bouger davantage, à la hausse comme à la baisse.\n\n"
            "Un point important si ton capital est proche du minimum accepté (100 $) : le lot minimum "
            "imposé par les courtiers peut représenter, sur une seule position, un risque plus élevé que "
            "celui visé par ton niveau choisi — parfois jusqu'à 9 ou 10 % du solde sur un seul trade, "
            "même en Prudent. C'est une contrainte technique liée à la taille de ton compte, pas un bug. "
            "Nous recommandons un capital d'au moins 600 $ pour que la gestion du risque fonctionne "
            "exactement comme décrit ci-dessus, à tous les niveaux.\n\n"
            "Tu peux changer de niveau à tout moment, aussi souvent que tu veux, directement depuis "
            "l'onglet Robot. Le nouveau réglage est pris en compte par le serveur en quelques dizaines "
            "de secondes, sans avoir besoin de déconnecter ton compte MT5."
        ),
    },
    {
        "title": "Lire ton historique de trades",
        "duration_min": 8,
        "meta_label": "Prise en main",
        "premium": False,
        "order": 5,
        "body": (
            "Dans l'onglet Historique, chaque ligne représente un trade que le robot a passé pour toi "
            "sur ton compte. Les trades sont regroupés par jour (\"Aujourd'hui\", \"Hier\", puis par "
            "date), du plus récent au plus ancien. Pour chaque trade, tu vois la paire tradée (XAUUSD), "
            "l'heure d'ouverture, et le résultat en dollars et en francs CFA — en vert s'il est gagnant, "
            "en rouge s'il est perdant.\n\n"
            "Sur l'écran Accueil, trois chiffres résument ta situation : le solde estimé de ton compte, "
            "le gain ou la perte du jour, et la variation de ton solde sur les 7 derniers jours en "
            "pourcentage. Le nombre de \"Trades ouverts\" indique les positions que le robot a "
            "actuellement en cours, pas encore clôturées — leur résultat peut encore bouger tant qu'elles "
            "restent ouvertes.\n\n"
            "Un point important : seuls les trades passés par le robot lui-même apparaissent dans ton "
            "historique et comptent dans tes statistiques. Si tu passes un ordre manuellement dans MT5, "
            "il n'apparaît pas ici — l'application ne suit que ce que le robot fait pour toi.\n\n"
            "Ne panique pas devant une ligne rouge isolée : c'est normal et attendu, même une stratégie "
            "solide perd une partie de ses trades, comme expliqué dans la leçon sur le risque. Une petite "
            "série de pertes d'affilée peut arriver, surtout sur des marchés difficiles à lire ; c'est "
            "justement pour ça que la limite de perte journalière existe — elle arrête le robot avant que "
            "ça aille trop loin, et il reprend automatiquement le lendemain.\n\n"
            "Ce qui compte vraiment, c'est le résultat cumulé sur la semaine ou le mois, pas un trade pris "
            "isolément. Si tu observes une série de pertes qui te semble anormalement longue, ou si un "
            "chiffre te paraît incohérent, n'hésite pas à nous écrire depuis Profil puis Support : on "
            "regarde ton compte avec toi et on t'explique ce qui s'est passé."
        ),
    },
    {
        "title": "Gestion du risque avancée",
        "duration_min": 15,
        "meta_label": "Stratégie",
        "premium": True,
        "order": 6,
        "body": (
            "Au-delà du stop loss posé sur chaque position, le robot Lotabot utilise trois garde-fous "
            "supplémentaires pour protéger ton capital, du plus local au plus global.\n\n"
            "Premier niveau : la limite de perte journalière. Si tes pertes cumulées sur une journée "
            "atteignent le seuil de ton niveau de risque (2 % en Prudent, 3 % en Modéré, 5 % en "
            "Agressif), le robot arrête de prendre de nouvelles positions jusqu'au lendemain. Les "
            "positions déjà ouvertes continuent d'être gérées normalement (stop loss, sécurisation des "
            "gains), mais aucune nouvelle entrée n'est tentée ce jour-là. C'est une pause forcée qui "
            "évite de s'acharner sur une mauvaise journée.\n\n"
            "Deuxième niveau, optionnel : l'objectif de gain journalier. S'il est activé, le robot peut "
            "aussi s'arrêter pour la journée une fois un certain niveau de gain atteint, pour sécuriser "
            "ce qui a été gagné plutôt que de tout remettre en jeu le même jour.\n\n"
            "Troisième niveau, le plus important : le coupe-circuit sur le drawdown (la baisse depuis le "
            "plus haut historique de ton compte). Si ton solde chute de 10 % (Prudent), 15 % (Modéré) "
            "ou 25 % (Agressif) par rapport à son sommet, le robot s'arrête complètement sur ce compte, "
            "pas seulement pour la journée. C'est un arrêt de sécurité, visible dans l'application avec "
            "un message clair, et il reste actif jusqu'à ce que la situation soit revue manuellement.\n\n"
            "Concrètement, sur chaque position individuelle, le robot pose aussi deux mécanismes "
            "automatiques : le passage au point mort (dès que le trade est suffisamment gagnant, le "
            "stop loss remonte au prix d'entrée, pour qu'un trade gagnant ne puisse plus finir en "
            "perte), puis un stop suiveur (le stop loss continue de suivre le prix à distance, pour "
            "protéger une partie des gains si le marché se retourne).\n\n"
            "Ensemble, ces règles forment plusieurs filets de sécurité imbriqués : par trade, par jour, "
            "et sur l'ensemble du compte. Aucun de ces mécanismes ne garantit l'absence de perte — le "
            "trading comporte toujours un risque réel, rappelé dans l'avertissement sur les risques — "
            "mais ils sont pensés pour qu'aucun mauvais scénario de marché ne puisse, à lui seul, mettre "
            "ton capital en danger sans que le robot ne s'arrête avant."
        ),
    },
]


def make_referral_code(full_name: str) -> str:
    base = "".join(ch for ch in full_name.upper() if ch.isalpha())[:6] or "LOTA"
    suffix = "".join(random.choices(string.digits, k=2))
    return base + suffix


def seed_courses(db: Session):
    """Insere les formations manquantes ET met a jour celles qui existent deja, pour que
    l'ordre, le texte et les autres champs restent toujours synchronises avec DEFAULT_COURSES
    ci-dessus. Cette fonction tourne a chaque demarrage du serveur (voir main.py), donc un
    simple redeploiement suffit a propager un changement fait ici."""
    existing = {c.title: c for c in db.query(models.Course).all()}
    for c in DEFAULT_COURSES:
        row = existing.get(c["title"])
        if row is None:
            db.add(models.Course(**c))
        else:
            row.duration_min = c["duration_min"]
            row.meta_label = c["meta_label"]
            row.premium = c["premium"]
            row.order = c["order"]
            row.body = c["body"]
    db.commit()


def bootstrap_user(db: Session, user: models.User, plan: str = "classique"):
    """Crée toutes les entités liées à un nouvel utilisateur (réglages robot,
    abonnement en essai gratuit, code de parrainage, préférences de notifications, MT5)."""
    price = 15000.0 if plan == "premium" else 10000.0
    trial_end = datetime.utcnow() + timedelta(days=TRIAL_DAYS)

    user.trial_ends_at = trial_end

    db.add(models.RobotSettings(user_id=user.id, lot=0.01, max_positions=1))
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
