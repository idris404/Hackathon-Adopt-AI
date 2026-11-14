# HLA Twin data model

Current deterministic data pipeline for the synthetic kidney-transplant
demonstrator. The active dataset is patient-profile v3; serum/MFI histories are
the next vertical slice.

## Active layout

```text
data-model/
├── data/
│   ├── raw/
│   │   └── patients_synthetiques_v3.csv.gz
│   ├── processed/patient-profiles/
│   │   ├── profile-source-cases.jsonl.gz
│   │   ├── profile-scores.jsonl.gz
│   │   ├── profile-outcomes.jsonl.gz
│   │   └── profile-import-report.json
│   ├── scenarios/
│   └── dictionary.csv
├── protocols/
│   └── ruleset-profile-1.0.0.json
├── schemas/
├── src/hla_data_model/
│   ├── profile_normalization.py
│   ├── profile_importer.py
│   ├── profile_analyzer.py
│   ├── history_analyzer.py
│   ├── case_analyzer.py
│   └── validator.py
└── tests/
```

Legacy v1/v2 imports and committed generated demo artifacts have been removed.
Regenerable tools remain available for contract and future serum testing.

## Import patient profiles

From `data-model/`:

```bash
PYTHONPATH=src python3 -m hla_data_model.profile_importer \
  --input data/raw/patients_synthetiques_v3.csv.gz \
  --sources data/processed/patient-profiles/profile-source-cases.jsonl.gz \
  --profiles data/processed/patient-profiles/profile-scores.jsonl.gz \
  --outcomes data/processed/patient-profiles/profile-outcomes.jsonl.gz \
  --report data/processed/patient-profiles/profile-import-report.json
```

The import is deterministic and kidney-only. Generation truth, injected anomaly
labels, and simulated future outcomes never enter patient-profile scoring.

## Patient scoring

`PROFILE-1.0.0` calculates eleven explicit factors and maps the total to:

- `minimal`: 0–1;
- `moderate`: 2–3;
- `medium`: 4–5;
- `high`: 6–7;
- `very_high`: 8 or more;
- `uncertain`: a required scoring input is missing or contradictory.

Every output retains `human_validation_required=true`. The demonstrator is
decision support, not autonomous clinical validation.

## Serum/MFI status

The current patient dataset contains no serum history. `history_analyzer.py`
and the source contract are retained for the next slice: three prior analyses
plus the current analysis over at least three years, using longitudinal MFI and
the versioned assay positivity threshold.

## Checks

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m hla_data_model.validator data/scenarios
```
