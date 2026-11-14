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
