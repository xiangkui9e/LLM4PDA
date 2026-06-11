from openai import OpenAI
import argparse
import csv
import os
import re
import time
from collections import defaultdict
from pathlib import Path

from tqdm import tqdm


# ============================================================
# 1. Disease-description prompt with explicit leakage control
# ============================================================

def create_user_message_dis_DOID(disease_name, doid_id):
    """
    Full piPromptLab disease-description prompt.

    This prompt keeps the original 12-field schema and adds explicit leakage-control
    constraints to reduce explicit piRNA/PDA-related semantic leakage.
    """
    return (
        f"Generate a single, cohesive, narrative paragraph for the disease '{disease_name}' "
        f"with Disease Ontology ID '{doid_id}'.\n\n"

        "The response must include the following 12 structured information points:\n"
        "1) Disease classification and nature (e.g., malignant, benign, chronic, acute, autoimmune, metabolic).\n"
        "2) Disease type (e.g., tumor, infectious disease, neurological disorder, cardiovascular condition).\n"
        "3) Key associated genes or mutations (minimum 2–3, e.g., TP53, TERT promoter mutation).\n"
        "4) Key proteins involved in pathogenesis (e.g., PTEN, beta-catenin, Bcl-2).\n"
        "5) Related signaling pathways (e.g., Wnt/beta-catenin, PI3K/Akt, JAK/STAT).\n"
        "6) Epigenetic mechanisms (e.g., DNA methylation, histone modifications, chromatin remodeling).\n"
        "7) Brief molecular or cellular pathogenesis mechanisms (e.g., inflammation, apoptosis dysregulation, immune evasion).\n"
        "8) Established treatment drugs and therapeutic mechanisms (at least 3 examples with mode of action).\n"
        "9) Typical clinical symptoms and signs (e.g., fever, jaundice, pain, weight loss).\n"
        "10) Common comorbidities and complications (e.g., liver cirrhosis, diabetes, metastasis).\n"
        "11) Inheritance patterns and known genetic factors (e.g., autosomal dominant, SNPs, CNVs).\n"
        "12) Diagnostic criteria and clinical testing methods (e.g., MRI, CT, biopsy, ELISA, biomarkers).\n\n"

        "Please follow these additional constraints:\n"
        "- Only include facts supported by standard biomedical knowledge or commonly cited in peer-reviewed literature "
        "or curated databases (e.g., DOID, GeneCards, KEGG, Reactome).\n"
        "- If a specific data point is unavailable or unclear, state explicitly: 'No available information'.\n"
        "- Do not fabricate gene names, drug names, molecular mechanisms, or diagnostic tools.\n"
        "- Do not speculate or hallucinate relationships or effects without clear evidence.\n"
        "- If confidence or evidence is limited, qualify statements (e.g., 'commonly reported', 'suspected', 'under investigation').\n\n"

        "Leakage-control constraints:\n"
        "- Do not mention piRNA, PIWI, PIWI-interacting RNA, hsa_piR identifiers, piRNA-disease associations, PDA labels, "
        "benchmark datasets, training/test splits, prediction targets, or model predictions.\n"
        "- Do not include any disease-specific piRNA evidence or any statement implying that a specific piRNA is associated with this disease.\n"
        "- The description must focus only on general disease-level biomedical background.\n\n"

        "The final output should be:\n"
        "- A cohesive, medically precise paragraph integrating all available points above.\n"
        "- Written in professional biomedical language suitable for clinical or research contexts.\n"
        "- Fully self-contained, without requiring external references.\n"
    )


# ============================================================
# 2. Keyword audit utilities for semantic-leakage checking
# ============================================================

