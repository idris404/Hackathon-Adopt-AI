# Raw synthetic data

`patients_synthetiques_v2.csv.gz` is a deterministic gzip copy of the supplied
51,000-row synthetic CSV. Its uncompressed SHA-256 is recorded in
`../profile-v2/profile-import-report.json`.

Do not edit the raw file. Normalization, filtering, and label separation belong
in `profile_csv_v2_importer.py`.

`patients_synthetiques_v3.csv.gz` is the corrected 51,000-row synthetic source.
Its uncompressed SHA-256 is recorded in
`../profile-v3/profile-import-report.json`. Normalize it only through
`profile_csv_v3_importer.py`; never use `_verite_*`, outcome, or injected-
anomaly columns as patient-profile inputs.
