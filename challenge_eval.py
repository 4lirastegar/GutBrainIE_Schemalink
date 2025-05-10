
import json

# DEFINE HERE THE PATH(S) TO YOUR PREDICTIONS
PREDICTIONS_PATH_6_1 = 'org_T61_BaselineRun_NuNerZero.json'
PREDICTIONS_PATH_6_2 = 'org_T621_BaselineRun_ATLOP.json'
PREDICTIONS_PATH_6_3 = 'org_T622_BaselineRun_ATLOP.json'
PREDICTIONS_PATH_6_4 = 'org_T623_BaselineRun_ATLOP.json'

# DEFINE HERE FOR WHICH SUBTASK(S) YOU WANT TO EVAL YOUR PREDICTIONS
eval_6_1_NER = True
eval_6_2_binary_tag_RE = False
eval_6_3_ternary_tag_RE = False
eval_6_4_ternary_mention_RE = False

GROUND_TRUTH_PATH = "dev.json"
try:
    with open(GROUND_TRUTH_PATH, 'r', encoding='utf-8') as file:
        ground_truth = json.load(file)
except OSError:
    raise OSError(f'Error in opening the specified json file: {GROUND_TRUTH_PATH}')

LEGAL_ENTITY_LABELS = [
    "anatomical location",
    "animal",
    "bacteria",
    "biomedical technique",
    "chemical",
    "DDF",
    "dietary supplement",
    "drug",
    "food",
    "gene",
    "human",
    "microbiome",
    "statistical technique"
]

LEGAL_RELATION_LABELS = [
    "administered",
    "affect",
    "change abundance",
    "change effect",
    "change expression",
    "compared to",
    "impact",
    "influence",
    "interact",
    "is a",
    "is linked to",
    "located in",
    "part of",
    "produced by",
    "strike",
    "target",
    "used by"
]



def remove_duplicated_entities(predictions: dict) -> None:
    removed_count = 0
    for pmid in list(predictions.keys()):
        seen = set()
        deduped = []
        for ent in predictions[pmid]["entities"]:
            key = (ent["start_idx"], ent["end_idx"], ent["location"])
            if key not in seen:
                seen.add(key)
                deduped.append(ent)
            else:
                removed_count += 1
        predictions[pmid]["entities"] = deduped
    
    if removed_count > 0:
        print(f"=== Removed {removed_count} duplicated entities from predictions ===")
    else:
        #print("=== No duplicated entities found in predictions ===")
        pass

def remove_overlapping_entities(predictions: dict) -> None:
    removed_count = 0

    # Iterate over PMIDs
    for pmid in list(predictions.keys()):
        original_len = len(predictions[pmid]['entities'])
        
        # Group entities by location
        groups = {'title': [], 'abstract': []}
        for ent in predictions[pmid]['entities']:
            loc = ent["location"]
            groups[loc].append(ent)

        # For each location, build overlap clusters and select the longest
        keepers = set()
        for loc in groups:
            group = groups[loc]
            # sort by start_idx so we have overlapping entities contiguous
            group = sorted(group, key=lambda e: e["start_idx"])

            clusters = []
            cluster = []
            current_end = None

            for ent in group:
                if not cluster:
                    # start the first cluster
                    cluster = [ent]
                    current_end = ent["end_idx"]
                else:
                    # check overlap: ent.start_idx < current_end
                    if ent["start_idx"] < current_end:
                        cluster.append(ent)
                        # extend cluster span if needed
                        if ent["end_idx"] > current_end:
                            current_end = ent["end_idx"]
                    else:
                        clusters.append(cluster)
                        cluster = [ent]
                        current_end = ent["end_idx"]
            if cluster:
                clusters.append(cluster)

            # pick the longest entity in each cluster
            for clust in clusters:
                # initialize with first entity
                longest = clust[0]
                max_len = longest["end_idx"] - longest["start_idx"]
                # compare with the rest
                for ent in clust[1:]:
                    length = ent["end_idx"] - ent["start_idx"]
                    if length > max_len:
                        longest = ent
                        max_len = length
                # track by (start, end, loc)
                keepers.add((longest["start_idx"],
                             longest["end_idx"],
                             longest["location"]))

        # Rebuild the entity list in original order, keeping only the keepers
        deduped = []
        for ent in predictions[pmid]['entities']:
            key = (ent["start_idx"], ent["end_idx"], ent["location"])
            if key in keepers:
                deduped.append(ent)
                keepers.remove(key)  # avoid duplicates

        predictions[pmid]["entities"] = deduped

        # count how many overlapping entities have been removed for this document
        removed_count += (original_len - len(deduped))

    if removed_count > 0:
        print(f"=== Removed {removed_count} overlapping entities ===")
    else:
        #print("=== No overlapping entity found ===")
        pass

