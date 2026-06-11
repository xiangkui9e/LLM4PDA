from openai import OpenAI
from tqdm import tqdm
from pathlib import Path
import csv
import time
import json

EMBEDDING_PRICE_PER_1M = 0.13  # text-embedding-3-large via OpenRouter


def get_embeddings(text, api_key):
    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://github.com",
            "X-Title": "disease-embedding",
        },
    )
    response = client.embeddings.create(
        input=text,
        model="openai/text-embedding-3-small",
        # dimensions=640
    )
    return response.data[0].embedding, response.usage.total_tokens


if __name__ == '__main__':
    # Load the OpenAI API key
    with open("openrouter_key.txt", "r") as file:
        api_key = file.read().strip('\n')

    input_csv = '01-疾病描述生成/gpt-5.4_dis_desc.csv'
    output_txt = '02-疾病嵌入生成/gpt-5.4_dis_emb.txt'
    token_log_path = Path(output_txt).with_suffix(".token_cost.csv")

    Path(output_txt).parent.mkdir(parents=True, exist_ok=True)

    # 计算总行数
    with open(input_csv, 'r', encoding='utf-8') as f:
        total_rows = sum(1 for _ in f) - 1

    miRNA_to_embedding = {}
    total_tokens = 0

    with open(input_csv, 'r', encoding='utf-8') as csvfile, \
         open(output_txt, 'w', encoding='utf-8') as txtfile, \
         open(token_log_path, 'w', newline='', encoding='utf-8') as token_log:

        reader = csv.DictReader(csvfile)
        txtfile.write("Disease::::Embedding\n")

        token_writer = csv.DictWriter(token_log, fieldnames=["Disease_Name", "Tokens", "Cost_USD"])
        token_writer.writeheader()
        token_log.flush()

        for row in tqdm(reader, total=total_rows, desc="Embedding diseases"):
            name = row['Disease_Name']
            description = row['Description']
            try:
                embedding, tokens = get_embeddings(description, api_key)
                miRNA_to_embedding[name] = embedding
                total_tokens += tokens
                cost = (tokens / 1_000_000) * EMBEDDING_PRICE_PER_1M

                txtfile.write(f"{name}::::{json.dumps(embedding)}\n")
                tqdm.write(f"Processed: {name} | tokens: {tokens} | cost: ${cost:.6f}")

                token_writer.writerow({
                    "Disease_Name": name,
                    "Tokens": tokens,
                    "Cost_USD": round(cost, 6),
                })
                token_log.flush()

            except Exception as e:
                print(f"Error embedding '{name}': {e}")
                miRNA_to_embedding[name] = None
                txtfile.write(f"{name}::::ERROR: {e}\n")
            txtfile.flush()

            time.sleep(3)

    total_cost = (total_tokens / 1_000_000) * EMBEDDING_PRICE_PER_1M
    print(f"Processing complete. Output saved to {output_txt}")
    print(f"Total token usage: {total_tokens}")
    print(f"Total cost: ${total_cost:.6f} ($0.13/1M tokens)")
    print(f"Token cost log saved to {token_log_path}")