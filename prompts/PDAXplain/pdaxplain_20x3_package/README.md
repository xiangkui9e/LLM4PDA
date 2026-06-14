# PDAXplain 20 x 3 batch generation and audit package

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

## Expected outputs

- 60 raw reports: 20 predictions x 3 repeats in `reports/`
- `results/report_runs.csv`
- `results/consistency_by_prediction.csv`
- `results/consistency_summary.csv`
- `results/claim_audit_long.csv`
- `results/claim_evidence_support.csv`
- `results/pdaxplain_20x3_results.xlsx`