def eval_submission_6_1_NER(path):
    try:
        with open(path, 'r', encoding='utf-8') as file:
            predictions = json.load(file)
    except OSError:
        raise OSError(f'Error in opening the specified json file: {path}')

    # Remove duplicated and overlapping entities
    remove_duplicated_entities(predictions)
    remove_overlapping_entities(predictions)
    
    ground_truth_NER = dict()
    count_annotated_entities_per_label = {}
    
    for pmid, article in ground_truth.items():
        if pmid not in ground_truth_NER:
            ground_truth_NER[pmid] = []
        for entity in article['entities']:
            start_idx = int(entity["start_idx"])
            end_idx = int(entity["end_idx"])
            location = str(entity["location"])
            text_span = str(entity["text_span"])
            label = str(entity["label"]) 
            
            entry = (start_idx, end_idx, location, text_span, label)
            ground_truth_NER[pmid].append(entry)
            
            if label not in count_annotated_entities_per_label:
                count_annotated_entities_per_label[label] = 0
            count_annotated_entities_per_label[label] += 1

    count_predicted_entities_per_label = {label: 0 for label in list(count_annotated_entities_per_label.keys())}
    count_true_positives_per_label = {label: 0 for label in list(count_annotated_entities_per_label.keys())}

    for pmid in predictions.keys():
        try:
            entities = predictions[pmid]['entities']
        except KeyError:
            raise KeyError(f'{pmid} - Not able to find field \"entities\" within article')
        
        for entity in entities:
            try:
                start_idx = int(entity["start_idx"])
                end_idx = int(entity["end_idx"])
                location = str(entity["location"])
                text_span = str(entity["text_span"])
                label = str(entity["label"]) 
            except KeyError:
                raise KeyError(f'{pmid} - Not able to find one or more of the expected fields for entity: {entity}')
            
            if label not in LEGAL_ENTITY_LABELS:
                raise NameError(f'{pmid} - Illegal label {label} for entity: {entity}')

            if label in count_predicted_entities_per_label:
                count_predicted_entities_per_label[label] += 1

            entry = (start_idx, end_idx, location, text_span, label)
            if entry in ground_truth_NER[pmid]:
                count_true_positives_per_label[label] += 1

    count_annotated_entities = sum(count_annotated_entities_per_label[label] for label in list(count_annotated_entities_per_label.keys()))
    count_predicted_entities = sum(count_predicted_entities_per_label[label] for label in list(count_annotated_entities_per_label.keys()))
    count_true_positives = sum(count_true_positives_per_label[label] for label in list(count_annotated_entities_per_label.keys()))

    micro_precision = count_true_positives / (count_predicted_entities + 1e-10)
    micro_recall = count_true_positives / (count_annotated_entities + 1e-10)
    micro_f1 = 2 * ((micro_precision * micro_recall) / (micro_precision + micro_recall + 1e-10))

    precision, recall, f1 = 0, 0, 0
    n = 0
    for label in list(count_annotated_entities_per_label.keys()):
        n += 1
        current_precision = count_true_positives_per_label[label] / (count_predicted_entities_per_label[label] + 1e-10) 
        current_recall = count_true_positives_per_label[label] / (count_annotated_entities_per_label[label] + 1e-10) 
        
        precision += current_precision
        recall += current_recall
        f1 += 2 * ((current_precision * current_recall) / (current_precision + current_recall + 1e-10))
    
    precision = precision / n
    recall = recall / n
    f1 = f1 / n

    return precision, recall, f1, micro_precision, micro_recall, micro_f1



