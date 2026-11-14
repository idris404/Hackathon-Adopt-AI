from app.core.exceptions import AppError


class PatientAlreadySignedError(AppError):
    """Ce patient a déjà une signature."""
