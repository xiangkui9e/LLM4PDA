# Representative piPromptLab Iteration Record

## Important Note

This file provides a **representative schema-refinement record** reconstructed from the documented piPromptLab protocol, final schema, and retained design decisions. It should not be described as a complete raw transcript unless replaced with the original raw multi-session logs.

## Iteration ID

Round 2, Schema Version v0.2 → v0.3

## Speaking Agent

Molecular Biology Specialist

## Reviewing Agents

- Computational Biology Specialist
- Clinical Medicine Specialist

## Current Schema Before This Round

The current schema contained the following candidate fields:

1. Disease classification.
2. Disease type.
3. Molecular mechanisms.
4. Genes and mutations.
5. Pathways.
6. Clinical symptoms.
7. Diagnostic methods.
8. Treatments.

## Speaking Agent Proposal

The Molecular Biology Specialist suggested that the schema should explicitly include proteins and epigenetic mechanisms because many disease processes are mediated not only by gene mutations but also by protein-level dysregulation and epigenetic remodeling. The agent also suggested that “molecular mechanisms” should be revised to include cellular processes such as inflammation, apoptosis dysregulation, immune evasion, proliferation, and metabolic dysregulation.

### Proposed additions

1. Key proteins involved in disease pathogenesis.
2. Epigenetic mechanisms, including DNA methylation, histone modifications, and chromatin remodeling.
3. Molecular or cellular pathogenesis mechanisms.

### Rationale

Genes, proteins, pathways, and epigenetic regulation capture complementary levels of disease biology. Keeping these fields separate can improve the granularity of disease semantic representations.

## Peer Review by Computational Biology Specialist

### Overall judgment

The proposed fields are useful but should be constrained to avoid inconsistent generation and hallucination.

### Fields to retain

- Key proteins involved in pathogenesis.
- Related signaling pathways.
- Brief molecular or cellular pathogenesis mechanisms.

### Fields to revise

- “Epigenetic mechanisms” should include an instruction to report “No available information” when disease-specific epigenetic information is unclear.

### Leakage concerns

The schema must not mention piRNA, PIWI, piRNA-disease associations, benchmark labels, or prediction targets. Molecular fields should describe general disease biology only.

### Recommendation

Retain the proposed fields but add factuality and leakage-control constraints.

## Peer Review by Clinical Medicine Specialist

### Overall judgment

The molecular additions are useful but should be balanced by clinical fields so that the description remains disease-level and medically interpretable.

### Fields to retain

- Disease classification and nature.
- Disease type.
- Typical clinical symptoms and signs.
- Diagnostic criteria and clinical testing methods.
- Established treatment drugs and therapeutic mechanisms.

### Fields to revise

- Treatments should specify established drugs and mechanisms of action rather than speculative therapies.
- Diagnosis should include clinical testing methods such as imaging, biopsy, ELISA, and biomarkers when applicable.

### Leakage concerns

No disease-specific piRNA evidence should be included in the disease background description.

### Recommendation

Retain molecular fields and strengthen treatment and diagnosis fields.

## Human Supervisor Filtering and Integration

### Retained suggestions

1. Add “key proteins involved in pathogenesis.”
2. Add “epigenetic mechanisms.”
3. Revise “molecular mechanisms” to “brief molecular or cellular pathogenesis mechanisms.”
4. Revise “treatments” to “established treatment drugs and therapeutic mechanisms.”
5. Revise “diagnostic methods” to “diagnostic criteria and clinical testing methods.”

### Removed suggestions

No retained suggestion was removed in this round. However, the supervisor removed any wording that could encourage piRNA-specific evidence or prediction-target-specific statements.

### Conflict resolution

The supervisor accepted the molecular biology agent’s request for finer biological granularity but applied the computational biology agent’s constraint that uncertain information must be qualified or marked as “No available information.” The supervisor also accepted the clinical medicine agent’s recommendation to keep clinical fields explicit and clinically grounded.

## Updated Schema After This Round

1. Disease classification and nature.
2. Disease type.
3. Key associated genes or mutations.
4. Key proteins involved in pathogenesis.
5. Related signaling pathways.
6. Epigenetic mechanisms.
7. Brief molecular or cellular pathogenesis mechanisms.
8. Established treatment drugs and therapeutic mechanisms.
9. Typical clinical symptoms and signs.
10. Common comorbidities and complications.
11. Inheritance patterns and known genetic factors.
12. Diagnostic criteria and clinical testing methods.

## Added Constraints

1. If a specific data point is unavailable or unclear, state “No available information.”
2. Do not fabricate gene names, drug names, molecular mechanisms, or diagnostic tools.
3. Do not mention piRNA, PIWI, hsa_piR identifiers, piRNA-disease associations, PDA labels, benchmark datasets, training/test splits, prediction targets, or model predictions.

## Convergence Status

Not yet converged in this representative round. The schema required an additional review round to confirm redundancy removal, leakage-control wording, and final output format.
