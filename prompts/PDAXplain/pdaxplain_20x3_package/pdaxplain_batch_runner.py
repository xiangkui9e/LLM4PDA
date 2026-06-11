
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDAXplain 20 x 3 batch generator and audit script.

What it does
------------
1. Reads pdaxplain_20_predictions.csv.
2. Generates 3 PDAXplain reports per prediction using the OpenAI API.
3. Saves all raw reports as Markdown files.
4. Computes inter-report consistency metrics:
   - section completion rate
   - key-claim overlap
   - semantic similarity
   - recommendation consistency
   - contradiction rate
5. Optionally performs LLM-based claim-level evidence support audit.
6. Writes CSV and XLSX tables for supplementary materials, including token/cost estimates.

Before running
--------------
pip install openai pandas numpy scikit-learn openpyxl

Set your API key locally. Do NOT paste it into the script.
Linux/macOS:
    export OPENAI_API_KEY="sk-..."
Windows PowerShell:
    setx OPENAI_API_KEY "sk-..."

Recommended command:
    python pdaxplain_batch_runner.py \
      --input pdaxplain_20_predictions.csv \
      --prompt prompts/pdaxplain_prompt_template.txt \
      --outdir results \
      --report_dir reports \
      --model openai/gpt-5.5 \
      --temperature 0.2 \
      --n_runs 3 \
      --audit_mode llm \
      --embedding_model text-embedding-3-small \
      --input_price_per_1M 2.50 \
      --output_price_per_1M 10.00

Notes
-----
- If using OpenRouter, set OPENROUTER_API_KEY (or OPENAI_API_KEY) and ensure --model uses the OpenRouter prefix (e.g. openai/gpt-5.5).
- Exact token accounting and latency are read from API responses when available.
- If the Responses API is unavailable in your SDK/model, the script falls back to Chat Completions.
- Cost estimation requires --input_price_per_1M and --output_price_per_1M (USD). You can also set PDAXPLAIN_INPUT_PRICE and PDAXPLAIN_OUTPUT_PRICE env vars.
"""

import argparse
import csv
import itertools
import json
import math
import os
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from openai import OpenAI
except Exception as e:
    print("The openai package is required. Install with: pip install openai", file=sys.stderr)
    raise

SECTION_TITLES = [
    "Biological plausibility",
    "Potential mechanisms",
    "Literature or database support",
    "Credibility assessment",
    "Experimental validation suggestions",
    "Summary statement",
]

VALIDATION_KEYWORDS = [
    "qRT-PCR", "RT-qPCR", "qPCR", "northern blot", "small RNA sequencing", "RNA-seq",
    "expression", "clinical sample", "paired tumor", "plasma", "serum", "sperm",
    "RIP", "CLIP", "PIWI", "HIWI", "immunoprecipitation",
    "mimic", "inhibitor", "antagomir", "knockdown", "overexpression",
    "proliferation", "migration", "invasion", "apoptosis", "cell cycle",
    "luciferase", "target", "rescue", "functional assay", "cohort",
]

PROMPT_TEMPLATE_DEFAULT = """You are a rigorous biology and bioinformatics expert. Evaluate the following predicted piRNA–disease association as a cautious, post-prediction biological report.

IMPORTANT RULES:
- Do not fabricate references, database identifiers, genes, pathways, targets, or mechanisms.
- If reliable information is unavailable, explicitly state "No reliable information is available" or "Uncertain".
- Mechanistic inference must be based on known piRNA/PIWI biology, related family/sequence evidence, or supplied curated evidence.
- The prediction probability is only a model-derived score and must not be treated as biological evidence.
- Use conservative language, such as "may", "could", "hypothesis", and "requires validation".
- Clearly distinguish direct evidence, indirect evidence, hypothesis-level interpretation, and unsupported/unavailable information.

INPUT:
piRNA name: {piRNA_name}
piRNA aliases: {piRNA_aliases}
piRNA sequence: {piRNA_sequence}
Disease name: {disease_name}
Disease description: {disease_description}
Predicted association probability: {prediction_score}
Post hoc supporting evidence: {evidence}
Evidence category: {evidence_level}
Curated background knowledge: {curated_background_knowledge}

