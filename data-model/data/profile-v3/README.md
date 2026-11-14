# Patient profile dataset v3

This directory is generated deterministically from the corrected synthetic CSV.

- `profile-source-cases.jsonl.gz` contains normalized kidney-only profile facts;
- `profile-scores.jsonl.gz` contains the deterministic `PROFILE-1.0.0` score and category;
- `profile-outcomes.jsonl.gz` contains separated simulated future labels;
- `profile-import-report.json` records hashes, exclusions, contradictions, and distributions.

Kidney-pancreas rows are excluded from the kidney-only demonstrator. Every
`_verite_*` field and `_anomalies_injectees` is generation metadata and is
excluded from patient inputs. The artifacts are synthetic and are not evidence
of clinical performance.
