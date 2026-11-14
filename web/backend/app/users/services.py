import uuid

from fastapi_users import BaseUserManager, UUIDIDMixin

from app.users.entity import User


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    """Logique métier des utilisateurs : inscription, authentification, mise à jour.

    Les dépendances (adaptateur de base de données, hasher) arrivent par le constructeur.
    Le mot de passe est validé par les schémas (`UserCreate`, `UserUpdate`).

    La réinitialisation de mot de passe et la vérification d'email ne sont pas activées :
    elles demandent un fournisseur d'envoi d'email et deux secrets
    (`reset_password_token_secret`, `verification_token_secret`) à ajouter ici.
    """
