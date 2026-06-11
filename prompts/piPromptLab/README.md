# piPromptLab Reproducibility Materials

This folder documents the **schema-construction stage** of piPromptLab. It is intended to support transparency and reviewer evaluation of the human-mediated prompt-schema development process.

## Important reproducibility boundary

piPromptLab was used to develop a frozen disease-description schema. It was **not** used as a runtime component of model training or inference.

The present materials document how the schema was constructed, including agent roles, initial prompts, supervisor rules, information-transfer rules, peer-evaluation criteria, stopping criteria, and a representative schema-refinement record.

## Files

| File | Purpose |
|---|---|
| `agent_roles.md` | Defines the three domain-specialized agents |
| `agent_initial_prompts.md` | Provides the initial prompts used for schema generation and critique |
| `supervisor_rules.md` | Documents the human supervisor's filtering, merging, routing, and conflict-resolution rules |
| `information_transfer_rules.md` | Defines what information should be retained, revised, merged, downgraded, or removed |
| `peer_evaluation_criteria.md` | Provides the review rubric used by non-speaking agents |
| `stopping_criteria.md` | Defines convergence criteria for freezing the schema |
| `example_iteration_record.md` | Provides a representative schema-refinement iteration |
| `schema_evolution_table.csv` | Provides a compact schema-evolution audit table |
| `audit_record_template.csv` | Template for adding real raw-session evidence if available |
| `schema_construction_protocol.json` | Machine-readable version of the protocol |
| `supplementary_text_ready_to_use.md` | Manuscript-ready supplementary text and tables |

