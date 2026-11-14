# HLA Twin data model

This workspace contains the first contract-first vertical slice for the HLA
Twin hackathon demonstrator. All records are synthetic and deterministic.

## Safety boundary

- The source cases never contain real patient data.
- A missing value is never converted to a negative result or to zero.
- Patient-profile weights and category thresholds are versioned in
  `protocols/ruleset-profile-1.0.0.json`.
- Quantitative assay proximity, directional trends, and discordance arbitration
  remain `pending_review`.
- Every expected restitution requires human validation.

## Layout

```text
data-model/
├── data/
│   ├── dictionary.csv
│   ├── generated/
│   │   └── README.md
│   ├── imported/
│   │   ├── profile-source-cases.jsonl
│   │   ├── profile-restitutions.jsonl
│   │   └── profile-import-report.json
│   ├── longitudinal/
│   │   ├── source-cases.jsonl
│   │   ├── restitutions.jsonl
│   │   ├── history-generation-report.json
│   │   └── dataset-report.json
│   ├── profile-v2/
│   │   ├── profile-source-cases.jsonl.gz
│   │   ├── profile-outcomes.jsonl.gz
│   │   └── profile-import-report.json
│   ├── profile-v3/
│   │   ├── profile-source-cases.jsonl.gz
│   │   ├── profile-scores.jsonl.gz
│   │   ├── profile-outcomes.jsonl.gz
│   │   └── profile-import-report.json
│   ├── raw/
│   │   └── patients_synthetiques_v2.csv.gz
│   └── scenarios/
│       ├── complete_case/
│       ├── incomplete_case/
│       ├── doubtful_case/
│       ├── discordant_case/
│       ├── contradictory_profile_case/
│       └── fluctuating_case/
│           ├── source.json
│           └── expected-restitution.json
├── protocols/
│   ├── ruleset-pending-review.json
│   ├── ruleset-partial-0.2.0.json
│   └── ruleset-profile-1.0.0.json
├── schemas/
│   ├── profile-outcome.schema.json
│   ├── source-case.schema.json
│   └── restitution.schema.json
├── src/hla_data_model/
│   ├── batch_pipeline.py
│   ├── balanced_generator.py
│   ├── case_analyzer.py
│   ├── feature_pipeline.py
│   ├── generator.py
│   ├── history_analyzer.py
│   ├── profile_analyzer.py
│   ├── profile_csv_importer.py
│   ├── profile_csv_v2_importer.py
│   ├── profile_csv_v3_importer.py
│   ├── profile_history_generator.py
│   └── validator.py
└── tests/
    └── test_validation.py
```

Source-like inputs and expected derived results are intentionally stored in
different files.

## Run the checks

From `data-model/`:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m hla_data_model.validator data/scenarios
```

Generate non-representative source cases for interface testing:

```bash
PYTHONPATH=src python3 -m hla_data_model.generator \
  --count 100 \
  --seed 20261114 \
  --output data/generated/source-cases.jsonl
```

The generator never produces a score, risk category, interpretation, decision,
expected restitution, or performance label.

Generate the recommended stratified demo dataset:

```bash
PYTHONPATH=src python3 -m hla_data_model.balanced_generator \
  --seed 20261114 \
  --output data/generated/source-cases.jsonl
```

Its quotas are explicit coverage choices, not clinical prevalence estimates.
The `simulation_scenario` provenance label must be excluded from ML features.

Process a complete JSONL dataset and generate restitutions plus a quality
report:

```bash
PYTHONPATH=src python3 -m hla_data_model.batch_pipeline \
  --input data/generated/source-cases.jsonl \
  --restitutions data/generated/restitutions.jsonl \
  --report data/generated/dataset-report.json
```

Invalid records are isolated in the report with their line number and do not
prevent valid records from being processed.

Build leakage-aware ML artifacts:

```bash
PYTHONPATH=src python3 -m hla_data_model.feature_pipeline \
  --sources data/generated/source-cases.jsonl \
  --restitutions data/generated/restitutions.jsonl \
  --features data/generated/model-features.csv \
  --labels data/generated/simulation-labels.csv \
  --splits data/generated/dataset-splits.csv \
  --manifest data/generated/feature-manifest.json
```

Features, simulated labels, and train/validation/test assignments are separate.
The split is 70/15/15 and stratified by generation scenario for coverage only.

Import the synthetic profile-only CSV and recompute profile categories with the
local ruleset:

```bash
PYTHONPATH=src python3 -m hla_data_model.profile_csv_importer \
  --input /path/to/patients_synthetiques.csv \
  --sources data/imported/profile-source-cases.jsonl \
  --profiles data/imported/profile-restitutions.jsonl \
  --report data/imported/profile-import-report.json
```

The importer accepts only rows explicitly marked synthetic, keeps kidney-only
records, and excludes kidney-pancreas records. It never copies the source risk
category, status, or justification. PF-01, PF-02, and PF-07 are recalculated by
`profile_analyzer.py`; unresolved active factors keep the full category
`uncertain`. HLA typing and detailed source facts are preserved under
`patient_profile.source_context` as non-scored context.

Import the large v2 profile dataset without applying a patient score:

```bash
PYTHONPATH=src python3 -m hla_data_model.profile_csv_v2_importer \
  --input data/raw/patients_synthetiques_v2.csv.gz \
  --sources data/profile-v2/profile-source-cases.jsonl.gz \
  --outcomes data/profile-v2/profile-outcomes.jsonl.gz \
  --report data/profile-v2/profile-import-report.json
