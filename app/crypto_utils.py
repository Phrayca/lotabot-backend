import os
from cryptography.fernet import Fernet, InvalidToken

# Clé de chiffrement du mot de passe de trading MT5 des clients. À définir sur
# Render (variable ENCRYPTION_KEY). Générée une seule fois avec :
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
_ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
_fernet = Fernet(_ENCRYPTION_KEY.encode()) if _ENCRYPTION_KEY else None


def encrypt_secret(plain_text: str) -> str:
    if not _fernet:
        raise RuntimeError("ENCRYPTION_KEY n'est pas configurée sur le serveur")
    return _fernet.encrypt(plain_text.encode()).decode()


def decrypt_secret(cipher_text: str) -> str:
    if not _fernet:
        raise RuntimeError("ENCRYPTION_KEY n'est pas configurée sur le serveur")
    try:
        return _fernet.decrypt(cipher_text.encode()).decode()
    except InvalidToken:
        raise RuntimeError("Impossible de déchiffrer ce mot de passe (clé changée ?)")
