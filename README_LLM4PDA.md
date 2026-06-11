# LLM4PDA: Large-language-model-augmented piRNA–disease association prediction

> Anonymous peer-review code archive. Author identities, affiliations, and non-anonymized repository metadata are intentionally omitted during double-blind review. The repository will be made public after acceptance.

## Overview

LLM4PDA is a framework for piRNA–disease association (PDA) prediction. It combines:

1. RNA-FM-derived RNA sequence embeddings for piRNAs or tRNAs;
2. disease semantic embeddings generated from fixed piPromptLab disease descriptions;
3. a lightweight MLP-based feature-alignment module followed by inner-product association scoring;
4. fold-specific positive–unlabeled learning (PUL) reliable-negative selection; and
5. PDAXplain, a separate post-prediction reporting workflow for generating structured, evidence-aware biological hypothesis summaries.

The predictive experiments can be reproduced using the released processed datasets, cached RNA/disease embeddings, fixed cross-validation splits, and precomputed reliable-negative files. No additional LLM API calls are required when the cached descriptions and embeddings are used.

## Repository structure

```text
.
├── data/                         # Main MNDR4.0 piRNA-disease benchmark files
├── data_piRDisease/              # Independent piRDisease v1.0 benchmark files, if provided separately
├── feat/                         # Disease-description generation and embedding-generation scripts; cached embeddings
│   ├── desc_generate.py
│   ├── dis_emb_generate_full_pipromptlab.py
│   ├── dis_emb_to_pkl.py
│   ├── piRNA_embeddings.ipynb
│   ├── piRNA_name.csv
│   └── LLM_piRNA_emb.zip         # Contains cached LLM_piRNA_emb.pkl and LLM_disease_emb.pkl
├── LLM4PDA/                      # Main LLM4PDA model, training loop, and evaluation logger
├── spy/                          # Spy-based reliable-negative generation script and cached reliable negatives
├── pu_bagging/                   # PU-bagging reliable-negative generation script and cached reliable negatives
├── two_step/                     # Two-step PU reliable-negative generation script and cached reliable negatives
├── ETGPDA/                       # Baseline implementation or wrapper
├── iPiDA-GCN/                    # Baseline implementation or wrapper
├── iPiDA-SWGCN/                  # Baseline implementation or wrapper
├── iPiDA-GBNN/                   # Baseline implementation or wrapper
├── iPiDi-PUL/                    # Baseline implementation or wrapper
├── piRDA/                        # Baseline implementation or wrapper
├── PUTransGCN_comb_5/            # Baseline implementation or wrapper
├── MambaCAttnGCN/                # Baseline implementation or wrapper
├── tRNA-disease_LLM4PDA/         # Cross-RNA-type tRNA-disease evaluation code
└── prompts/
    ├── piPromptLab/              # piPromptLab role prompts, supervisor rules, peer-evaluation criteria, and schema records
    └── PDAXplain/                # PDAXplain prompt templates, example reports, and audit packages
```

## Required processed data files

For exact reproduction, the following files should be present after extracting the released data package at the repository root:

```text
data/adj.csv
data/doid.csv
data/piRNA_seq.csv
data/p2p_smith.csv
data/d2d_do.csv
data/fold_info.pickle
feat/LLM_piRNA_emb.pkl
feat/LLM_disease_emb.pkl
spy/rn_ij_list_5.pickle
pu_bagging/rn_ij_list.pickle
two_step/rn_ij_list.pickle
```

For the tRNA cross-RNA-type evaluation, the expected files include:

```text
tRNA-disease_LLM4PDA/data/adj.csv
tRNA-disease_LLM4PDA/data/doid.csv
tRNA-disease_LLM4PDA/data/tRNA_seq.csv
tRNA-disease_LLM4PDA/data/tRNA_name.csv
tRNA-disease_LLM4PDA/data/p2p_smith.csv
tRNA-disease_LLM4PDA/data/d2d_do.csv
tRNA-disease_LLM4PDA/data/LLM_tRNA_emb.pkl
tRNA-disease_LLM4PDA/data/LLM_disease_emb_tRNA.pkl
tRNA-disease_LLM4PDA/data/data_*/fold_info.pickle
```

Raw source data were obtained from public resources described in the manuscript and Supplementary Material. The file `data/Readme.txt` provides the raw-data source link used during preprocessing. The processed files listed above are the exact files required by the released scripts.

## Installation

The code was developed with Python 3.10 and PyTorch. A CUDA-enabled GPU is recommended because the main scripts currently use `torch.device("cuda")`.

```bash
conda create -n llm4pda python=3.10 -y
conda activate llm4pda

pip install numpy pandas scikit-learn scipy matplotlib openpyxl tqdm networkx obonet minineedle openai
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

Some baseline models may additionally require:

```bash
pip install torch-geometric
pip install mamba-ssm
```

RNA-FM embedding extraction requires the RNA-FM dependencies used by the official RNA-FM implementation. If using the released cached RNA embeddings, RNA-FM installation is not required for reproducing the reported prediction results.

## Before running the main model

If cached files are distributed as compressed archives, extract them first:

```bash
unzip feat/LLM_piRNA_emb.zip -d feat/
unzip spy/rn_ij_list_5.zip -d spy/
unzip pu_bagging/rn_ij_list.zip -d pu_bagging/
unzip two_step/rn_ij_list.zip -d two_step/
```

Then check that the expected files exist:

```bash
python - <<'PY'
from pathlib import Path
required = [
    'data/adj.csv',
    'data/doid.csv',
    'data/p2p_smith.csv',
    'data/d2d_do.csv',
    'data/fold_info.pickle',
    'feat/LLM_piRNA_emb.pkl',
    'feat/LLM_disease_emb.pkl',
    'spy/rn_ij_list_5.pickle',
    'pu_bagging/rn_ij_list.pickle',
    'two_step/rn_ij_list.pickle',
]
missing = [p for p in required if not Path(p).exists()]
if missing:
    print('Missing files:')
    for p in missing:
        print('  -', p)
    raise SystemExit(1)
