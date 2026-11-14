# Raw synthetic data

`patients_synthetiques_v2.csv.gz` is a deterministic gzip copy of the supplied
51,000-row synthetic CSV. Its uncompressed SHA-256 is recorded in
`../profile-v2/profile-import-report.json`.

Do not edit the raw file. Normalization, filtering, and label separation belong
in `profile_csv_v2_importer.py`.