def remove_duplicated_binary_tag_relations(predictions: dict) -> None:
    removed_count = 0
    for pmid in list(predictions.keys()):
        seen = set()
        deduped = []
        for rel in predictions[pmid]["binary_tag_based_relations"]:
            key = (rel["subject_label"], rel["object_label"])
            if key not in seen:
                seen.add(key)
                deduped.append(rel)
            else:
                removed_count += 1
        predictions[pmid]["binary_tag_based_relations"] = deduped
    
    if removed_count > 0:
        print(f"=== Removed {removed_count} duplicated binary tag-based relations from predictions ===")
    else:
        #print("=== No duplicated binary tag-based relations found in predictions ===")
        pass

def eval_submission_6_2_binary_tag_RE(path):
    try:
        with open(path, 'r', encoding='utf-8') as file:
            predictions = json.load(file)
    except OSError:
        raise OSError(f'Error in opening the specified json file: {path}')

    # Remove duplicated binary tag-based relations
    remove_duplicated_binary_tag_relations(predictions)

    ground_truth_binary_tag_RE = dict()
    count_annotated_relations_per_label = {}

    for pmid, article in ground_truth.items():
        if pmid not in ground_truth_binary_tag_RE:
            ground_truth_binary_tag_RE[pmid] = []
        for relation in article['binary_tag_based_relations']:
            subject_label = str(relation["subject_label"])
            object_label = str(relation["object_label"]) 

            label = (subject_label, object_label)
            ground_truth_binary_tag_RE[pmid].append(label)

            if label not in count_annotated_relations_per_label:
                count_annotated_relations_per_label[label] = 0
            count_annotated_relations_per_label[label] += 1
    
    count_predicted_relations_per_label = {label: 0 for label in list(count_annotated_relations_per_label.keys())}
    count_true_positives_per_label = {label: 0 for label in list(count_annotated_relations_per_label.keys())}

    for pmid in predictions.keys():
        try:
            relations = predictions[pmid]['binary_tag_based_relations']
        except KeyError:
            raise KeyError(f'{pmid} - Not able to find field \"binary_tag_based_relations\" within article')
        
        for relation in relations:
            try:
                subject_label = str(relation["subject_label"])
                object_label = str(relation["object_label"]) 
            except KeyError:
                raise KeyError(f'{pmid} - Not able to find one or more of the expected fields for relation: {relation}')
            
            if subject_label not in LEGAL_ENTITY_LABELS:
                raise NameError(f'{pmid} - Illegal subject entity label {subject_label} for relation: {relation}')
            
            if object_label not in LEGAL_ENTITY_LABELS:
                raise NameError(f'{pmid} - Illegal object entity label {object_label} for relation: {relation}')

            label = (subject_label, object_label)
            if label in count_predicted_relations_per_label:
                count_predicted_relations_per_label[label] += 1

            if label in ground_truth_binary_tag_RE[pmid]:
                count_true_positives_per_label[label] += 1

    count_annotated_relations = sum(count_annotated_relations_per_label[label] for label in list(count_annotated_relations_per_label.keys()))
    count_predicted_relations = sum(count_predicted_relations_per_label[label] for label in list(count_annotated_relations_per_label.keys()))
    count_true_positives = sum(count_true_positives_per_label[label] for label in list(count_annotated_relations_per_label.keys()))

    micro_precision = count_true_positives / (count_predicted_relations + 1e-10)
    micro_recall = count_true_positives / (count_annotated_relations + 1e-10)
    micro_f1 = 2 * ((micro_precision * micro_recall) / (micro_precision + micro_recall + 1e-10))

    precision, recall, f1 = 0, 0, 0
    n = 0
    for label in list(count_annotated_relations_per_label.keys()):
        n += 1
        current_precision = count_true_positives_per_label[label] / (count_predicted_relations_per_label[label] + 1e-10) 
        current_recall = count_true_positives_per_label[label] / (count_annotated_relations_per_label[label] + 1e-10) 
        
        precision += current_precision
        recall += current_recall
        f1 += 2 * ((current_precision * current_recall) / (current_precision + current_recall + 1e-10))
    
    precision = precision / n
    recall = recall / n
    f1 = f1 / n

    return precision, recall, f1, micro_precision, micro_recall, micro_f1



