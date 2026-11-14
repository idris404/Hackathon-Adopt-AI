from app.core.exceptions import AppError


class PatientNotFoundError(AppError):
    """Aucun patient ne porte cet identifiant."""


class PatientSeedError(AppError):
    """Le CSV à ingérer est inutilisable. Le message ne contient jamais de valeur du fichier."""
