from enum import StrEnum
from typing import Final

DEFAULT_PAGE: Final = 1
DEFAULT_PAGE_SIZE: Final = 20
MAX_PAGE_SIZE: Final = 100

# Recherche plein texte : longueur bornée côté entrée, caractère d'échappement des jokers LIKE.
SEARCH_MAX_LENGTH: Final = 100
LIKE_ESCAPE_CHARACTER: Final = "\\"


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"
