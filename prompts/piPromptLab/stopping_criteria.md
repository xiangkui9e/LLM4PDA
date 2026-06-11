# piPromptLab Stopping Criteria

## Purpose

The stopping criteria define when the human-mediated schema-construction process is considered converged and the disease-description schema can be frozen.

## Convergence Criteria

The schema can be finalized when all of the following conditions are met:

1. **No new essential fields:** No agent proposes an additional disease-level field that is essential and non-redundant.
2. **Completeness:** The schema covers clinical, molecular, genetic, pathway-level, therapeutic, diagnostic, and pathological context.
3. **Factual consistency:** The schema includes instructions to avoid fabrication and to state “No available information” when information is unavailable or uncertain.
4. **Disease-level generality:** All fields describe general disease-level background rather than specific piRNA-disease associations.
5. **Machine encodability:** The fields are suitable for conversion into text embeddings.
6. **Non-redundancy:** Overlapping fields have been merged or removed.
7. **Leakage control:** The prompt explicitly prohibits piRNA identifiers, PIWI/piRNA-specific evidence, PDA labels, benchmark labels, train/test split information, prediction targets, and model predictions.
8. **Output consistency:** The final output format is defined as a cohesive disease-level biomedical paragraph.
9. **Cross-fold stability:** The schema is frozen before disease-description generation and remains unchanged across all cross-validation folds.

## Finalization Decision

When the criteria above are satisfied, the human supervisor records the schema version as final and freezes it for disease-description generation. No downstream model performance information is used to modify the schema after freezing.

## Recommended Reporting Sentence

The piPromptLab schema was frozen when no additional essential schema field was proposed and all agents agreed that the schema was complete, factually consistent, disease-level, machine-encodable, and suitable for downstream embedding. The frozen schema was then used to generate disease descriptions, which were embedded, cached, and kept unchanged across all cross-validation folds.
