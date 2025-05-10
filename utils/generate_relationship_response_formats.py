import json

def generate_relationship_response_format(schema_path, output_format_path, two_dependency_classes):
    """
    Generate a single response format for relationship-type classes based on schema definitions.

    Args:
        schema_path (str): Path to the JSON schema file.
        output_format_path (str): Path to save the generated response format.
        two_dependency_classes (dict): Dictionary containing relationship-type classes (with exactly two dependencies).
    
    Returns:
        None: Saves the response format JSON.
    """
    with open(schema_path, "r") as file:
        schema = json.load(file)

    relationship_formats = {}

    for class_name, dependencies in two_dependency_classes.items():
        class_data = schema["classes"].get(class_name, {})
        attributes = class_data.get("attributes", {})

        properties = {}
        required_fields = []

        # ✅ Dynamically Extract Predicate Enum Value
        predicate_values = []
        predicate_range = attributes.get("predicate", {}).get("range", None)

        if predicate_range and predicate_range in schema["classes"]:
            predicate_class_info = schema["classes"][predicate_range]
            predicate_id = predicate_class_info.get("attributes", {}).get("id", {}).get("pattern", None)

            if predicate_id:
                predicate_values = [p.strip().strip("^$") for p in predicate_id.split("|")]

        for attr_name, attr_data in attributes.items():
            attr_type = attr_data.get("range", "string").lower()  # Default to string if not specified

            if attr_name == "predicate" and predicate_values:
                field_type = {"type": "string", "enum": predicate_values}  # ✅ Add enum for predicate
            elif attr_type == "date":
                field_type = {"type": "string"}
            elif attr_type in schema["classes"]:  # If it's a reference to another class
                field_type = {"type": "string"}  # IDs of referenced classes should be string
            else:
                field_type = {"type": "number"} if attr_type in ["integer", "float"] else {"type": "string"}

            properties[attr_name] = field_type
            required_fields.append(attr_name)

        response_format = {
            "responseFormat": {
                "type": "json_schema",
                "json_schema": {
                    "name": f"{class_name}_instances",
                    "schema": {
                        "type": "object",
                        "properties": {
                            f"{class_name}Relationships": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": properties,
                                    "required": required_fields,
                                    "additionalProperties": False
                                }
                            }
                        },
                        "required": [f"{class_name}Relationships"],
                        "additionalProperties": False
                    },
                    "strict": True
                }
            }
        }

        relationship_formats[class_name] = response_format

    with open(output_format_path, "w") as file:
        json.dump(relationship_formats, file, indent=4)

    print(f"Generated response formats saved to {output_format_path}")


