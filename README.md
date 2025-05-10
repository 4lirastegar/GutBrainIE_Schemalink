# 🧬 Biomedical Entity Extraction with GPT

This repository performs named entity extraction from biomedical literature using a structured schema and GPT-based prompting.

---

## 🚀 How to Use

### ✅ Prerequisites

Before running the pipeline:

1. **Place your OpenAI API key**  
   Open the file `utils/process_named_entities.py` and replace the API key on **line 3** with your own:

   ```python
   client = OpenAI(api_key="YOUR_OPENAI_API_KEY")
   ```

2. **Add input documents**  
   Copy or paste the documents you want to analyze into the `dev.json` file at the root of the repository.

---

## 📒 Running the Pipeline

Open and run `main.ipynb` step-by-step:

- **Cell 1:** Converts the entity schema from `.yaml` to `.json`.
- **Cell 2:** Extracts named entity classes from the JSON schema.
- **Cell 3:** Generates the expected structured response format (for GPT validation).
- **Cell 4:** Processes each document in `dev.json` using the pipeline in `utils/process_named_entities.py` and saves the results to `org_T61_BaselineRun_NuNerZero.json`.

---

## 📊 Evaluation (Optional)

To evaluate the extracted entities against a gold standard, run:

```bash
python challenge_eval.py
```

---

## 📁 Directory Structure

| Path                                 | Description                                  |
| ------------------------------------ | -------------------------------------------- |
| `main.ipynb`                         | Jupyter notebook that runs the full pipeline |
| `utils/process_named_entities.py`    | Contains the main entity extraction logic    |
| `generated/schema.json`              | Converted version of the entity schema       |
| `generated/prompts/`                 | Stores generated prompts                     |
| `output/generated_responses.json`    | Raw GPT responses for entity mentions        |
| `output/tmp_<PMID>_converted.json`   | Span-based extracted entity outputs          |
| `org_T61_BaselineRun_NuNerZero.json` | Final combined prediction output             |
| `challenge_eval.py`                  | Evaluation script (optional)                 |
| `dev.json`                           | Input biomedical articles (title & abstract) |

---

## 🛠 Requirements

- Python 3.8+
- Jupyter Notebook
- OpenAI Python SDK

To install dependencies:

```bash
pip install openai
```

---

## 🧾 License

This project is licensed for academic and research use only.
