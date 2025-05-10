import json
import os

gold_path = "gold_s2.json"
run_prefix = "evaluation/run_"
output_path = "evaluation/per_object_evaluation.json"

# 📂 Load gold data
with open(gold_path) as f:
    gold_all = json.load(f)

results = {}
all_tp_ent, all_fp_ent, all_fn_ent = set(), set(), set()
all_tp_rel, all_fp_rel, all_fn_rel = set(), set(), set()

# 🧬 Entity extractors
def extract_gold_entities(gold_entry):
    gold_entities = set()
    for group in gold_entry.get("entities", []):
        for ent_type, items in group.items():
            for entity in items:
                label = entity.get("label", "").strip().lower()
                if label:
                    gold_entities.add(label)
    return gold_entities

def extract_predicted_entities(run_data):
    pred_entities = set()
    for ent_type, ent_section in run_data.items():
        if isinstance(ent_section, dict):
            labels = ent_section.get("schemaResponse", {}).get("label", [])
            pred_entities.update([label.lower().strip() for label in labels])
            attr_key = [k for k in ent_section.keys() if k.endswith("Attributes")]
            if attr_key:
                for item in ent_section.get(attr_key[0], []):
                    label = item.get("label", "").lower().strip()
                    if label:
                        pred_entities.add(label)
    return pred_entities

# 🔗 Relation extractors
def extract_triples_from_gold(gold_entry):
    triples = set()
    for relation_block in gold_entry.get("relations", []):
        for _, relation_list in relation_block.items():
            for relation in relation_list:
                subj = relation.get("subject", "").strip().lower()
                pred = relation.get("predicate", "").strip().lower()
                obj = relation.get("object", "").strip().lower()
                triples.add((subj, pred, obj))
    return triples

def extract_triples_from_run(run_data):
    triples = set()
    for class_name, section in run_data.items():
        if class_name.endswith("Relationship"):
            rels_key = list(section.keys())[0]
            for relation in section[rels_key]:
                subj = relation.get("subject", "").strip().lower()
                pred = relation.get("predicate", "").strip().lower()
                obj = relation.get("object", "").strip().lower()
                for p in pred.split("|"):
                    triples.add((subj, p.strip(), obj))
    return triples

# 📊 Metric helper
def compute_metrics(tp, fp, fn):
    precision = len(tp) / (len(tp) + len(fp)) if tp or fp else 0
    recall = len(tp) / (len(tp) + len(fn)) if tp or fn else 0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
    return precision, recall, f1

# 🔁 Loop through each gold object
for i, gold in enumerate(gold_all):
    run_path = f"{run_prefix}{i+1}.json"
    if not os.path.exists(run_path):
        continue

    with open(run_path) as f:
        run = json.load(f)

    gold_ents = extract_gold_entities(gold)
    pred_ents = extract_predicted_entities(run)

    gold_triples = extract_triples_from_gold(gold)
    pred_triples = extract_triples_from_run(run)

    TP_ent = pred_ents & gold_ents
    FP_ent = pred_ents - gold_ents
    FN_ent = gold_ents - pred_ents

    TP_rel = pred_triples & gold_triples
    FP_rel = pred_triples - gold_triples
    FN_rel = gold_triples - pred_triples

    all_tp_ent |= TP_ent
    all_fp_ent |= FP_ent
    all_fn_ent |= FN_ent

    all_tp_rel |= TP_rel
    all_fp_rel |= FP_rel
    all_fn_rel |= FN_rel

    results[f"Object {i+1}"] = {
        "Entities": {
            "true_positives": list(TP_ent),
            "false_positives": list(FP_ent),
            "false_negatives": list(FN_ent)
        },
        "Relations": {
            "true_positives": list(map(list, TP_rel)),
            "false_positives": list(map(list, FP_rel)),
            "false_negatives": list(map(list, FN_rel))
        }
    }

# 🔢 Final scores
ent_p, ent_r, ent_f1 = compute_metrics(all_tp_ent, all_fp_ent, all_fn_ent)
rel_p, rel_r, rel_f1 = compute_metrics(all_tp_rel, all_fp_rel, all_fn_rel)

results["Overall Metrics"] = {
    "Entities": {
        "precision": round(ent_p, 3),
        "recall": round(ent_r, 3),
        "f1_score": round(ent_f1, 3)
    },
    "Relations": {
        "precision": round(rel_p, 3),
        "recall": round(rel_r, 3),
        "f1_score": round(rel_f1, 3)
    }
}

# 💾 Save results
with open(output_path, "w") as f:
    json.dump(results, f, indent=2)

print("✅ Evaluation complete. Results saved to:", output_path)
