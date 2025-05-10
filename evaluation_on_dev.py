import json
import os
import time
from nbclient import NotebookClient
from nbformat import read

def run_notebook(notebook_path):
    with open(notebook_path) as f:
        nb = read(f, as_version=4)
    client = NotebookClient(nb, timeout=600, kernel_name='python3')
    client.execute()

def evaluate_generated_vs_gold(generated_path, gold_path):
    with open(generated_path, 'r', encoding='utf-8') as f:
        generated_data = json.load(f)
    with open(gold_path, 'r', encoding='utf-8') as f:
        gold_data = json.load(f)

    generated_entities = {(e['text_span'].lower(), e['label'].lower()) for e in generated_data['mentions']}
    gold_entities = {(e['text_span'].lower(), e['label'].lower()) for e in gold_data['entities']}

    true_positives = generated_entities & gold_entities
    false_positives = generated_entities - gold_entities
    false_negatives = gold_entities - generated_entities

    precision = len(true_positives) / (len(true_positives) + len(false_positives) + 1e-8)
    recall = len(true_positives) / (len(true_positives) + len(false_negatives) + 1e-8)
    f1 = 2 * precision * recall / (precision + recall + 1e-8)

    result = {
        "true_positives": list(true_positives),
        "false_positives": list(false_positives),
        "false_negatives": list(false_negatives),
        "precision": precision,
        "recall": recall,
        "f1_score": f1
    }

    return result

# Paths
input_file = 'dev.json'
sample_file = 'input/sample.txt'
output_entities_file = 'converted_entities.json'
gold_file = 'output/gold.json'   # <- saving gold standard dynamically here
notebook_path = 'main.ipynb'

os.makedirs('input', exist_ok=True)
os.makedirs('output', exist_ok=True)

# Read dev data
with open(input_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Initialize counters
total_tp = total_fp = total_fn = 0

# How many samples to process
MAX_SAMPLES = 38 

# Loop through first MAX_SAMPLES
for idx, (pmid, content) in enumerate(list(data.items())[:MAX_SAMPLES]):
    title = content['metadata']['title']
    abstract = content['metadata']['abstract']
    gold_entities = content['entities']

    # Clear previous outputs
    if os.path.exists(output_entities_file):
        os.remove(output_entities_file)
    if os.path.exists(gold_file):
        os.remove(gold_file)

    # Write sample.txt
    text = f"title: {title}\nabstract: {abstract}"
    with open(sample_file, 'w', encoding='utf-8') as f:
        f.write(text)

    # Write corresponding gold.json
    with open(gold_file, 'w', encoding='utf-8') as f:
        json.dump({"entities": gold_entities}, f, indent=2)

    print(f"\n[{idx+1}] PMID {pmid}: Sample text written to {sample_file} and gold to {gold_file} ✅")

    # 🚀 Run your Jupyter Notebook
    print(f"⚡ Running your notebook {notebook_path} automatically...")
    run_notebook(notebook_path)

    # Wait briefly
    time.sleep(2)

    # Load generated and gold entities
    if not os.path.exists(output_entities_file):
        print(f"❗ Error: No output file '{output_entities_file}' found after running the notebook.")
        continue

    result = evaluate_generated_vs_gold(output_entities_file, gold_file)

    total_tp += len(result["true_positives"])
    total_fp += len(result["false_positives"])
    total_fn += len(result["false_negatives"])

    print(f"✅ Evaluation Done: Precision={result['precision']:.4f} | Recall={result['recall']:.4f} | F1={result['f1_score']:.4f}")

# Overall metrics
overall_precision = total_tp / (total_tp + total_fp + 1e-8)
overall_recall = total_tp / (total_tp + total_fn + 1e-8)
overall_f1 = 2 * overall_precision * overall_recall / (overall_precision + overall_recall + 1e-8)

print("\n=== 📊 Overall Performance ===")
print(f"Overall Precision: {overall_precision:.4f}")
print(f"Overall Recall: {overall_recall:.4f}")
print(f"Overall F1 Score: {overall_f1:.4f}")
