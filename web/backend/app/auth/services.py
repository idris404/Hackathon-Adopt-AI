import uuid
from typing import Protocol

from app.auth.exceptions import InvalidCredentialsError
from app.users.entity import User
from app.users.services import UserManager


class SessionIssuer(Protocol):
    """Ce dont `AuthService` a besoin : ouvrir une session pour un utilisateur."""

    async def write_token(self, user: User) -> str: ...


class UserSessionRevoker(Protocol):
    """Ce dont `SessionService` a besoin : supprimer toutes les sessions d'un utilisateur."""

    async def delete_all_for_user(self, user_id: uuid.UUID) -> None: ...


class AuthService:
    """Connexion : vérifie les identifiants et ouvre une session.

    L'envoi du jeton au client (cookie) est du ressort du router.
    """

    def __init__(self, users: UserManager, sessions: SessionIssuer) -> None:
        self._users = users
        self._sessions = sessions

    async def login(self, email: str, password: str) -> str:
        """Retourne le jeton de la nouvelle session.

        Lève `InvalidCredentialsError` pour un email inconnu, un mauvais mot de passe ou un compte
        désactivé, sans distinguer ces cas.
        """
        user = await self._users.authenticate_with_email(email, password)
        if user is None or not user.is_active:
            raise InvalidCredentialsError()
        return await self._sessions.write_token(user)


class SessionService:
    """Gestion des sessions ouvertes d'un utilisateur.

    La déconnexion de l'appareil courant passe par `POST /logout` (voir `router.py`).
    """

    def __init__(self, sessions: UserSessionRevoker) -> None:
        self._sessions = sessions

    async def logout_all(self, user_id: uuid.UUID) -> None:
        """Révoque toutes les sessions de l'utilisateur, sur tous ses appareils."""
        await self._sessions.delete_all_for_user(user_id)
