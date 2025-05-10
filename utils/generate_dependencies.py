import json
import os

def generate_dependencies(input_file="generated/schema.json", output_file="generated/class_dependencies.json"):
    """
    Generate dependencies for all classes in the input schema, excluding classes where is_a = RelationshipType.

    Args:
        input_file (str): Path to the schema.json file.
        output_file (str): Path to save the generated class dependencies JSON.

    Returns:
        None: Saves the dependencies JSON file inside the generated directory.
    """
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # Load schema JSON
    try:
        with open(input_file, "r") as file:
            schema_data = json.load(file)
    except FileNotFoundError:
        print(f"❌ ERROR: The input file '{input_file}' was not found.")
        return
    except json.JSONDecodeError:
        print(f"❌ ERROR: Failed to parse JSON in '{input_file}'. Please check the file format.")
        return

    classes = schema_data.get("classes", {})
    dependencies_output = {}

    print("🔍 Extracting class dependencies...")

    for class_name, class_details in classes.items():
        is_a = class_details.get("is_a", "")
        
        # Skip classes where is_a is "RelationshipType"
        if is_a == "RelationshipType":
            continue

        dependencies = []

        # Handle inheritance (is_a)
        if is_a and is_a in classes:  # If is_a refers to another class
            dependencies.append(is_a)

        # Handle relationships in "Triple" classes
        if is_a == "Triple":
            attributes = class_details.get("attributes", {})
            subject = attributes.get("subject", {}).get("range", "")
            object_ = attributes.get("object", {}).get("range", "")

            if subject:
                dependencies.append(subject)
            if object_:
                dependencies.append(object_)

        # Store dependencies if found
        dependencies_output[class_name] = {"dependencies": dependencies}

        print(f"   ✅ {class_name}: {dependencies if dependencies else 'No dependencies found'}")

    # Save the generated dependencies JSON
    with open(output_file, "w") as file:
        json.dump(dependencies_output, file, indent=4)

    print(f"\n🎯 **Class dependencies successfully generated!**")
    print(f"📂 **Input File:** {input_file}")
    print(f"📂 **Output File:** {output_file}")