def remove_duplicated_ternary_tag_relations(predictions: dict) -> None:
    removed_count = 0
    for pmid in list(predictions.keys()):
        seen = set()
        deduped = []
        for rel in predictions[pmid]["ternary_tag_based_relations"]:
            key = (rel["subject_label"], rel["predicate"], rel["object_label"])
            if key not in seen:
                seen.add(key)
                deduped.append(rel)
            else:
                removed_count += 1
        predictions[pmid]["ternary_tag_based_relations"] = deduped
    
    if removed_count > 0:
        print(f"=== Removed {removed_count} duplicated ternary tag-based relations from predictions ===")
    else:
        #print("=== No duplicated ternary tag-based relations found in predictions ===")
        pass

def eval_submission_6_3_ternary_tag_RE(path):
    try:
        with open(path, 'r', encoding='utf-8') as file:
            predictions = json.load(file)
    except OSError:
        raise OSError(f'Error in opening the specified json file: {path}')

    # Remove duplicated ternary tag-based relations
    remove_duplicated_ternary_tag_relations(predictions)
    
    ground_truth_ternary_tag_RE = dict()
    count_annotated_relations_per_label = {}

    for pmid, article in ground_truth.items():
        if pmid not in ground_truth_ternary_tag_RE:
            ground_truth_ternary_tag_RE[pmid] = []
        for relation in article['ternary_tag_based_relations']:
            subject_label = str(relation["subject_label"])
            predicate = str(relation["predicate"])
            object_label = str(relation["object_label"]) 
            
            label = (subject_label, predicate, object_label)
            ground_truth_ternary_tag_RE[pmid].append(label)

            if label not in count_annotated_relations_per_label:
                count_annotated_relations_per_label[label] = 0
            count_annotated_relations_per_label[label] += 1

    count_predicted_relations_per_label = {label: 0 for label in list(count_annotated_relations_per_label.keys())}
    count_true_positives_per_label = {label: 0 for label in list(count_annotated_relations_per_label.keys())}

    for pmid in predictions.keys():
        try:
            relations = predictions[pmid]['ternary_tag_based_relations']
        except KeyError:
            raise KeyError(f'{pmid} - Not able to find field \"ternary_tag_based_relations\" within article')
        
        for relation in relations:            
            try:
                subject_label = str(relation["subject_label"])
                predicate = str(relation["predicate"])
                object_label = str(relation["object_label"]) 
            except KeyError:
                raise KeyError(f'{pmid} - Not able to find one or more of the expected fields for relation: {relation}')
            
            if subject_label not in LEGAL_ENTITY_LABELS:
                raise NameError(f'{pmid} - Illegal subject entity label {subject_label} for relation: {relation}')
            
            if object_label not in LEGAL_ENTITY_LABELS:
                raise NameError(f'{pmid} - Illegal object entity label {object_label} for relation: {relation}')
            
            if predicate not in LEGAL_RELATION_LABELS:
                raise NameError(f'{pmid} - Illegal predicate {predicate} for relation: {relation}')

            label = (subject_label, predicate, object_label)
            if label in count_predicted_relations_per_label:
                count_predicted_relations_per_label[label] += 1

            if label in ground_truth_ternary_tag_RE[pmid]:
                count_true_positives_per_label[label] += 1

    count_annotated_relations = sum(count_annotated_relations_per_label[label] for label in list(count_annotated_relations_per_label.keys()))
    count_predicted_relations = sum(count_predicted_relations_per_label[label] for label in list(count_annotated_relations_per_label.keys()))
    count_true_positives = sum(count_true_positives_per_label[label] for label in list(count_annotated_relations_per_label.keys()))

    micro_precision = count_true_positives / (count_predicted_relations + 1e-10)
    micro_recall = count_true_positives / (count_annotated_relations + 1e-10)
    micro_f1 = 2 * ((micro_precision * micro_recall) / (micro_precision + micro_recall + 1e-10))

    precision, recall, f1 = 0, 0, 0
    n = 0
    for label in list(count_annotated_relations_per_label.keys()):
        n += 1
        current_precision = count_true_positives_per_label[label] / (count_predicted_relations_per_label[label] + 1e-10) 
        current_recall = count_true_positives_per_label[label] / (count_annotated_relations_per_label[label] + 1e-10) 
        
        precision += current_precision
        recall += current_recall
        f1 += 2 * ((current_precision * current_recall) / (current_precision + current_recall + 1e-10))
    
    precision = precision / n
    recall = recall / n
    f1 = f1 / n

    return precision, recall, f1, micro_precision, micro_recall, micro_f1



