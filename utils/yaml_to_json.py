import yaml
import json
import os

# Convert enums to a valid JSON structure
def process_enums(enums):
    processed_enums = {}
    for enum_name, enum_details in enums.items():
        permissible_values = enum_details.get("permissible_values", {})
        processed_enums[enum_name] = {
            "type": "string",
            "enum": list(permissible_values.keys())
        }
    return processed_enums

# Load YAML and convert to JSON
def yaml_to_json(yaml_file="input/schema.yaml", json_file="generated/schema.json"):
    """
    Converts a YAML file to JSON and saves it inside the 'generated/' directory.

    Args:
        yaml_file (str): Path to the input YAML file.
        json_file (str): Path to save the output JSON file.

    Returns:
        None
    """
    try:
        # Ensure the output directory exists
        os.makedirs(os.path.dirname(json_file), exist_ok=True)

        # Load YAML data
        with open(yaml_file, 'r') as file:
            yaml_data = yaml.safe_load(file)

        # Process enums
        if "enums" in yaml_data:
            yaml_data["enums"] = process_enums(yaml_data["enums"])

        # Save to JSON file
        with open(json_file, 'w') as file:
            json.dump(yaml_data, file, indent=4)

        # Print success message
        print(f"✅ YAML successfully converted to JSON!\n - Input: {yaml_file}\n - Output: {json_file}")

    except FileNotFoundError:
        print(f"❌ Error: The file {yaml_file} was not found.")
    except yaml.YAMLError as e:
        print(f"❌ YAML Parsing Error: {e}")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
