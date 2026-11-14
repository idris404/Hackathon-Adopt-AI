from typing import Final

# Mots de passe
PASSWORD_MIN_LENGTH: Final = 12
PASSWORD_MAX_LENGTH: Final = 256

# Hachage Argon2id : 64 MiB de mémoire, 3 itérations, 4 voies de parallélisme
ARGON2_TIME_COST: Final = 3
ARGON2_MEMORY_COST_KIB: Final = 64 * 1024
ARGON2_PARALLELISM: Final = 4

# Session : jeton opaque stocké en base, transporté par un cookie HttpOnly
SESSION_LIFETIME_SECONDS: Final = 7 * 24 * 60 * 60
SESSION_COOKIE_NAME: Final = "adopt_ai_session"
SESSION_COOKIE_PATH: Final = "/"
SESSION_COOKIE_HTTPONLY: Final = True
SESSION_COOKIE_SAMESITE: Final = "lax"

# Routes
AUTH_BACKEND_NAME: Final = "cookie"
AUTH_ROUTER_PREFIX: Final = "/auth"
AUTH_ROUTER_TAG: Final = "auth"
