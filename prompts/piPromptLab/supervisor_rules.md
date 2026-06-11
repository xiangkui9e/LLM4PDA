# Human Supervisor Rules for piPromptLab

## Purpose

The human supervisor controls all inter-agent communication in piPromptLab. The supervisor routes messages, filters feedback, merges complementary suggestions, resolves conflicts, maintains the schema version history, and decides whether convergence has been reached.

## Core Principles

1. The supervisor must preserve disease-level generality.
2. The supervisor must remove prediction-target-specific or benchmark-specific content.
3. The supervisor must not add disease-specific piRNA association evidence.
4. The supervisor must prioritize fields that are consistently available across diseases.
5. The supervisor must reduce redundancy and noise.
6. The supervisor must document all retained, revised, merged, or removed fields.

## Routing Rule

At each iteration:

1. Select one speaking agent according to the rotation schedule.
2. Provide the current schema to the speaking agent for revision.
3. Provide the speaking agent's revised schema to the two reviewing agents.
4. Collect independent critiques from the reviewing agents.
5. Filter and integrate feedback into a new schema version.
6. Return the revised schema to the next speaking agent.

## Filtering Rule

The supervisor removes feedback if it contains:

1. Explicit piRNA identifiers.
2. PIWI/piRNA-specific disease evidence.
3. Known piRNA-disease association labels.
4. Benchmark dataset labels or split information.
5. Prediction-target-specific statements.
6. Unsupported speculation.
7. Duplicated fields.
8. Fields that cannot be consistently generated across diseases.
9. Overly narrow disease-subtype details unless they can be generalized.
10. Claims that would require manual literature curation for every disease.

## Merging Rule

The supervisor merges fields when they capture overlapping concepts. Examples:

- “Disease classification” and “disease nature” may be merged.
- “Molecular mechanism” and “cellular pathogenesis” may be merged if they overlap.
- “Clinical diagnosis” and “testing methods” may be merged into one diagnostic field.
- “Comorbidities” and “complications” may be combined.

## Conflict-Resolution Rule

When agents disagree:

1. Prefer disease-level fields over association-specific fields.
2. Prefer broadly available fields over rare or disease-specific fields.
3. Prefer factual and curated biomedical background over speculative mechanistic interpretation.
4. Prefer concise fields that improve semantic representation over lengthy narrative requirements.
5. Retain uncertainty wording when evidence strength varies across diseases.
6. Remove any content that increases leakage risk.

## Version-Control Rule

Each schema version should be recorded with:

- version ID,
- speaking agent,
- reviewing agents,
- fields added,
- fields revised,
- fields merged,
- fields removed,
- supervisor rationale,
- leakage-control decision,
- convergence status.

## Freezing Rule

The final schema can be frozen only when:

1. No agent proposes a new essential field.
2. All retained fields are disease-level and task-general.
3. The schema can be applied consistently across all diseases.
4. Leakage-control constraints are explicitly included.
5. The output format is defined.
6. The schema is judged suitable for downstream text embedding.
