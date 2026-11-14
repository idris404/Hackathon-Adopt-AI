# HLA Twin data model

This workspace contains the first contract-first vertical slice for the HLA
Twin hackathon demonstrator. All records are synthetic and deterministic.

## Safety boundary

- The source cases never contain real patient data.
- A missing value is never converted to a negative result or to zero.
- Medical weights, thresholds, history interpretation, and discordance
  arbitration remain `pending_review` until Ahmed validates them.
- The current validator checks structure and safety invariants only. It does not
  compute a medical score.
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
│   └── ruleset-partial-0.2.0.json
├── schemas/
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

Sex, dialysis, rejection suspicion, and organ context are copied into the
restitution as non-scored context. They cannot silently affect the profile
score. Pregnancy, CAR-T, and therapeutic-antibody rules remain `pending_review`.

## Profile analyzer

`profile_analyzer.py` now builds the complete profile restitution from source
facts. PF-01 (age), PF-02 (pregnancy), and PF-07 (transfusion) use the rules
validated by Ahmed. A full score and category are emitted only when every other
factor is explicitly absent; an active, missing, or contradictory factor whose
weight is unresolved keeps the full score null and the category `uncertain`.
The validated partial score remains visible in both cases.

## History analyzer

`history_analyzer.py` preserves every source result, identifies the latest
serum, exposes missing results and same-serum discordances, and describes
constant, evolving, fluctuating, or indeterminate histories. It emits `stable`
only for repeated identical source categories. It never emits `increasing` or
`decreasing` without a validated ordinal or quantitative rule.

## Case integration

`case_analyzer.py` combines the profile and history outputs into the complete
restitution contract. With the pending ruleset it can emit only
`human_review_required` or `blocked` while the exact negative-constant history
definition remains pending. The simplified-review route is encoded but cannot
activate until that history definition is validated, and it will always retain
human confirmation.

The project has no runtime dependency outside the Python standard library.

## Current acceptance criteria

- all six canonical scenario pairs validate;
- identifiers and ISO 8601 timestamps are stable;
- `synthetic` and `human_validation_required` are always `true`;
- source-result absence remains explicit and distinct from `negative`;
- an incomplete factor appears in the restitution's `missing_data` list;
- no simplified-review candidate is emitted while the ruleset is unvalidated;
- source inputs do not contain derived scores or risk categories;
- current source results are preserved before history pattern and trend;
- discordant results from one serum remain unresolved;
- generated volume data contains inputs only and is not representative.

## Deferred decisions

The following inputs are unresolved and must not receive invented weights:

- diabetes, hypertension, and autoimmune disease;
- previous transplantation;
- CAR-T and other antibody-based treatments;
- the definition of regular transfusion;
- totals above six;
- minimum duration and result count for a constant negative history;
- any Immucor performance table used to arbitrate discordance.
