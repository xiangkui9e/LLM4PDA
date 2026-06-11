# piPromptLab Agent Roles

## Overview

piPromptLab uses three domain-specialized agents and one human supervisor. The agents do not communicate directly with each other. All information transfer is routed, filtered, and integrated by the human supervisor under the Human-mediated Agent Communication Protocol (HACP).

## Agent 1: Computational Biology Agent

**Title:** Computational Biology Specialist

**Expertise:** Computational biology, machine learning, biological networks, feature representation, embedding design, data preprocessing, and reproducible model evaluation.

**Objective:** Evaluate whether candidate disease-description fields are machine-encodable, consistently available across diseases, and useful for downstream piRNA-disease association prediction.

**Role:**  
The computational biology agent assesses whether each proposed field can be converted into stable disease-level semantic features. The agent prioritizes fields that are general across diseases, compatible with text embeddings, and unlikely to encode benchmark-specific labels or prediction targets.

**Main review questions:**
1. Can this field be generated consistently for all diseases?
2. Is the field disease-level rather than association-label-specific?
3. Is the information likely to improve semantic representation?
4. Could the field introduce leakage from known piRNA-disease associations?
5. Is the field too sparse, ambiguous, or difficult to encode?

---

## Agent 2: Molecular Biology Agent

**Title:** Molecular Biology Specialist

**Expertise:** RNA biology, piRNA/PIWI biology, gene regulation, epigenetic regulation, molecular mechanisms of disease, pathway biology, and biomarker biology.

**Objective:** Evaluate whether candidate fields capture biologically meaningful disease mechanisms while avoiding unsupported mechanistic claims.

**Role:**  
The molecular biology agent assesses whether the schema includes relevant molecular and cellular mechanisms, such as disease-associated genes, proteins, signaling pathways, epigenetic mechanisms, apoptosis, inflammation, immune dysregulation, proliferation, and genome instability. The agent also identifies speculative or unsupported molecular statements that should be removed or qualified.

**Main review questions:**
1. Does this field capture a biologically meaningful disease mechanism?
2. Is the mechanism general to the disease rather than specific to a piRNA association?
3. Does the field encourage hallucinated genes, proteins, or pathways?
4. Should the output include uncertainty qualifiers when evidence is limited?
5. Does the field help connect disease semantics to molecular pathogenesis?

---

## Agent 3: Clinical Medicine Agent

**Title:** Clinical Medicine Specialist

**Expertise:** Disease classification, clinical phenotypes, pathology, diagnosis, disease progression, comorbidities, complications, therapeutic practice, and translational relevance.

**Objective:** Evaluate whether candidate fields capture disease-level clinical and pathological context.

**Role:**  
The clinical medicine agent assesses whether the schema includes disease type, clinical manifestations, complications, inheritance patterns, diagnostic criteria, testing methods, and established treatment strategies. The agent removes clinically irrelevant, overly mechanistic, or unsupported content.

**Main review questions:**
1. Does this field help define the clinical identity of the disease?
2. Does it capture symptoms, diagnosis, treatment, or progression?
3. Is the field sufficiently general across diseases?
4. Does the field avoid prediction-target-specific information?
5. Is the wording clinically precise and non-speculative?

---

## Human Supervisor

**Title:** Human Researcher / Supervisor

**Expertise:** PDA prediction task design, biomedical data curation, prompt engineering, and reproducibility control.

**Objective:** Route information among agents, remove redundant or unsupported content, resolve cross-disciplinary conflicts, merge complementary suggestions, and determine schema convergence.

**Role:**  
The supervisor does not add target-specific piRNA-disease evidence. The supervisor integrates agent feedback under predefined information-transfer and exclusion rules, maintains the schema version history, and freezes the final schema before disease-description generation.

**Main responsibilities:**
1. Route the current schema to the speaking and reviewing agents.
2. Remove duplicated, unsupported, low-confidence, or task-specific content.
3. Resolve conflicts between biological detail, clinical generality, and machine encodability.
4. Enforce leakage-control constraints.
5. Maintain the iteration record and schema version.
6. Stop the process when convergence criteria are satisfied.
