class AppError(Exception):
    """Base des erreurs métier. Leur conversion en code HTTP est faite dans `main.py`."""


class SeedError(AppError):
    """Le CSV à ingérer est inutilisable. Le message ne contient jamais de valeur du fichier."""