print('All required files are present.')
PY
```

## Reproducing the main LLM4PDA experiment

Run from the `LLM4PDA/` directory because relative paths are used in the scripts:

```bash
cd LLM4PDA
python main.py
```

The script writes per-epoch prediction scores to:

```text
LLM4PDA/scores/
```

and writes fold-level metrics to:

```text
LLM4PDA/LLM4PDA_comb_5.xlsx
```

The reported cross-validation performance is obtained by averaging the final five epochs of each fold and then summarizing across the five folds.

## Reproducing PUL reliable-negative files

The released predictive experiments use precomputed fold-specific reliable-negative files:

```text
spy/rn_ij_list_5.pickle
pu_bagging/rn_ij_list.pickle
two_step/rn_ij_list.pickle
```

These files are used directly by `LLM4PDA/main.py`. Regeneration scripts are provided in `spy/`, `pu_bagging/`, and `two_step/`. Regeneration requires the same processed similarity matrices, cross-validation splits, and random seed settings used in the manuscript. If auxiliary random-forest classifiers are not included, uncomment or enable the classifier-training blocks in the corresponding scripts before rerunning the reliable-negative generation step.

## Disease-description and embedding generation

The reported predictive experiments should use the released cached disease descriptions and embeddings. Regeneration is optional and will require access to an OpenAI-compatible API.

Disease-description generation:

```bash
cd feat
python desc_generate.py \
  --input_csv ../data/doid.csv \
  --output_csv disease_descriptions.csv \
  --api_key_path key.txt \
  --model_id <MODEL_ID_REPORTED_IN_THE_MANUSCRIPT>
```

Disease embedding generation:

```bash
python dis_emb_generate_full_pipromptlab.py
python dis_emb_to_pkl.py
```

For reproducibility and double-blind review, API keys should never be committed. Use local environment variables or local ignored key files.

## Reproducing baseline experiments

Baseline implementations or wrappers are provided in separate folders. Each baseline should be run from its own folder so that relative paths resolve correctly:

```bash
cd ETGPDA && python main.py
cd ../iPiDA-GCN && python main.py
cd ../iPiDA-SWGCN && python main.py
cd ../iPiDA-GBNN && python main.py
cd ../piRDA && python main.py
cd ../PUTransGCN_comb_5 && python main.py
cd ../MambaCAttnGCN && python main.py
```

The iPiDi-PUL variants are run separately:

```bash
cd iPiDi-PUL
python main_dt.py
python main_rf.py
python main_svm.py
```

## Cross-RNA-type tRNA evaluation

Run from `tRNA-disease_LLM4PDA/LLM4PDA/` and provide the target fold file:

```bash
cd tRNA-disease_LLM4PDA/LLM4PDA
python main.py ../data/data_1/fold_info.pickle
```

For repeated runs, use the provided shell scripts after confirming that the required `data_*` folders and cached embeddings are present.

## PDAXplain report generation and audit

PDAXplain is a post-prediction reporting workflow and is not part of the neural prediction model. The main resources are located in:

```text
prompts/PDAXplain/
```

For the 20 predictions x 3 repeated-generation audit:

```bash
cd prompts/PDAXplain/pdaxplain_20x3_package
python pdaxplain_batch_runner.py \
  --input pdaxplain_20_predictions.csv \
  --prompt prompts/pdaxplain_prompt_template.txt \
  --outdir results \
  --report_dir reports \
  --model <MODEL_ID> \
  --temperature 0.2 \
  --n_runs 3 \
  --audit_mode llm \
  --use_openai_embeddings \
  --embedding_model text-embedding-3-small
```

For the background-knowledge dependence analysis:

```bash
cd prompts/PDAXplain/pdaxplain_background_ablation_package
python scripts/pdaxplain_background_ablation.py \
  --input examples/two_pdaxplain_cases_extracted.json \
  --prompt prompts/pdaxplain_ablation_prompt_template.txt \
  --outdir results_bg_ablation \
  --report-dir reports_bg_ablation \
  --model <MODEL_ID> \
  --n-runs 3 \
  --settings A B \
  --audit-mode llm \
  --temperature 0.2
```

## piPromptLab documentation

The piPromptLab folder documents the schema-construction protocol rather than a runtime model component. It includes domain-agent role definitions, initial prompts, supervisor rules, information-transfer rules, peer-evaluation criteria, stopping criteria, a representative iteration record, and a machine-readable protocol file.

```text
prompts/piPromptLab/
```

The final schema is fixed before model training, and the cached disease descriptions and embeddings allow downstream prediction experiments to be reproduced without rerunning the human-mediated schema-construction process.

## Double-blind and security notes

Before pushing to the anonymous review repository:

1. remove all API keys, including any `*key*.txt` files;
2. remove `__pycache__/`, `*.pyc`, local logs, and non-anonymized metadata;
3. make sure Git commit metadata does not reveal author identities;
4. use an anonymous repository name and anonymous account during peer review;
5. provide large processed files through the anonymous repository release assets or another anonymized data archive if they are too large for GitHub; and
6. keep the public repository link inactive or private until the journal permits public release.

Recommended `.gitignore` entries:

```gitignore
__pycache__/
*.pyc
*.pyo
.ipynb_checkpoints/
.DS_Store
.env
*key*.txt
*.log
scores/
```

## Citation

This repository accompanies the manuscript:

```text
LLM4PDA: Augmenting piRNA-Disease Association Prediction with Large Language Models
```

The full citation will be added after acceptance.
