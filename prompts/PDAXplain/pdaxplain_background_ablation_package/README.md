# PDAXplain Background-Knowledge Dependence Analysis

This package runs the small input-ablation analysis for PDAXplain:

- Setting A: prediction score + piRNA name + disease description only
- Setting B: Setting A + manually curated background knowledge

## 1. Install dependencies

```bash
pip install openai python-docx pandas numpy scikit-learn
```

Only `openai` and `python-docx` are required for the main script. The other packages are optional if you later extend the analysis.

## 2. Set API key

```bash
export OPENAI_API_KEY="your_api_key"
```

Do not place your API key in the manuscript, supplementary files, or GitHub repository.

## 3. Run the A vs B analysis on your two DOCX examples

```bash
python scripts/pdaxplain_background_ablation.py \
  --docx hsa_piR_004153_3.docx hsa_piR_000823.docx \
  --prompt prompts/pdaxplain_ablation_prompt_template.txt \
  --outdir results_bg_ablation \
  --report-dir reports_bg_ablation \
  --model gpt-5.5 \
  --n-runs 3 \
  --settings A B \
  --audit-mode llm \
  --temperature 0.2 \
  --input-price-per-m 5.00 \
  --output-price-per-m 22.50
```

Update `--input-price-per-m` and `--output-price-per-m` according to the pricing page at the time of your experiment. If you only want token/latency logs without cost estimates, set both prices to `0`.

## 4. Run A/B if you have review summaries and retrieved snippets

The extracted JSON file in `examples/two_pdaxplain_cases_extracted.json` contains automatically extracted fields from your two DOCX examples.

Then run:

```bash
python scripts/pdaxplain_background_ablation.py \
  --input examples/two_pdaxplain_cases_extracted.json \
  --prompt prompts/pdaxplain_ablation_prompt_template.txt \
  --outdir results_bg_ablation_abcd \
  --report-dir reports_bg_ablation_abcd \
  --model gpt-5.5 \
  --n-runs 3 \
  --settings A B \
  --skip-missing-optional-settings \
  --audit-mode llm \
  --temperature 0.2 \
  --input-price-per-m 5.00 \
  --output-price-per-m 22.50
```

## 5. Output files

The script writes:

- `reports_bg_ablation/<case_id>/setting_A/run_1.md` etc.  
  Full generated PDAXplain reports.
- `results_bg_ablation/background_dependence_report_runs.csv`  
  Run-level metrics and token/latency/cost logs.
- `results_bg_ablation/background_dependence_audit_long.csv`  
  Report-level audit metrics.
- `results_bg_ablation/background_dependence_case_setting_summary.csv`  
  Case-setting-level means across repeated runs.
- `results_bg_ablation/background_dependence_summary_by_setting.csv`  
  Main Supplementary Table Sx.8 values.
- `results_bg_ablation/background_dependence_cost_latency_summary.csv`  
  Cost and latency by setting and call type.
- `results_bg_ablation/background_dependence_cases_used.json`  
  The exact parsed input cases used in the experiment.

## 6. Recommended wording for Supplementary Methods

Use the results in `Sx8_background_knowledge_dependence_table.md` as the main table. Interpret Setting B as improved only if it increases direct evidence-supported claims and mechanistic specificity and/or reduces unsupported-claim rate compared with Setting A. Do not interpret PDAXplain reports as experimental validation.
