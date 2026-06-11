# piPromptLab Information-Transfer Rules

## Purpose

The information-transfer rules define which agent suggestions are retained, revised, merged, downgraded, or removed during the human-mediated schema-construction process.

## Retain

Retain a suggestion when it is:

1. Disease-level rather than association-specific.
2. Supported by standard biomedical knowledge or curated databases.
3. Applicable across most or all diseases.
4. Machine-encodable as text.
5. Useful for representing disease semantics.
6. Non-redundant with existing schema fields.
7. Unlikely to introduce piRNA-disease association leakage.

Examples:
- disease classification and nature,
- disease type,
- key associated genes or mutations,
- key proteins,
- signaling pathways,
- epigenetic mechanisms,
- molecular or cellular pathogenesis,
- treatments and mechanisms,
- symptoms and signs,
- comorbidities and complications,
- inheritance and genetic factors,
- diagnostic criteria and testing methods.

## Revise

Revise a suggestion when it is useful but too broad, vague, or potentially misleading.

Examples:
- “molecular mechanisms” → “brief molecular or cellular pathogenesis mechanisms”.
- “genetics” → “inheritance patterns and known genetic factors”.
- “drug therapy” → “established treatment drugs and therapeutic mechanisms”.
- “pathways” → “related signaling pathways”.

## Merge

Merge suggestions when they are conceptually overlapping.

Examples:
- “disease category” and “disease nature” → “disease classification and nature”.
- “clinical manifestations” and “symptoms” → “typical clinical symptoms and signs”.
- “diagnosis” and “testing” → “diagnostic criteria and clinical testing methods”.
- “comorbidity” and “complication” → “common comorbidities and complications”.

## Downgrade / Qualify

Downgrade a suggestion when evidence varies across diseases.

Required qualifiers:
- “commonly reported”
- “suspected”
- “under investigation”
- “No available information”

Use downgrading when a field is generally useful but not universally available.

## Remove

Remove a suggestion when it contains:

1. piRNA identifiers or PIWI/piRNA-specific disease evidence.
2. PDA labels, benchmark labels, or train/test split information.
3. prediction-target-specific statements.
4. model predictions.
5. unsupported mechanistic speculation.
6. fields requiring disease-specific manual curation beyond the scope of the protocol.
7. excessive detail that may add noise to embeddings.
8. duplicated information already covered by another field.

## Leakage-Control Rule

Any suggestion that explicitly or implicitly encodes known piRNA-disease associations must be removed. Disease descriptions must focus on general disease-level biomedical background and must not contain statements implying that a specific piRNA is associated with a disease.

## Output Rule

The final schema must generate a single cohesive narrative paragraph. The paragraph should integrate all available structured points while remaining medically precise, self-contained, and suitable for downstream embedding.
