import json
import os
import shutil
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

# Load gold standard with pre-processed 'text'
with open("gold_s2.json", "r") as f:
    gold_data = json.load(f)

# Paths
sample_text_path = "input/sample.txt"
notebook_path = "main.ipynb"
output_file_path = "output/generated_responses.json"
evaluation_dir = "evaluation"

# Create evaluation directory if it doesn't exist
os.makedirs(evaluation_dir, exist_ok=True)

# Load notebook structure
with open(notebook_path) as f:
    nb = nbformat.read(f, as_version=4)

ep = ExecutePreprocessor(timeout=600, kernel_name='python3')

# Iterate over each item
for i, item in enumerate(gold_data):  # 🔁 Use [:5] if you only want to run on first 5
    print(f"\n🚀 Running notebook for item {i+1}/{len(gold_data)}...")

    # Write current sample text to file
    with open(sample_text_path, "w") as text_file:
        text_file.write(item["text"])

    # Copy notebook content before running
    notebook_instance = nbformat.from_dict(nb)

    try:
        # Run the notebook
        ep.preprocess(notebook_instance, {'metadata': {'path': '.'}})
        print(f"✅ Execution completed for item {i+1}")

        # Copy output to evaluation directory
        if os.path.exists(output_file_path):
            destination = os.path.join(evaluation_dir, f"run_{i+1}.json")
            shutil.copy(output_file_path, destination)
            print(f"📁 Output copied to {destination}")
        else:
            print("⚠️ Output file not found!")

    except Exception as e:
        print(f"❌ Error during execution for item {i+1}: {e}")