```

The v2 importer keeps profile facts and future outcomes in separate compressed
JSONL files. The source partitions are retained only as provenance. Generation
truth columns and injected-anomaly labels are excluded from patient inputs.
No patient score is generated until the healthcare-professional scoring rules
are received and versioned.

Import and score the corrected v3 profile dataset:

```bash
PYTHONPATH=src python3 -m hla_data_model.profile_csv_v3_importer \
  --input data/raw/patients_synthetiques_v3.csv.gz \
  --sources data/profile-v3/profile-source-cases.jsonl.gz \
  --profiles data/profile-v3/profile-scores.jsonl.gz \
  --outcomes data/profile-v3/profile-outcomes.jsonl.gz \
  --report data/profile-v3/profile-import-report.json
```

The v3 importer calculates only `PROFILE-1.0.0`. It excludes every `_verite_*`
column and `_anomalies_injectees` from patient inputs, and keeps future outcome
labels in a separate file.

Attach deterministic longitudinal assay histories to the imported profiles,
then compute the integrated restitutions:

```bash
PYTHONPATH=src python3 -m hla_data_model.profile_history_generator \
  --input data/imported/profile-source-cases.jsonl \
  --output data/longitudinal/source-cases.jsonl \
  --report data/longitudinal/history-generation-report.json \
  --seed 20261114

PYTHONPATH=src python3 -m hla_data_model.batch_pipeline \
  --input data/longitudinal/source-cases.jsonl \
  --restitutions data/longitudinal/restitutions.jsonl \
  --report data/longitudinal/dataset-report.json
```

The history scenarios are balanced for software and demo coverage only. They
are not prevalence estimates. Transitions preserve their source sequence, but
their trend stays `indeterminate` because no ordinal clinical rule has been
validated. The generator refuses to overwrite an existing serum history.

## Patient profile v0.2

The source profile now keeps the following facts explicitly and without medical
interpretation:

- age and sex at birth;
- pregnancy history and transfusion history;
- diabetes, hypertension, and autoimmune disease;
- dialysis status and known start date;
- source suspicion-of-rejection flag, which is not a diagnosis;
- kidney workflow status and registration date;
- previous transplant history;
- CAR-T treatments and therapeutic-antibody treatments as separate histories.
- optional source HLA and detailed profile facts as non-scored context.

Sex, dialysis, and organ context are copied as non-scored context. Rejection
suspicion is preserved in context and also scored explicitly as PF-10.

## Profile analyzer

`profile_analyzer.py` calculates eleven explicit factors from age, pregnancy,
diabetes, hypertension, autoimmune disease, previous transplants and rejection
history, transfusions, CAR-T, antibody treatment, rejection suspicion, and the
initial chronic kidney disease. The
category bands are 0–1 minimal, 2–3 moderate, 4–5 medium, 6–7 high, and 8+
very high. A missing or contradictory scoring criterion makes the category
`uncertain`; the available partial score remains visible.

## History analyzer

`history_analyzer.py` preserves every source result, identifies the latest
serum, exposes missing results and same-serum discordances, and describes
constant, evolving, fluctuating, or indeterminate histories. A categorical
constant pattern needs three prior analyses plus the current analysis spanning
at least three years. Qualification remains pending until histories expose the
MFI value needed to verify that each relative gap is at most 50%. It never
emits `increasing` or `decreasing` without a validated quantitative rule.

## Case integration

`case_analyzer.py` exposes an explicit route for simplified-review candidates,
supervised full-dossier review, mandatory manual biologist review, uncertain
profiles, and unresolved discordance. A simplified-review candidate still
retains `human_validation_required=true`; this demonstrator never emits a final
autonomous clinical validation.

The project has no runtime dependency outside the Python standard library.

## Current acceptance criteria

- all six canonical scenario pairs validate;
- identifiers and ISO 8601 timestamps are stable;
- `synthetic` and `human_validation_required` are always `true`;
- source-result absence remains explicit and distinct from `negative`;
- an incomplete factor appears in the restitution's `missing_data` list;
- simplified-review candidates require a minimal profile and a qualified
  non-discordant history with three prior analyses plus the current one;
- source inputs do not contain derived scores or risk categories;
- current source results are preserved before history pattern and trend;
- discordant results from one serum remain unresolved;
- generated volume data contains inputs only and is not representative.

## Deferred decisions

The following inputs remain unresolved and must not receive invented rules:

- the source field for chronic diseases other than the explicit initial kidney
  disease, diabetes, hypertension, and autoimmune fields;
- the longitudinal MFI field and unit used by the validated 50% proximity threshold;
- the versioned assay positivity threshold used when the preceding MFI is zero;
- increasing or decreasing quantitative assay trends;
- any Immucor performance table used to arbitrate discordance.
