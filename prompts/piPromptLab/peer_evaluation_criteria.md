# piPromptLab Peer-Evaluation Criteria

## Purpose

In each piPromptLab iteration, the non-speaking agents independently review the speaking agent's proposed schema revision. The review is performed using the following rubric.

## Review Rubric

Each candidate schema field is evaluated across seven dimensions.

| Criterion | Question | Decision |
|---|---|---|
| Completeness | Does the schema miss an essential disease-level dimension? | Add / retain |
| Redundancy | Does the field overlap with another field? | Merge / remove |
| Factual consistency | Could the field encourage hallucination or unsupported claims? | Revise / qualify / remove |
| Disease-level generality | Can this field be generated across all diseases? | Retain / revise / remove |
| Machine encodability | Is the field suitable for text embedding? | Retain / revise |
| Clinical or biological relevance | Does the field capture meaningful disease context? | Retain / revise |
| Leakage risk | Could the field encode piRNA-disease association evidence? | Remove / constrain |

## Review Output Format

Each peer-evaluation response should use the following structure:

1. Overall judgment.
2. Fields to retain.
3. Fields to revise.
4. Fields to merge.
5. Fields to remove.
6. Fields to add.
7. Leakage concerns.
8. Final recommendation.

## Rating Scale

Each field may be assigned one of the following decisions:

- **Retain:** The field is useful, general, and low-risk.
- **Revise:** The field is useful but needs clearer wording or constraints.
- **Merge:** The field overlaps with an existing field.
- **Remove:** The field is unsupported, redundant, too narrow, or leakage-prone.
- **Add:** The field is missing and should be incorporated.
- **Qualify:** The field should allow uncertainty statements such as “No available information” or “under investigation”.

## Minimum Acceptance Standard

A schema field can be retained in the next version only if it satisfies all of the following:

1. It is disease-level.
2. It is not benchmark-specific.
3. It is not piRNA-association-specific.
4. It is sufficiently general across diseases.
5. It is compatible with text embedding.
6. It does not encourage unsupported factual claims.
