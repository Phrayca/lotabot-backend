import os

# Taux de change utilisé pour convertir les montants du compte MT5 (en USD)
# vers l'affichage FCFA de l'application. Modifiable via la variable
# d'environnement EXCHANGE_RATE_USD_FCFA sur Render, sans avoir à retoucher au code.
EXCHANGE_RATE_USD_FCFA = float(os.getenv("EXCHANGE_RATE_USD_FCFA", "610"))
