# Patient profile dataset v2

This directory contains the normalized kidney-only import of the large
synthetic patient dataset.

- `profile-source-cases.jsonl.gz` contains 50,019 patient profiles without a
  derived patient score;
- `profile-outcomes.jsonl.gz` contains future outcome labels in a separate
  file joined by `case_id`;
- `profile-import-report.json` records hashes, exclusions, partitions,
  contradictions, and label coverage.

The 981 kidney-pancreas rows are excluded from the current kidney-only scope.
The `_verite_*` columns and `_anomalies_injectees` are generation metadata and
are not copied into patient inputs. Outcome fields are also excluded from
profile features to prevent target leakage.

Patient scoring remains `pending_healthcare_professional_scoring`. Derived
score artifacts will be generated after the scoring protocol is received and
versioned; the normalized source facts remain unchanged.
