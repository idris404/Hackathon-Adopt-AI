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
│   └── scenarios/
│       ├── complete_case/
│       │   ├── source.json
│       │   └── expected-restitution.json
│       └── incomplete_case/
│           ├── source.json
│           └── expected-restitution.json
├── protocols/
│   └── ruleset-pending-review.json
├── schemas/
│   ├── source-case.schema.json
│   └── restitution.schema.json
├── src/hla_data_model/
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

The project has no runtime dependency outside the Python standard library.

## Current acceptance criteria

- both canonical scenario pairs validate;
- identifiers and ISO 8601 timestamps are stable;
- `synthetic` and `human_validation_required` are always `true`;
- source-result absence remains explicit and distinct from `negative`;
- an incomplete factor appears in the restitution's `missing_data` list;
- no simplified-review candidate is emitted while the ruleset is unvalidated;
- source inputs do not contain derived scores or risk categories.

## Deferred decisions

The following inputs are unresolved and must not receive invented weights:

- diabetes, hypertension, and autoimmune disease;
- previous transplantation;
- CAR-T and other antibody-based treatments;
- the definition of regular transfusion;
- totals above six;
- minimum duration and result count for a constant negative history;
- any Immucor performance table used to arbitrate discordance.
