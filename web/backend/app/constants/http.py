from typing import Final

DEFAULT_FRONTEND_URL: Final = "http://localhost:5173"

# Toutes les routes métier sont servies sous /api/<version>. Une nouvelle version
# majeure ajoute sa constante et son routeur dans main.py, sans toucher à la précédente.
API_PREFIX: Final = "/api"
API_VERSION_V1: Final = "v1"
API_V1_PREFIX: Final = f"{API_PREFIX}/{API_VERSION_V1}"

CORS_ALLOWED_METHODS: Final = ("GET", "POST", "PATCH", "DELETE")
CORS_ALLOWED_HEADERS: Final = ("Content-Type",)