def remove_duplicated_ternary_mention_relations(predictions: dict) -> None:
    removed_count = 0
    for pmid in list(predictions.keys()):
        seen = set()
        deduped = []
        for rel in predictions[pmid]["ternary_mention_based_relations"]:
            key = (rel['subject_text_span'], rel["subject_label"], rel["predicate"], rel['object_text_span'], rel["object_label"])
            if key not in seen:
                seen.add(key)
                deduped.append(rel)
            else:
                removed_count += 1
        predictions[pmid]["ternary_mention_based_relations"] = deduped
    
    if removed_count > 0:
        print(f"=== Removed {removed_count} duplicated ternary mention-based relations from predictions ===")
    else:
        #print("=== No duplicated ternary mention-based relations found in predictions ===")
        pass

def eval_submission_6_4_ternary_mention_RE(path):
    try:
        with open(path, 'r', encoding='utf-8') as file:
            predictions = json.load(file)
    except OSError:
        raise OSError(f'Error in opening the specified json file: {path}')

    # Remove duplicated ternary mention-based relations
    remove_duplicated_ternary_mention_relations(predictions)
    
    ground_truth_ternary_mention_RE = dict()
    count_annotated_relations_per_label = {}

    for pmid, article in ground_truth.items():
        if pmid not in ground_truth_ternary_mention_RE:
            ground_truth_ternary_mention_RE[pmid] = []
        for relation in article['ternary_mention_based_relations']:
            subject_text_span = str(relation["subject_text_span"])
            subject_label = str(relation["subject_label"])
            predicate = str(relation["predicate"])
            object_text_span = str(relation["object_text_span"])
            object_label = str(relation["object_label"]) 

            entry = (subject_text_span, subject_label, predicate, object_text_span, object_label)
            ground_truth_ternary_mention_RE[pmid].append(entry)

            label = (subject_label, predicate, object_label)
            if label not in count_annotated_relations_per_label:
                count_annotated_relations_per_label[label] = 0
            count_annotated_relations_per_label[label] += 1

    count_predicted_relations_per_label = {label: 0 for label in list(count_annotated_relations_per_label.keys())}
    count_true_positives_per_label = {label: 0 for label in list(count_annotated_relations_per_label.keys())}
    
    for pmid in predictions.keys():
        try:
            relations = predictions[pmid]['ternary_mention_based_relations']
        except KeyError:
            raise KeyError(f'{pmid} - Not able to find field \"ternary_mention_based_relations\" within article')
        
        for relation in relations:
            try:
                subject_text_span = str(relation["subject_text_span"])
                subject_label = str(relation["subject_label"])
                predicate = str(relation["predicate"])
                object_text_span = str(relation["object_text_span"])
                object_label = str(relation["object_label"]) 
            except KeyError:
                raise KeyError(f'{pmid} - Not able to find one or more of the expected fields for relation: {relation}')
            
            if subject_label not in LEGAL_ENTITY_LABELS:
                raise NameError(f'{pmid} - Illegal subject entity label {subject_label} for relation: {relation}')
            
            if object_label not in LEGAL_ENTITY_LABELS:
                raise NameError(f'{pmid} - Illegal object entity label {object_label} for relation: {relation}')
            
            if predicate not in LEGAL_RELATION_LABELS:
                raise NameError(f'{pmid} - Illegal predicate {predicate} for relation: {relation}')
                        
            entry = (subject_text_span, subject_label, predicate, object_text_span, object_label)
            label = (subject_label, predicate, object_label) 
            
            if label in count_predicted_relations_per_label:
                count_predicted_relations_per_label[label] += 1
            
            if entry in ground_truth_ternary_mention_RE[pmid]:
                count_true_positives_per_label[label] += 1
    
    count_annotated_relations = sum(count_annotated_relations_per_label[label] for label in list(count_annotated_relations_per_label.keys()))
    count_predicted_relations = sum(count_predicted_relations_per_label[label] for label in list(count_annotated_relations_per_label.keys()))
    count_true_positives = sum(count_true_positives_per_label[label] for label in list(count_annotated_relations_per_label.keys()))

    micro_precision = count_true_positives / (count_predicted_relations + 1e-10)
    micro_recall = count_true_positives / (count_annotated_relations + 1e-10)
    micro_f1 = 2 * ((micro_precision * micro_recall) / (micro_precision + micro_recall + 1e-10))

    precision, recall, f1 = 0, 0, 0
    n = 0
    for label in list(count_annotated_relations_per_label.keys()):
        n += 1
        current_precision = count_true_positives_per_label[label] / (count_predicted_relations_per_label[label] + 1e-10) 
        current_recall = count_true_positives_per_label[label] / (count_annotated_relations_per_label[label] + 1e-10) 
        
        precision += current_precision
        recall += current_recall
        f1 += 2 * ((current_precision * current_recall) / (current_precision + current_recall + 1e-10))
    
    precision = precision / n
    recall = recall / n
    f1 = f1 / n

    return precision, recall, f1, micro_precision, micro_recall, micro_f1


