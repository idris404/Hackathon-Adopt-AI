import csv
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path

from app.constants.seed import FIRST_CSV_DATA_LINE


def read_csv_rows(
    csv_path: Path, check_headers: Callable[[Sequence[str]], None]
) -> Iterator[tuple[int, dict[str, str]]]:
    """Lit le CSV ligne à ligne : `(numéro de ligne dans le fichier, ligne)`.

    Le fichier est très large et compte des dizaines de milliers de lignes : jamais tout en
    mémoire. `check_headers` reçoit l'en-tête et lève si une colonne attendue manque.
    """
    with csv_path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        check_headers(reader.fieldnames or [])
        yield from enumerate(reader, start=FIRST_CSV_DATA_LINE)
