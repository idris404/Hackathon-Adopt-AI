import uuid
from enum import StrEnum
from typing import Final

# Routes
PATIENTS_ROUTER_PREFIX: Final = "/patients"
PATIENTS_ROUTER_TAG: Final = "patients"
PATIENT_NOT_FOUND_CODE: Final = "PATIENT_NOT_FOUND"

# Tables
PATIENTS_TABLE_NAME: Final = "patients"
# `patient_id` : identifiant fonctionnel unique d'un patient (« SYN-0001 »), repris du CSV.
PATIENT_CODE_MAX_LENGTH: Final = 50
FIRSTNAME_MAX_LENGTH: Final = 100
LASTNAME_MAX_LENGTH: Final = 100
CITY_MAX_LENGTH: Final = 100
COUNTRY_MAX_LENGTH: Final = 100


class Gender(StrEnum):
    """Mêmes valeurs que la colonne `sexe` du CSV source."""

    MALE = "M"
    FEMALE = "F"


class PatientSortField(StrEnum):
    """Liste blanche des colonnes sur lesquelles le client peut trier."""

    PATIENT_ID = "patient_id"
    FIRSTNAME = "firstname"
    LASTNAME = "lastname"
    BIRTH = "birth"
    GENDER = "gender"
    CITY = "city"
    COUNTRY = "country"
    CREATED_AT = "created_at"


DEFAULT_PATIENT_SORT_FIELD: Final = PatientSortField.LASTNAME

# Seed ---------------------------------------------------------------------------------------
# Colonnes du CSV qui alimentent la table `patients` (identité). La colonne `patient_id` est
# dans constants/seed.py : les deux contextes la lisent.
CSV_COLUMN_BIRTH: Final = "date_naissance"
CSV_COLUMN_GENDER: Final = "sexe"

# L'id d'un patient est dérivé du `patient_id` du CSV (UUID v5) : relancer le seed retrouve les
# mêmes id, donc ne crée pas de doublons. C'est aussi ce qui relie un patient synthétique à son patient.
SEED_UUID_NAMESPACE: Final = uuid.UUID("6f1c2a52-9d3e-4b7a-8c41-2f0e5b9a7d13")

# Le CSV ne contient ni nom, ni prénom, ni ville, ni pays. Ils sont tirés de ces listes, de façon
# déterministe à partir du `patient_id` : ce sont des identités fictives, sans lien avec une
# personne réelle.
SEED_MALE_FIRSTNAMES: Final = (
    "Lucas", "Hugo", "Louis", "Jules", "Nathan", "Théo", "Adam", "Gabriel", "Léo", "Arthur",
    "Paul", "Antoine", "Maxime", "Thomas", "Julien", "Nicolas", "Pierre", "Mehdi", "Karim",
    "Samuel", "Yanis", "Romain", "Alexandre", "Mathieu", "Olivier",
)  # fmt: skip
SEED_FEMALE_FIRSTNAMES: Final = (
    "Emma", "Léa", "Chloé", "Camille", "Inès", "Sarah", "Manon", "Jade", "Louise", "Alice",
    "Clara", "Julie", "Marie", "Océane", "Laura", "Nina", "Zoé", "Amina", "Sofia", "Élodie",
    "Claire", "Anaïs", "Margaux", "Lucie", "Nadia",
)  # fmt: skip
SEED_LASTNAMES: Final = (
    "Martin", "Bernard", "Dubois", "Thomas", "Robert", "Richard", "Petit", "Durand", "Leroy",
    "Moreau", "Simon", "Laurent", "Lefebvre", "Michel", "Garcia", "David", "Bertrand", "Roux",
    "Vincent", "Fournier", "Morel", "Girard", "André", "Mercier", "Dupont", "Lambert", "Bonnet",
    "François", "Martinez", "Legrand", "Garnier", "Faure", "Rousseau", "Blanc", "Guérin",
    "Muller", "Henry", "Roussel", "Perrin", "Morin", "Mathieu", "Clément", "Gauthier", "Dumont",
    "Lopez", "Fontaine", "Chevalier", "Robin", "Masson",
)  # fmt: skip
# (ville, pays)
SEED_CITIES: Final = (
    ("Paris", "France"), ("Lyon", "France"), ("Marseille", "France"), ("Toulouse", "France"),
    ("Nice", "France"), ("Nantes", "France"), ("Strasbourg", "France"),
    ("Montpellier", "France"), ("Bordeaux", "France"), ("Lille", "France"),
    ("Rennes", "France"), ("Reims", "France"), ("Grenoble", "France"), ("Dijon", "France"),
    ("Angers", "France"), ("Bruxelles", "Belgique"), ("Liège", "Belgique"),
    ("Genève", "Suisse"), ("Lausanne", "Suisse"), ("Luxembourg", "Luxembourg"),
    ("Montréal", "Canada"),
)  # fmt: skip
