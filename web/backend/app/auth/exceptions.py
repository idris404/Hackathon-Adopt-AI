from app.core.exceptions import AppError


class InvalidCredentialsError(AppError):
    """Email inconnu, mauvais mot de passe ou compte désactivé : volontairement indistinguables."""
