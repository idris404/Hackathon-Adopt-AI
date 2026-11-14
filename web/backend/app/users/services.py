import uuid

from fastapi.security import OAuth2PasswordRequestForm
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

    async def authenticate_with_email(self, email: str, password: str) -> User | None:
        """Retourne l'utilisateur si l'email et le mot de passe sont corrects, sinon `None`.

        Mêmes garanties que `authenticate` de FastAPI Users : un hachage factice est exécuté quand
        l'email est inconnu (pas de différence de temps de réponse), et le hash est recalculé si ses
        paramètres ont changé. `authenticate` attend un formulaire OAuth2, d'où l'adaptation ici.
        """
        credentials = OAuth2PasswordRequestForm(username=email, password=password)
        return await self.authenticate(credentials)
