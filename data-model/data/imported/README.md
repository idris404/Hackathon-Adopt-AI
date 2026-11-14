# Imported synthetic profiles

These files are derived from the explicitly synthetic
`patients_synthetiques.csv` source with `profile-csv-importer-v1`.

- `profile-source-cases.jsonl` contains 980 kidney-only source profiles;
- `profile-restitutions.jsonl` contains profile results recomputed with
  `DEMO-PARTIAL-0.2.0`;
- `profile-import-report.json` records hashes, exclusions, contradictions, and
  recalculated category distributions.

The 20 kidney-pancreas records are outside the current demonstrator scope and
are excluded. The three source risk columns and `_anomalies_injectees` are not
copied into source cases or used as model inputs. Detected contradictions are
represented through availability states so they cannot receive a favorable
score silently.