OUTPUT:
Write a structured report with exactly the following six sections. Use the section titles verbatim.

1. Biological plausibility
Discuss whether the piRNA, its known/related expression, or general piRNA/PIWI biology could plausibly relate to the disease. Explicitly state missing information.

2. Potential mechanisms
Provide cautious possible mechanisms only when supported by supplied evidence or general piRNA/PIWI biology. If no reliable mechanism is available, state this clearly.

3. Literature or database support
List direct and indirect evidence. Mention the supplied PMID/database evidence, and explicitly state whether it supports the exact piRNA–disease pair or only indirect/contextual evidence.

4. Credibility assessment
Assign one of: High, Medium, Medium-low, Low. Explain why. Do not use the prediction score alone as evidence.

5. Experimental validation suggestions
Suggest feasible validation experiments and expected observations, starting with expression validation and then mechanism/function assays if appropriate.

6. Summary statement
Provide a conservative integrative conclusion and clearly state that the report is hypothesis-oriented rather than experimental validation."""

def load_prompt(path):
    if path:
        return Path(path).read_text(encoding="utf-8")
    return PROMPT_TEMPLATE_DEFAULT

def load_api_key(key_file):
    key_path = Path(key_file)
    if key_path.exists():
        lines = [line.strip() for line in key_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if lines:
            return lines[0]
    return None

def safe_str(x):
    if x is None:
        return ""
    if isinstance(x, float) and math.isnan(x):
        return ""
    return str(x)

def build_prompt(template, row):
    record = {k: safe_str(v) for k, v in row.items()}
    # Ensure all expected fields exist.
    fields = [
        "piRNA_name", "piRNA_aliases", "piRNA_sequence", "disease_name", "disease_description",
        "prediction_score", "evidence", "evidence_level", "curated_background_knowledge",
    ]
    for f in fields:
        record.setdefault(f, "")
    return template.format(**record)

def call_openai_text(client, model, prompt, temperature=0.2, max_output_tokens=None):
    start = time.time()
    usage = {}
    try:
        kwargs = {
            "model": model,
            "input": [
                {"role": "system", "content": [{"type": "input_text", "text": "You are a careful biomedical reporting assistant. Follow the user's anti-hallucination constraints exactly."}]},
                {"role": "user", "content": [{"type": "input_text", "text": prompt}]},
            ],
            "temperature": temperature,
        }
        if max_output_tokens:
            kwargs["max_output_tokens"] = max_output_tokens
        resp = client.responses.create(**kwargs)
        text = getattr(resp, "output_text", None)
        if text is None:
            # Robust extraction.
            chunks = []
            for item in getattr(resp, "output", []) or []:
                for content in getattr(item, "content", []) or []:
                    if getattr(content, "text", None):
                        chunks.append(content.text)
            text = "\n".join(chunks)
        u = getattr(resp, "usage", None)
        if u is not None:
            usage = {
                "input_tokens": getattr(u, "input_tokens", None) or getattr(u, "prompt_tokens", None),
                "output_tokens": getattr(u, "output_tokens", None) or getattr(u, "completion_tokens", None),
                "total_tokens": getattr(u, "total_tokens", None),
            }
        return text, usage, time.time() - start
    except Exception as responses_error:
        # Fallback for older SDK/model routes.
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a careful biomedical reporting assistant. Follow anti-hallucination constraints exactly."},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
        )
        text = resp.choices[0].message.content
        u = getattr(resp, "usage", None)
        if u is not None:
            usage = {
                "input_tokens": getattr(u, "prompt_tokens", None),
                "output_tokens": getattr(u, "completion_tokens", None),
                "total_tokens": getattr(u, "total_tokens", None),
            }
        return text, usage, time.time() - start

def compute_cost(input_tokens, output_tokens, input_price_per_1M, output_price_per_1M):
    if input_tokens is None or output_tokens is None:
        return None
    try:
        it = float(input_tokens)
        ot = float(output_tokens)
    except (ValueError, TypeError):
        return None
    if math.isnan(it) or math.isnan(ot):
        return None
    return round((it / 1_000_000) * input_price_per_1M + (ot / 1_000_000) * output_price_per_1M, 6)

def section_flags(text):
    flags = {}
    lower = text.lower()
    for title in SECTION_TITLES:
        flags[title] = 1 if title.lower() in lower else 0
    return flags

def extract_section(text, title):
    # Supports numbered headings and exact title.
    escaped = re.escape(title)
    pattern = re.compile(rf"(?:^|\n)\s*(?:\d+\.\s*)?{escaped}\s*(?:\n|:)(.*?)(?=\n\s*(?:\d+\.\s*)?(?:{'|'.join(map(re.escape, SECTION_TITLES))})\s*(?:\n|:)|\Z)", re.I | re.S)
    m = pattern.search(text)
    return m.group(1).strip() if m else ""

def tokenize_terms(text):
    words = re.findall(r"[A-Za-z][A-Za-z0-9_\-]{2,}", text.lower())
    stop = set("the and for with that this from are was were have has into only when while may could should would disease pirna pirnas association evidence report".split())
    return set(w for w in words if w not in stop)

def jaccard(a, b):
    a, b = set(a), set(b)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)

def extract_recommendation_terms(text):
    sec = extract_section(text, "Experimental validation suggestions")
    terms = []
    for kw in VALIDATION_KEYWORDS:
        if kw.lower() in sec.lower():
            terms.append(kw.lower())
    return set(terms)

def heuristic_key_claim_terms(text):
    # Extract from the first four sections but remove generic terms.
    relevant = "\n".join([
        extract_section(text, "Biological plausibility"),
        extract_section(text, "Potential mechanisms"),
        extract_section(text, "Literature or database support"),
        extract_section(text, "Credibility assessment"),
    ])
    return tokenize_terms(relevant)

def tfidf_cosine(texts):
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        X = TfidfVectorizer(stop_words="english", max_features=5000).fit_transform(texts)
        sim = cosine_similarity(X)
        return sim
    except Exception:
        # Simple bag-of-words cosine fallback.
        vocab = sorted(set().union(*(tokenize_terms(t) for t in texts)))
        if not vocab:
            return np.eye(len(texts))
        idx = {w:i for i,w in enumerate(vocab)}
        mat = np.zeros((len(texts), len(vocab)))
        for i,t in enumerate(texts):
            c = Counter(re.findall(r"[A-Za-z][A-Za-z0-9_\-]{2,}", t.lower()))
            for w,n in c.items():
                if w in idx:
                    mat[i,idx[w]] = n
        norms = np.linalg.norm(mat, axis=1)
        norms[norms == 0] = 1
        mat = mat / norms[:, None]
        return mat @ mat.T

def embed_texts_openai(client, model, texts):
    # Batches texts for OpenAI embeddings.
    resp = client.embeddings.create(model=model, input=texts)
    vecs = [np.array(item.embedding, dtype=float) for item in resp.data]
    mat = np.vstack(vecs)
    norms = np.linalg.norm(mat, axis=1)
    norms[norms == 0] = 1
    mat = mat / norms[:, None]
    return mat @ mat.T

def mean_pairwise_from_similarity(sim):
    vals = []
    for i, j in itertools.combinations(range(sim.shape[0]), 2):
        vals.append(float(sim[i, j]))
    return float(np.mean(vals)) if vals else None

def simple_contradiction_rate(texts):
    # Conservative heuristic. For publishable values, prefer audit_mode=llm.
    pairs = list(itertools.combinations(range(len(texts)), 2))
    if not pairs:
        return 0.0
    contradictions = 0
    for i, j in pairs:
        a, b = texts[i].lower(), texts[j].lower()
        up_down = (("upregulated" in a and "downregulated" in b) or ("downregulated" in a and "upregulated" in b))
        high_low = (("high credibility" in a and "low credibility" in b) or ("low credibility" in a and "high credibility" in b))
        if up_down or high_low:
            contradictions += 1
    return contradictions / len(pairs)

def parse_json_safely(text):
    text = text.strip()
    m = re.search(r"```json\s*(.*?)```", text, re.S | re.I)
    if m:
        text = m.group(1).strip()
    else:
        m = re.search(r"(\{.*\}|\[.*\])", text, re.S)
        if m:
            text = m.group(1)
    return json.loads(text)

def llm_claim_audit(client, model, report_text, evidence, disease, pirna):
    prompt = f"""
