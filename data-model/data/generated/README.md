# Generated source cases

Files in this directory are deterministic synthetic inputs for interface and
contract testing. They are not statistically representative of a transplant
population and must not be used to claim model or clinical performance.

The generator intentionally produces no score, risk category, interpretation,
decision, expected restitution, or performance label.

The batch pipeline materializes three reproducible files:

- `source-cases.jsonl`: source-only synthetic cases;
- `restitutions.jsonl`: deterministic integrated outputs;
- `dataset-report.json`: distributions, quality counters, versions, hashes,
  and line-level validation errors.

The checked dataset uses `balanced-generator-v1`. Its scenario quotas are
designed to cover product states and must not be presented as real-world
clinical prevalence. `provenance.simulation_scenario` is generation metadata
and is prohibited as an ML input feature.

ML preparation produces four additional files:

- `model-features.csv`: pre-evaluation source features only;
- `simulation-labels.csv`: simulated outputs, kept separate from features;
- `dataset-splits.csv`: deterministic 70/15/15 assignments;
- `feature-manifest.json`: schemas, hashes, exclusions, and safety status.