if __name__ == '__main__':
    round_to_decimal_position = 4

    if eval_6_1_NER:
        precision, recall, f1, micro_precision, micro_recall, micro_f1 = eval_submission_6_1_NER(PREDICTIONS_PATH_6_1)
        print("\n\n=== 6_1_NER ===")
        print(f"Macro-precision: {round(precision, round_to_decimal_position)}")
        print(f"Macro-recall: {round(recall, round_to_decimal_position)}")
        print(f"Macro-F1: {round(f1, round_to_decimal_position)}")
        print(f"Micro-precision: {round(micro_precision, round_to_decimal_position)}")
        print(f"Micro-recall: {round(micro_recall, round_to_decimal_position)}")
        print(f"Micro-F1: {round(micro_f1, round_to_decimal_position)}")

    if eval_6_2_binary_tag_RE:
        precision, recall, f1, micro_precision, micro_recall, micro_f1 = eval_submission_6_2_binary_tag_RE(PREDICTIONS_PATH_6_2)
        print("\n\n=== 6_2_binary_tag_RE ===")
        print(f"Macro-precision: {round(precision, round_to_decimal_position)}")
        print(f"Macro-recall: {round(recall, round_to_decimal_position)}")
        print(f"Macro-F1: {round(f1, round_to_decimal_position)}")
        print(f"Micro-precision: {round(micro_precision, round_to_decimal_position)}")
        print(f"Micro-recall: {round(micro_recall, round_to_decimal_position)}")
        print(f"Micro-F1: {round(micro_f1, round_to_decimal_position)}")

    if eval_6_3_ternary_tag_RE:
        precision, recall, f1, micro_precision, micro_recall, micro_f1 = eval_submission_6_3_ternary_tag_RE(PREDICTIONS_PATH_6_3)
        print("\n\n=== 6_3_ternary_tag_RE ===")
        print(f"Macro-precision: {round(precision, round_to_decimal_position)}")
        print(f"Macro-recall: {round(recall, round_to_decimal_position)}")
        print(f"Macro-F1: {round(f1, round_to_decimal_position)}")
        print(f"Micro-precision: {round(micro_precision, round_to_decimal_position)}")
        print(f"Micro-recall: {round(micro_recall, round_to_decimal_position)}")
        print(f"Micro-F1: {round(micro_f1, round_to_decimal_position)}")

    if eval_6_4_ternary_mention_RE:
        precision, recall, f1, micro_precision, micro_recall, micro_f1 = eval_submission_6_4_ternary_mention_RE(PREDICTIONS_PATH_6_4)
        print("\n\n=== 6_4_ternary_mention_RE ===")
        print(f"Macro-precision: {round(precision, round_to_decimal_position)}")
        print(f"Macro-recall: {round(recall, round_to_decimal_position)}")
        print(f"Macro-F1: {round(f1, round_to_decimal_position)}")
        print(f"Micro-precision: {round(micro_precision, round_to_decimal_position)}")
        print(f"Micro-recall: {round(micro_recall, round_to_decimal_position)}")
        print(f"Micro-F1: {round(micro_f1, round_to_decimal_position)}")
