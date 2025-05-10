import yaml
import json

def extract_named_entity_classes():
    # Load the JSON file
    json_file = 'generated/schema.json'
    with open(json_file, 'r') as file:
        data = json.load(file)
    
    # Extract classes with is_a = "NamedEntity"
    named_entity_classes = {
        class_name: details
        for class_name, details in data.get('classes', {}).items()
        if details.get('is_a') == "NamedEntity"
    }
    
    return named_entity_classes