You are auditing a PDAXplain biomedical report for evidence grounding.

Candidate: {pirna} -- {disease}
Supplied evidence/background:
{evidence}

Report:
{report_text}

Task:
Extract 8-15 factual or mechanistic claims from the report and classify each claim into exactly one category:
- directly_supported: exact piRNA-disease or expression claim supported by supplied PMID/database evidence.
- indirectly_supported: supported by related piRNA/PIWI/disease biology or contextual literature, but not direct evidence for the exact pair.
- hypothesis_level: explicitly speculative or proposed as a hypothesis requiring validation.
- unsupported_or_unverifiable: no identifiable support from supplied evidence/background.
- contradictory: conflicts with supplied evidence.

Return valid JSON only:
{{
  "claims":[{{"claim":"...", "category":"...", "reason":"..."}}],
  "contradiction_count": 0
}}
"""
    text, usage, latency = call_openai_text(client, model, prompt, temperature=0.0)
    try:
        data = parse_json_safely(text)
    except Exception:
        data = {"claims": [], "contradiction_count": None, "raw_audit_response": text}
    return data, usage, latency

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="pdaxplain_20_predictions.csv")
    ap.add_argument("--prompt", default="prompts/pdaxplain_prompt_template.txt")
    ap.add_argument("--outdir", default="results")
    ap.add_argument("--report_dir", default="reports")
    ap.add_argument("--model", default=os.getenv("PDAXPLAIN_MODEL", "openai/gpt-5.5"))
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--n_runs", type=int, default=3)
    ap.add_argument("--max_output_tokens", type=int, default=None)
    ap.add_argument("--input_price_per_1M", type=float, default=float(os.getenv("PDAXPLAIN_INPUT_PRICE", "0.0")),
                    help="Price per 1 million input tokens (USD), e.g. 2.50 for $2.50/M input tokens.")
    ap.add_argument("--output_price_per_1M", type=float, default=float(os.getenv("PDAXPLAIN_OUTPUT_PRICE", "0.0")),
                    help="Price per 1 million output tokens (USD), e.g. 10.00 for $10.00/M output tokens.")
    ap.add_argument("--audit_mode", choices=["none", "heuristic", "llm"], default="llm")
    ap.add_argument("--embedding_model", default=os.getenv("PDAXPLAIN_EMBEDDING_MODEL", "text-embedding-3-small"))
    ap.add_argument("--use_openai_embeddings", action="store_true", help="Use OpenAI embeddings for semantic similarity. Otherwise use TF-IDF fallback.")
    ap.add_argument("--key_file", default="openrouter_key.txt",
                    help="Path to a file containing the API key (read from first non-empty line).")
    args = ap.parse_args()

    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    report_dir = Path(args.report_dir); report_dir.mkdir(parents=True, exist_ok=True)
    prompt_template = load_prompt(args.prompt)

    df = pd.read_csv(args.input)
    api_key = load_api_key(args.key_file) or os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: No API key found. Provide one via:", file=sys.stderr)
        print("  1. --key_file <path> (default: openrouter_key.txt)", file=sys.stderr)
        print("  2. Environment variable OPENROUTER_API_KEY or OPENAI_API_KEY", file=sys.stderr)
        sys.exit(1)
    client = OpenAI(
        base_url=os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1"),
        api_key=api_key,
    )

    run_rows = []
    all_reports = defaultdict(list)
    claim_rows = []
    audit_usage_rows = []

    for _, row in df.iterrows():
        rec = row.to_dict()
        record_id = safe_str(rec.get("record_id"))
        pirna = safe_str(rec.get("piRNA_name"))
        disease = safe_str(rec.get("disease_name"))
        prompt = build_prompt(prompt_template, rec)
        prompt_path = outdir / f"{record_id}_{pirna}_{disease}_prompt.txt".replace("/", "_").replace(" ", "_")
        prompt_path.write_text(prompt, encoding="utf-8")

        for run_idx in range(1, args.n_runs + 1):
            print(f"Generating {record_id} run {run_idx}/{args.n_runs}: {pirna} -- {disease}")
            report, usage, latency = call_openai_text(client, args.model, prompt, temperature=args.temperature, max_output_tokens=args.max_output_tokens)
            fname = f"{record_id}_{pirna}_{disease}_run{run_idx}.md".replace("/", "_").replace(" ", "_")
            fpath = report_dir / fname
            fpath.write_text(report, encoding="utf-8")
            flags = section_flags(report)
            completion_rate = sum(flags.values()) / len(SECTION_TITLES)
            report_cost = compute_cost(usage.get("input_tokens"), usage.get("output_tokens"), args.input_price_per_1M, args.output_price_per_1M)
            run_row = {
                "record_id": record_id,
                "piRNA_name": pirna,
                "disease_name": disease,
                "run": run_idx,
                "report_file": str(fpath),
                "section_completion_rate": completion_rate,
                "input_tokens": usage.get("input_tokens"),
                "output_tokens": usage.get("output_tokens"),
                "total_tokens": usage.get("total_tokens"),
                "latency_seconds": latency,
                "cost_usd": report_cost,
            }
            for sec, flag in flags.items():
                run_row[f"section_present__{sec}"] = flag
            run_rows.append(run_row)
            all_reports[record_id].append({"text": report, "file": str(fpath), "row": rec, "run": run_idx})

            if args.audit_mode == "llm":
                evidence_text = "\n".join([
                    safe_str(rec.get("evidence")),
                    safe_str(rec.get("evidence_level")),
                    safe_str(rec.get("curated_background_knowledge")),
                ])
                audit_data, audit_usage, audit_latency = llm_claim_audit(client, args.model, report, evidence_text, disease, pirna)
                audit_cost = compute_cost(audit_usage.get("input_tokens"), audit_usage.get("output_tokens"), args.input_price_per_1M, args.output_price_per_1M)
                audit_usage_rows.append({
                    "record_id": record_id, "run": run_idx, "audit_input_tokens": audit_usage.get("input_tokens"),
                    "audit_output_tokens": audit_usage.get("output_tokens"), "audit_total_tokens": audit_usage.get("total_tokens"),
                    "audit_latency_seconds": audit_latency,
                    "audit_contradiction_count": audit_data.get("contradiction_count"),
                    "audit_cost_usd": audit_cost,
                })
                for c in audit_data.get("claims", []):
                    claim_rows.append({
                        "record_id": record_id,
                        "piRNA_name": pirna,
                        "disease_name": disease,
                        "run": run_idx,
                        "claim": c.get("claim"),
                        "category": c.get("category"),
                        "reason": c.get("reason"),
                    })

    # Save per-run data.
    runs_df = pd.DataFrame(run_rows)
    runs_df.to_csv(outdir / "report_runs.csv", index=False, encoding="utf-8-sig")

    consistency_rows = []
    for record_id, items in all_reports.items():
        texts = [x["text"] for x in items]
        rec = items[0]["row"]
        pairs = list(itertools.combinations(range(len(texts)), 2))

        # Key claim overlap.
        key_sets = [heuristic_key_claim_terms(t) for t in texts]
        key_pair_vals = [jaccard(key_sets[i], key_sets[j]) for i,j in pairs]
        key_overlap = float(np.mean(key_pair_vals)) if key_pair_vals else None

        # Semantic similarity.
        if args.use_openai_embeddings:
            try:
                sim = embed_texts_openai(client, args.embedding_model, texts)
            except Exception as e:
                print(f"OpenAI embedding failed for {record_id}; using TF-IDF fallback: {e}")
                sim = tfidf_cosine(texts)
        else:
            sim = tfidf_cosine(texts)
        semantic_similarity = mean_pairwise_from_similarity(sim)

        # Recommendation consistency.
        rec_sets = [extract_recommendation_terms(t) for t in texts]
        rec_pair_vals = [jaccard(rec_sets[i], rec_sets[j]) for i,j in pairs]
        recommendation_consistency = float(np.mean(rec_pair_vals)) if rec_pair_vals else None

        # Contradiction rate.
        if args.audit_mode == "llm" and audit_usage_rows:
            ccounts = [r["audit_contradiction_count"] for r in audit_usage_rows if r["record_id"] == record_id and r["audit_contradiction_count"] is not None]
            contradiction_rate = float(np.mean([1 if c > 0 else 0 for c in ccounts])) if ccounts else simple_contradiction_rate(texts)
        else:
            contradiction_rate = simple_contradiction_rate(texts)

        sub = runs_df[runs_df["record_id"] == record_id]
        total_report_cost = float(sub["cost_usd"].dropna().sum()) if sub["cost_usd"].notna().any() else None
        audit_sub = pd.DataFrame(audit_usage_rows)
        if len(audit_sub):
            total_audit_cost = float(audit_sub[audit_sub["record_id"] == record_id]["audit_cost_usd"].dropna().sum()) if "audit_cost_usd" in audit_sub.columns else None
        else:
            total_audit_cost = None
        consistency_rows.append({
            "record_id": record_id,
            "piRNA_name": safe_str(rec.get("piRNA_name")),
            "disease_name": safe_str(rec.get("disease_name")),
            "prediction_score": safe_str(rec.get("prediction_score")),
            "evidence": safe_str(rec.get("evidence")),
            "section_completion_rate": float(sub["section_completion_rate"].mean()),
            "key_claim_overlap": key_overlap,
            "semantic_similarity": semantic_similarity,
            "recommendation_consistency": recommendation_consistency,
            "contradiction_rate": contradiction_rate,
            "mean_latency_seconds": float(sub["latency_seconds"].mean()),
            "mean_total_tokens": float(sub["total_tokens"].dropna().mean()) if sub["total_tokens"].notna().any() else None,
            "total_report_cost_usd": total_report_cost,
            "total_audit_cost_usd": total_audit_cost,
            "total_cost_usd": round(total_report_cost + total_audit_cost, 6) if total_report_cost is not None and total_audit_cost is not None else (total_report_cost or total_audit_cost),
        })

    cons_df = pd.DataFrame(consistency_rows)
    cons_df.to_csv(outdir / "consistency_by_prediction.csv", index=False, encoding="utf-8-sig")

    summary_rows = []
    for metric in ["section_completion_rate", "key_claim_overlap", "semantic_similarity", "recommendation_consistency", "contradiction_rate",
                   "mean_latency_seconds", "mean_total_tokens", "total_report_cost_usd", "total_audit_cost_usd", "total_cost_usd"]:
        vals = pd.to_numeric(cons_df[metric], errors="coerce").dropna()
        summary_rows.append({
            "metric": metric,
            "mean": vals.mean() if len(vals) else None,
            "sd": vals.std(ddof=1) if len(vals) > 1 else 0,
            "min": vals.min() if len(vals) else None,
            "max": vals.max() if len(vals) else None,
            "n_predictions": int(len(vals)),
        })
    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(outdir / "consistency_summary.csv", index=False, encoding="utf-8-sig")

    cost_summary_rows = []
    report_cost_vals = pd.to_numeric(runs_df["cost_usd"], errors="coerce").dropna()
    cost_summary_rows.append({
        "category": "report_generation",
        "total_tokens": float(runs_df["total_tokens"].dropna().sum()) if runs_df["total_tokens"].notna().any() else None,
        "total_input_tokens": float(runs_df["input_tokens"].dropna().sum()) if runs_df["input_tokens"].notna().any() else None,
        "total_output_tokens": float(runs_df["output_tokens"].dropna().sum()) if runs_df["output_tokens"].notna().any() else None,
        "cost_usd": float(report_cost_vals.sum()) if len(report_cost_vals) else 0.0,
        "n_calls": len(runs_df),
    })
    audit_all = pd.DataFrame(audit_usage_rows)
    if len(audit_all) and "audit_cost_usd" in audit_all.columns:
        audit_cost_vals = pd.to_numeric(audit_all["audit_cost_usd"], errors="coerce").dropna()
        cost_summary_rows.append({
            "category": "claim_audit",
            "total_tokens": float(audit_all["audit_total_tokens"].dropna().sum()) if audit_all["audit_total_tokens"].notna().any() else None,
            "total_input_tokens": float(audit_all["audit_input_tokens"].dropna().sum()) if audit_all["audit_input_tokens"].notna().any() else None,
            "total_output_tokens": float(audit_all["audit_output_tokens"].dropna().sum()) if audit_all["audit_output_tokens"].notna().any() else None,
            "cost_usd": float(audit_cost_vals.sum()) if len(audit_cost_vals) else 0.0,
            "n_calls": len(audit_all),
        })
    grand_cost = sum(r["cost_usd"] for r in cost_summary_rows)
    grand_tokens = sum(r["total_tokens"] for r in cost_summary_rows if r["total_tokens"] is not None)
    cost_summary_rows.append({
        "category": "grand_total",
        "total_tokens": grand_tokens if grand_tokens else None,
        "total_input_tokens": sum(r["total_input_tokens"] for r in cost_summary_rows if r["total_input_tokens"] is not None),
        "total_output_tokens": sum(r["total_output_tokens"] for r in cost_summary_rows if r["total_output_tokens"] is not None),
        "cost_usd": grand_cost,
        "n_calls": sum(r["n_calls"] for r in cost_summary_rows if r["category"] != "grand_total"),
    })
    cost_summary_df = pd.DataFrame(cost_summary_rows)
    cost_summary_df.to_csv(outdir / "cost_summary.csv", index=False, encoding="utf-8-sig")

    if args.audit_mode == "llm":
        claims_df = pd.DataFrame(claim_rows)
        claims_df.to_csv(outdir / "claim_audit_long.csv", index=False, encoding="utf-8-sig")
        if len(claims_df):
            support = claims_df.groupby("category").size().reset_index(name="n_claims")
            support["percentage"] = support["n_claims"] / support["n_claims"].sum()
        else:
            support = pd.DataFrame(columns=["category", "n_claims", "percentage"])
        support.to_csv(outdir / "claim_evidence_support.csv", index=False, encoding="utf-8-sig")
        pd.DataFrame(audit_usage_rows).to_csv(outdir / "audit_usage.csv", index=False, encoding="utf-8-sig")
    else:
        support = pd.DataFrame(columns=["category", "n_claims", "percentage"])

    # XLSX workbook.
    xlsx_path = outdir / "pdaxplain_20x3_results.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Inputs")
        runs_df.to_excel(writer, index=False, sheet_name="Report runs")
        cons_df.to_excel(writer, index=False, sheet_name="Consistency by prediction")
        summary_df.to_excel(writer, index=False, sheet_name="Consistency summary")
        cost_summary_df.to_excel(writer, index=False, sheet_name="Cost summary")
        if args.audit_mode == "llm":
            claims_df.to_excel(writer, index=False, sheet_name="Claim audit long")
            support.to_excel(writer, index=False, sheet_name="Claim evidence support")
            pd.DataFrame(audit_usage_rows).to_excel(writer, index=False, sheet_name="Audit usage")
    print(f"Done. Results written to: {xlsx_path}")
    print(f"Raw reports written to: {report_dir.resolve()}")
    if grand_cost > 0:
        print(f"\n=== Cost Estimate (pricing: ${args.input_price_per_1M}/M input, ${args.output_price_per_1M}/M output) ===")
        for r in cost_summary_rows:
            tokens_str = f"  tokens={r['total_tokens']:,}" if r["total_tokens"] else "  tokens=N/A"
            print(f"  {r['category']}: ${r['cost_usd']:.4f} USD{tokens_str}  calls={r['n_calls']}")
    else:
        print("\n=== Cost Estimate ===  (pricing not configured; set --input_price_per_1M and --output_price_per_1M)")

if __name__ == "__main__":
    main()