AUDIT_PATTERNS = [
    # Strict PDA/piRNA-related terms
    {
        "category": "Explicit piRNA/PDA-related terms",
        "term": "piRNA",
        "pattern": r"\bpiRNAs?\b",
        "severity": "strict",
        "note": "Explicit piRNA mention"
    },
    {
        "category": "Explicit piRNA/PDA-related terms",
        "term": "PIWI",
        "pattern": r"\bPIWI(?:-like)?\b|\bPIWIL\d*\b",
        "severity": "strict",
        "note": "Explicit PIWI/PIWIL mention"
    },
    {
        "category": "Explicit piRNA/PDA-related terms",
        "term": "PIWI-interacting RNA",
        "pattern": r"\bPIWI[-\s]?interacting\s+RNAs?\b",
        "severity": "strict",
        "note": "Expanded piRNA term"
    },
    {
        "category": "Explicit piRNA/PDA-related terms",
        "term": "hsa_piR identifier",
        "pattern": r"\bhsa[_-]?piR[_-]?\d+\b",
        "severity": "strict",
        "note": "Human piRNA identifier"
    },
    {
        "category": "Explicit piRNA/PDA-related terms",
        "term": "piR identifier",
        "pattern": r"\bpiR[-_]?\d+\b|\bpiR[_-]?[A-Za-z0-9]+\b",
        "severity": "strict",
        "note": "piRNA-like identifier"
    },
    {
        "category": "Explicit piRNA/PDA-related terms",
        "term": "piRNA-disease association",
        "pattern": r"\bpiRNA[-\s–—]?disease\s+associations?\b|\bpiRNA\s+association(?:s)?\b",
        "severity": "strict",
        "note": "Explicit piRNA-disease association phrase"
    },
    {
        "category": "Explicit piRNA/PDA-related terms",
        "term": "PDA label",
        "pattern": r"\bPDA\b",
        "severity": "review",
        "note": "Ambiguous abbreviation; manually confirm whether it means piRNA-disease association"
    },

    # Broader ncRNA-related terms
    {
        "category": "Broader ncRNA-related terms",
        "term": "miRNA / microRNA",
        "pattern": r"\bmiRNAs?\b|\bmicroRNAs?\b",
        "severity": "broad",
        "note": "Broader ncRNA mention"
    },
    {
        "category": "Broader ncRNA-related terms",
        "term": "lncRNA",
        "pattern": r"\blncRNAs?\b|\blong\s+non[-\s]?coding\s+RNAs?\b",
        "severity": "broad",
        "note": "Broader ncRNA mention"
    },
    {
        "category": "Broader ncRNA-related terms",
        "term": "circRNA",
        "pattern": r"\bcircRNAs?\b|\bcircular\s+RNAs?\b",
        "severity": "broad",
        "note": "Broader ncRNA mention"
    },
    {
        "category": "Broader ncRNA-related terms",
        "term": "ncRNA / non-coding RNA",
        "pattern": r"\bncRNAs?\b|\bnon[-\s]?coding\s+RNAs?\b",
        "severity": "broad",
        "note": "Generic non-coding RNA mention"
    },
]


def normalize_text(text):
    if text is None:
        return ""
    return str(text)


def get_context(text, start, end, window=60):
    left = max(0, start - window)
    right = min(len(text), end + window)
    prefix = "..." if left > 0 else ""
    suffix = "..." if right < len(text) else ""
    return prefix + text[left:right].replace("\n", " ") + suffix


def audit_text(text):
    """
    Audit one generated disease description.

    Returns:
        hits: list of dicts, one row per matched keyword occurrence
    """
    text = normalize_text(text)
    hits = []

    for item in AUDIT_PATTERNS:
        regex = re.compile(item["pattern"], flags=re.IGNORECASE)
        for m in regex.finditer(text):
            hits.append({
                "category": item["category"],
                "term": item["term"],
                "severity": item["severity"],
                "matched_text": m.group(0),
                "start": m.start(),
                "end": m.end(),
                "context": get_context(text, m.start(), m.end()),
                "note": item["note"],
            })
    return hits


