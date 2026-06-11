# PDAXplain 20 x 3 batch generation and audit package

This package is prepared for the reviewer-requested PDAXplain inter-report consistency analysis.

## What is included

- `pdaxplain_20_predictions.csv`
- `pdaxplain_20_predictions_input.xlsx`
- `prompts/pdaxplain_prompt_template.txt`
- `pdaxplain_batch_runner.py`
- `reports/` for raw generated reports
- `results/` for output tables

The 20 candidate predictions are selected from the submitted manuscript case-study tables:
1. Fifteen disease-masking predictions from Table 4.
2. Five top-ranked DQ598677 piRNA-masking predictions from Table 5.

## Important limitation before final run

Several rows do not yet contain `piRNA_sequence` or full `disease_description` because these fields were not present in the uploaded summary table. For the most rigorous final run, fill those columns from your released processed resources before running the script.

The script still works if those fields are blank, but the generated reports will be less specific and should be described as "evidence-summary reports based on prediction metadata and post hoc evidence" rather than full PDAXplain reports.

## How to run

Install dependencies:

```bash
pip install openai pandas numpy scikit-learn openpyxl
```

Set your OpenAI API key locally. Do not share it.

Linux/macOS:

```bash
export OPENAI_API_KEY="sk-..."
```

Windows PowerShell:

```powershell
setx OPENAI_API_KEY "sk-..."
```

Run:

```bash
python pdaxplain_batch_runner.py \
  --input pdaxplain_20_predictions.csv \
  --prompt prompts/pdaxplain_prompt_template.txt \
  --outdir results \
  --report_dir reports \
  --model gpt-5.5 \
  --temperature 0.2 \
  --n_runs 3 \
  --audit_mode llm \
  --use_openai_embeddings \
  --embedding_model text-embedding-3-small
```

If your account uses a different GPT-5.5 API model identifier, replace `--model gpt-5.5`.

## Expected outputs

- 60 raw reports: 20 predictions x 3 repeats in `reports/`
- `results/report_runs.csv`
- `results/consistency_by_prediction.csv`
- `results/consistency_summary.csv`
- `results/claim_audit_long.csv`
- `results/claim_evidence_support.csv`
- `results/pdaxplain_20x3_results.xlsx`

## Recommended manuscript sentence

Repeated generation of PDAXplain reports for 20 high-confidence predictions showed high structural completion and semantic consistency under a fixed prompt template. Claim-level auditing further classified factual statements into directly supported, indirectly supported, hypothesis-level, and unsupported categories, providing a transparent estimate of evidence grounding and unsupported-claim risk.