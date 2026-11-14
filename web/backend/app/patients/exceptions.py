from app.core.exceptions import AppError


class PatientNotFoundError(AppError):
    """Aucun patient ne porte cet identifiant."""