def run_keyword_audit(
    description_csv_path,
    audit_output_dir=None,
    disease_col="Disease_Name",
    doid_col="DOID",
    desc_col="Description",
    dataset_label="disease_descriptions",
):
    """
    Run keyword audit on a disease-description CSV.

    Expected input CSV columns:
        Disease_Name, DOID, Description

    Generated outputs:
        1. *_audit_per_description.csv
        2. *_keyword_hits_long.csv
        3. *_audit_summary_by_term.csv
        4. *_audit_summary_for_paper.csv
        5. *_audit_summary_for_paper.md
        6. *_audit_term_barplot.png
    """
    description_csv_path = Path(description_csv_path)
    if audit_output_dir is None:
        audit_output_dir = description_csv_path.parent / "keyword_audit"
    audit_output_dir = Path(audit_output_dir)
    audit_output_dir.mkdir(parents=True, exist_ok=True)

    with open(description_csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    per_description_rows = []
    long_hit_rows = []

    for row in rows:
        disease_name = row.get(disease_col, "")
        doid = row.get(doid_col, "")
        desc = row.get(desc_col, "")

        hits = audit_text(desc)
        strict_hits = [h for h in hits if h["severity"] == "strict"]
        broad_hits = [h for h in hits if h["severity"] == "broad"]
        review_hits = [h for h in hits if h["severity"] == "review"]

        matched_terms = sorted(set(h["term"] for h in hits))
        matched_categories = sorted(set(h["category"] for h in hits))

        per_description_rows.append({
            "Disease_Name": disease_name,
            "DOID": doid,
            "Has_any_audit_term": "Yes" if hits else "No",
            "Has_explicit_piRNA_PDA_related_term": "Yes" if strict_hits else "No",
            "Has_broader_ncRNA_related_term": "Yes" if broad_hits else "No",
            "Has_ambiguous_PDA_abbreviation": "Yes" if review_hits else "No",
            "Total_hits": len(hits),
            "Strict_hits": len(strict_hits),
            "Broad_ncRNA_hits": len(broad_hits),
            "Ambiguous_PDA_hits": len(review_hits),
            "Matched_terms": "; ".join(matched_terms),
            "Matched_categories": "; ".join(matched_categories),
            "Description": desc,
        })

        for h in hits:
            long_hit_rows.append({
                "Disease_Name": disease_name,
                "DOID": doid,
                **h
            })

    # Write per-description audit table
    per_desc_path = audit_output_dir / f"{dataset_label}_audit_per_description.csv"
    with open(per_desc_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "Disease_Name", "DOID",
            "Has_any_audit_term",
            "Has_explicit_piRNA_PDA_related_term",
            "Has_broader_ncRNA_related_term",
            "Has_ambiguous_PDA_abbreviation",
            "Total_hits", "Strict_hits", "Broad_ncRNA_hits", "Ambiguous_PDA_hits",
            "Matched_terms", "Matched_categories", "Description"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(per_description_rows)

    # Write long hit table
    long_path = audit_output_dir / f"{dataset_label}_keyword_hits_long.csv"
    with open(long_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "Disease_Name", "DOID",
            "category", "term", "severity", "matched_text",
            "start", "end", "context", "note"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(long_hit_rows)

    # Summary by term
    term_stats = {}
    for item in AUDIT_PATTERNS:
        term_stats[item["term"]] = {
            "category": item["category"],
            "severity": item["severity"],
            "term": item["term"],
            "descriptions_with_term": 0,
            "total_hits": 0,
            "example_diseases": set(),
        }

    disease_term_seen = defaultdict(set)
    for h in long_hit_rows:
        key = h["term"]
        disease_key = (h["Disease_Name"], h["DOID"])
        disease_term_seen[key].add(disease_key)
        term_stats[key]["total_hits"] += 1
        if len(term_stats[key]["example_diseases"]) < 5:
            term_stats[key]["example_diseases"].add(h["Disease_Name"])

    for term, disease_keys in disease_term_seen.items():
        term_stats[term]["descriptions_with_term"] = len(disease_keys)

    summary_rows = []
    n_desc = len(rows)
    for term, s in term_stats.items():
        summary_rows.append({
            "Category": s["category"],
            "Term": term,
            "Severity": s["severity"],
            "Descriptions_with_term": s["descriptions_with_term"],
            "Descriptions_with_term_percent": round(100 * s["descriptions_with_term"] / n_desc, 2) if n_desc else 0,
            "Total_hits": s["total_hits"],
            "Example_diseases": "; ".join(sorted(s["example_diseases"])),
        })

    summary_path = audit_output_dir / f"{dataset_label}_audit_summary_by_term.csv"
    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "Category", "Term", "Severity",
            "Descriptions_with_term", "Descriptions_with_term_percent",
            "Total_hits", "Example_diseases"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)

    # Paper-ready overall summary
    any_count = sum(1 for r in per_description_rows if r["Has_any_audit_term"] == "Yes")
    strict_count = sum(1 for r in per_description_rows if r["Has_explicit_piRNA_PDA_related_term"] == "Yes")
    broad_count = sum(1 for r in per_description_rows if r["Has_broader_ncRNA_related_term"] == "Yes")
    ambiguous_count = sum(1 for r in per_description_rows if r["Has_ambiguous_PDA_abbreviation"] == "Yes")

    total_hits = sum(int(r["Total_hits"]) for r in per_description_rows)
    strict_hits = sum(int(r["Strict_hits"]) for r in per_description_rows)
    broad_hits = sum(int(r["Broad_ncRNA_hits"]) for r in per_description_rows)
    ambiguous_hits = sum(int(r["Ambiguous_PDA_hits"]) for r in per_description_rows)

    def pct(x):
        return round(100 * x / n_desc, 2) if n_desc else 0

    paper_rows = [
        {
            "Audit_item": "Number of disease descriptions audited",
            "Result": n_desc,
            "Percentage": "NA",
            "Interpretation": "Total number of generated disease descriptions included in the audit",
        },
        {
            "Audit_item": "Descriptions containing any audited term",
            "Result": any_count,
            "Percentage": pct(any_count),
            "Interpretation": "Descriptions requiring keyword-level review",
        },
        {
            "Audit_item": "Descriptions containing explicit piRNA/PDA-related terms",
            "Result": strict_count,
            "Percentage": pct(strict_count),
            "Interpretation": "Descriptions containing explicit piRNA, PIWI, hsa_piR/piR identifier, or piRNA-disease association terms",
        },
        {
            "Audit_item": "Descriptions containing broader ncRNA-related terms",
            "Result": broad_count,
            "Percentage": pct(broad_count),
            "Interpretation": "Descriptions containing miRNA, lncRNA, circRNA, ncRNA, or non-coding RNA terms",
        },
        {
            "Audit_item": "Descriptions containing ambiguous PDA abbreviation",
            "Result": ambiguous_count,
            "Percentage": pct(ambiguous_count),
            "Interpretation": "Descriptions containing the abbreviation PDA; manual review is needed because PDA can be clinically ambiguous",
        },
        {
            "Audit_item": "Total keyword hits",
            "Result": total_hits,
            "Percentage": "NA",
            "Interpretation": "Total number of audited keyword occurrences",
        },
        {
            "Audit_item": "Total explicit piRNA/PDA-related hits",
            "Result": strict_hits,
            "Percentage": "NA",
            "Interpretation": "Total strict leakage-related keyword occurrences",
        },
        {
            "Audit_item": "Total broader ncRNA-related hits",
            "Result": broad_hits,
            "Percentage": "NA",
            "Interpretation": "Total broader ncRNA keyword occurrences",
        },
        {
            "Audit_item": "Total ambiguous PDA hits",
            "Result": ambiguous_hits,
            "Percentage": "NA",
            "Interpretation": "Total ambiguous PDA abbreviation occurrences",
        },
    ]

    paper_csv_path = audit_output_dir / f"{dataset_label}_audit_summary_for_paper.csv"
    with open(paper_csv_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["Audit_item", "Result", "Percentage", "Interpretation"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(paper_rows)

    # Markdown table for direct Supplementary Methods copy/paste
    paper_md_path = audit_output_dir / f"{dataset_label}_audit_summary_for_paper.md"
    with open(paper_md_path, "w", encoding="utf-8") as f:
        f.write("| Audit item | Result | Percentage | Interpretation |\n")
        f.write("|---|---:|---:|---|\n")
        for r in paper_rows:
            f.write(f"| {r['Audit_item']} | {r['Result']} | {r['Percentage']} | {r['Interpretation']} |\n")

    # Optional figure
    try:
        import matplotlib.pyplot as plt

        fig_rows = [
            ("Any audited term", any_count),
            ("Explicit piRNA/PDA-related", strict_count),
            ("Broader ncRNA-related", broad_count),
            ("Ambiguous PDA abbreviation", ambiguous_count),
        ]
        labels = [x[0] for x in fig_rows]
        values = [x[1] for x in fig_rows]

        plt.figure(figsize=(8, 4.8))
        plt.bar(labels, values)
        plt.ylabel("Number of disease descriptions")
        plt.xticks(rotation=25, ha="right")
        plt.title("Keyword audit of generated disease descriptions")
        plt.tight_layout()
        fig_path = audit_output_dir / f"{dataset_label}_audit_term_barplot.png"
        plt.savefig(fig_path, dpi=300)
        plt.close()
    except Exception as e:
        fig_path = None
        print(f"[Warning] Could not generate figure: {e}")

    print("\nKeyword audit complete.")
    print(f"Per-description audit: {per_desc_path}")
    print(f"Long keyword hits:      {long_path}")
    print(f"Summary by term:       {summary_path}")
    print(f"Paper summary CSV:     {paper_csv_path}")
    print(f"Paper summary MD:      {paper_md_path}")
    if fig_path:
        print(f"Audit figure:          {fig_path}")

    return {
        "per_description": str(per_desc_path),
        "long_hits": str(long_path),
        "summary_by_term": str(summary_path),
        "paper_summary_csv": str(paper_csv_path),
        "paper_summary_md": str(paper_md_path),
        "figure": str(fig_path) if fig_path else None,
    }


# ============================================================
# 3. Disease-description generation
# ============================================================

def generate_disease_descriptions(
    input_csv_path,
    output_csv_path,
    api_key_path="key.txt",
    base_url="https://openai.weavex.tech/v1",
    model_id="gpt-5.4",
    max_tokens=2000,
    sleep_seconds=2,
):
    with open(api_key_path, "r", encoding="utf-8") as file:
        api_key = file.read().strip("\n")

    client = OpenAI(api_key=api_key, base_url=base_url)

    with open(input_csv_path, newline="", encoding="utf-8") as f:
        total_rows = sum(1 for _ in f) - 1

    output_csv_path = Path(output_csv_path)
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)

    with open(input_csv_path, newline="", encoding="utf-8") as infile:
        reader = csv.reader(infile)
        header = next(reader)

        with open(output_csv_path, "w", newline="", encoding="utf-8") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=["Disease_Name", "DOID", "Description"])
            writer.writeheader()
            outfile.flush()

            for row in tqdm(reader, total=total_rows, desc="Processing diseases", unit="disease"):
                dis_name = row[0]
                dis_id = row[1]

                messages = [
                    {
                        "role": "system",
                        "content": "You are an expert in medical research, genetics, chemistry, and pharmacology."
                    },
                    {
                        "role": "user",
                        "content": create_user_message_dis_DOID(dis_name, dis_id)
                    }
                ]

                try:
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=messages,
                        max_tokens=max_tokens
                    )
                    description = response.choices[0].message.content
                    tqdm.write(f"Processed: {dis_name}")
                except Exception as e:
                    error_message = f"An error occurred while processing {dis_name}: {e}"
                    tqdm.write(error_message)
                    description = "Error retrieving information"

                writer.writerow({
                    "Disease_Name": dis_name,
                    "DOID": dis_id,
                    "Description": description
                })
                outfile.flush()
                time.sleep(sleep_seconds)

    print(f"Processing complete. Output saved to {output_csv_path}")
    return str(output_csv_path)


def main():
    parser = argparse.ArgumentParser(
        description="Generate disease descriptions and audit explicit piRNA/PDA/ncRNA-related terms."
    )
    parser.add_argument("--input_csv", default="doid.csv", help="Input CSV with disease name and DOID columns.")
    parser.add_argument("--output_csv", default=None, help="Output CSV for generated disease descriptions.")
    parser.add_argument("--api_key_path", default="key.txt", help="Path to API key file.")
    parser.add_argument("--base_url", default="https://openai.weavex.tech/v1", help="OpenAI-compatible API base URL.")
    parser.add_argument("--model_id", default="gpt-5.4", help="Chat model ID.")
    parser.add_argument("--max_tokens", type=int, default=2000)
    parser.add_argument("--sleep_seconds", type=float, default=2)
    parser.add_argument("--audit_only", action="store_true", help="Only run keyword audit on an existing output CSV.")
    parser.add_argument("--audit_csv", default=None, help="Existing disease description CSV for audit-only mode.")
    parser.add_argument("--audit_output_dir", default=None, help="Directory for keyword audit outputs.")
    parser.add_argument("--dataset_label", default=None, help="Prefix label for audit output files.")

    args = parser.parse_args()

    if args.output_csv is None:
        args.output_csv = f"01-疾病描述生成/{args.model_id}_dis_desc.csv"

    if args.dataset_label is None:
        args.dataset_label = Path(args.output_csv).stem

    if args.audit_only:
        if args.audit_csv is None:
            raise ValueError("--audit_csv must be provided when --audit_only is used.")
        run_keyword_audit(
            description_csv_path=args.audit_csv,
            audit_output_dir=args.audit_output_dir,
            dataset_label=args.dataset_label,
        )
    else:
        generated_csv = generate_disease_descriptions(
            input_csv_path=args.input_csv,
            output_csv_path=args.output_csv,
            api_key_path=args.api_key_path,
            base_url=args.base_url,
            model_id=args.model_id,
            max_tokens=args.max_tokens,
            sleep_seconds=args.sleep_seconds,
        )
        run_keyword_audit(
            description_csv_path=generated_csv,
            audit_output_dir=args.audit_output_dir,
            dataset_label=args.dataset_label,
        )


if __name__ == "__main__":
    main()
