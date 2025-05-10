import json
import os
from openai import OpenAI



def process_inherited_entity_classes(
    schema, responses_file, text, response_formats_path, 
    output_responses_path, prompts_save_path, single_dependency_classes
):
    """
    Process inherited entity classes by generating prompts, calling GPT, and saving results.

    Args:
        schema (dict): The schema containing class definitions.
        responses_file (str): Path to the JSON file with existing responses.
        text (str): The input text to process.
        response_formats_path (str): Path to the response formats JSON file.
        output_responses_path (str): Path to save the output responses.
        prompts_save_path (str): Path to save the generated prompts.
        single_dependency_classes (dict): Classes with a single inheritance dependency.
    """
    print("\n🚀 Processing inherited entity classes...\n")
    
    # Ensure the prompts directory exists
    os.makedirs(os.path.dirname(prompts_save_path), exist_ok=True)

    # Load responses and response formats
    with open(responses_file, "r") as file:
        responses = json.load(file)

    with open(response_formats_path, "r") as schema_file:
        response_formats = json.load(schema_file)

    combined_responses = responses
    generated_prompts = {}

    # Extract schema title and description for context
    schema_title = schema.get("title", "")
    schema_description = schema.get("description", "")
    schema_intro = (
        f"The schema is titled '{schema_title}' and described as follows: {schema_description}."
        if schema_title and schema_description
        else f"the schema is described as follows: {schema_description}."
        if schema_description
        else f"The schema is titled '{schema_title}'"
        if schema_title
        else ""
    )

    # Process each inherited class
    for child_class, parent_class in single_dependency_classes.items():
        print(f"\n🔹 Processing '{child_class}' (Child of '{parent_class}')...\n")

        # Get information for child and parent classes
        child_info = schema["classes"].get(child_class, {})
        parent_info = schema["classes"].get(parent_class, {})
        child_attributes = child_info.get("attributes", {})
        parent_attributes = parent_info.get("attributes", {})
        
        parent_identifier_key = None
        for attr_name, attr_details in parent_attributes.items():
            if attr_details.get("identifier", False):
                parent_identifier_key = attr_name
                break

        # ✅ Retrieve parent instances dynamically
        parent_instances = responses.get(parent_class, {}).get("schemaResponse", {}).get(parent_identifier_key, [])
        
        # Skip if parent instances are missing
        if not parent_instances:
            print(f"⚠️ Skipping '{child_class}' because parent class '{parent_class}' has no instances.")
            continue

        # Generate Schema Prompt
        child_description = child_info.get("description", f"A '{child_class}' instance.")
        if child_description:
          class_desc="A '{child_class}' is defined as: {child_description}."
        else:
            class_desc=''
        schema_prompt = (
            f"{schema_intro} Extract all instances of class '{child_class}' that are **explicitly mentioned in the provided text**.  **If a protein is not explicitly written in the text, do not include it in the response, even if it is commonly associated with the entities mentioned.**  The extraction should be strictly limited to the words present in the text. "
            f"{class_desc}"
            f"Instances of this class are specializations of the parent class '{parent_class}', "
            f"which include the following parent entities: {', '.join(parent_instances)}. "
            f"While all instances of '{child_class}' are derived from '{parent_class}', not all entities of the parent class are necessarily members of the child class. "
            f"Return a list of all {parent_identifier_key} values for the class {child_class}"
        )

        # Generate Attribute Prompt
        attribute_descriptions = [
            f"{attr_name} ({attr_details.get('description', '')})" 
            if attr_details.get("description") else attr_name
            for attr_name, attr_details in {**parent_attributes, **child_attributes}.items()
        ]
        
        attribute_prompt = (
            f"For each {parent_identifier_key} identified as an instance of class '{child_class}', extract the following attributes: "
            f"{', '.join(attribute_descriptions)}. "
            f"Include all inherited attributes from the parent class '{parent_class}' and their respective values. "
        )

        # Extract response formats
        schema_response_format = response_formats.get(child_class, {}).get("schemaResponseFormat", None)
        attribute_response_format = response_formats.get(child_class, {}).get("attributeResponseFormat", None)

        combined_responses[child_class] = {"schemaResponse": None, "attributeResponse": None}
        extracted_labels = []

        # Call GPT for Schema Response
        if schema_response_format:
            try:
                schema_response = client.chat.completions.create(
                    model="gpt-4o-2024-08-06",
                    messages=[
                        {"role": "system", "content": "You are an expert in entity and relation extraction from plain text."},
                        {"role": "user", "content": schema_prompt},
                        {"role": "user", "content": f"Text:\n{text}"}
                    ],
                    response_format={"type": "json_schema", "json_schema": schema_response_format["json_schema"]}
                )
                schema_response_json = json.loads(schema_response.choices[0].message.content)
                combined_responses[child_class]["schemaResponse"] = schema_response_json
                extracted_labels = list(schema_response_json.values())[0] if schema_response_json else []
                print(f"✅ Entity extraction completed for '{child_class}'")
            except Exception as e:
                print(f"❌ Error processing schemaPrompt for {child_class}: {e}")

        # Call GPT for Attribute Response
        if attribute_response_format:
            try:
                if extracted_labels:
                    attribute_prompt += f"The identifiers should match the Identified entities in the previous step: {', '.join(extracted_labels)}."
                attribute_response = client.chat.completions.create(
                    model="gpt-4o-2024-08-06",
                    messages=[
                        {"role": "system", "content": "You are an expert in entity and relation extraction from plain text."},
                        {"role": "user", "content": attribute_prompt},
                        {"role": "user", "content": f"Text:\n{text}"}
                    ],
                    response_format={"type": "json_schema", "json_schema": attribute_response_format["json_schema"]}
                )
                combined_responses[child_class]["attributeResponse"] = json.loads(attribute_response.choices[0].message.content)
                print(f"✅ Attributes extraction completed for '{child_class}'")
            except Exception as e:
                print(f"❌ Error processing attributePrompt for {child_class}: {e}")

        # Save responses
        with open(output_responses_path, "w") as response_file:
            json.dump(combined_responses, response_file, indent=4)
        print(f"✅ Responses saved to {output_responses_path}")

        # Save prompts for this class
        generated_prompts[child_class] = {
            "schemaPrompts": schema_prompt,
            "attributePrompts": attribute_prompt
        }

        # Save prompts incrementally to avoid losing progress
        with open(prompts_save_path, "w") as prompts_file:
            json.dump(generated_prompts, prompts_file, indent=4)

    print(f"\n✅ Prompts for inherited classes saved to {prompts_save_path}.")



def process_inherited_entity_classes_without_dependencies(schema, responses_file, text, response_formats_path, 
    output_responses_path, prompts_save_path, single_dependency_classes):
    print("\n🚀 Processing inherited entity classes...\n")
    
    # Ensure the prompts directory exists
    os.makedirs(os.path.dirname(prompts_save_path), exist_ok=True)

    # Load responses and response formats
    with open(responses_file, "r") as file:
        responses = json.load(file)

    with open(response_formats_path, "r") as schema_file:
        response_formats = json.load(schema_file)

    combined_responses = responses
    generated_prompts = {}

    # Extract schema title and description for context
    schema_title = schema.get("title", "")
    schema_description = schema.get("description", "")
    schema_intro = (
        f"The schema is titled '{schema_title}' and described as follows: {schema_description}."
        if schema_title and schema_description
        else f"the schema is described as follows: {schema_description}."
        if schema_description
        else f"The schema is titled '{schema_title}'"
        if schema_title
        else ""
    )

    # Process each inherited class
    for child_class, parent_class in single_dependency_classes.items():
        print(f"\n🔹 Processing '{child_class}' (Child of '{parent_class}')...\n")

        # Get information for child and parent classes
        child_info = schema["classes"].get(child_class, {})
        parent_info = schema["classes"].get(parent_class, {})
        child_attributes = child_info.get("attributes", {})
        parent_attributes = parent_info.get("attributes", {})
        
        parent_identifier_key = None
        for attr_name, attr_details in parent_attributes.items():
            if attr_details.get("identifier", False):
                parent_identifier_key = attr_name
                break

        # ✅ Retrieve parent instances dynamically
        # parent_instances = responses.get(parent_class, {}).get("schemaResponse", {}).get(parent_identifier_key, [])
        
        # # Skip if parent instances are missing
        # if not parent_instances:
        #     print(f"⚠️ Skipping '{child_class}' because parent class '{parent_class}' has no instances.")
        #     continue

        # Generate Schema Prompt
        child_description = child_info.get("description", f"A '{child_class}' instance.")
        if child_description:
          class_desc=f"A '{child_class}' is defined as: {child_description}."
        else:
            class_desc=''
        schema_prompt = (
            f"{schema_intro} Extract all instances of class '{child_class}' that are **explicitly mentioned in the provided text**.  **If a protein is not explicitly written in the text, do not include it in the response, even if it is commonly associated with the entities mentioned.**  The extraction should be strictly limited to the words present in the text. "               f"{class_desc}"
            # f"Instances of this class are specializations of the parent class '{parent_class}', "
            # f"which include the following parent entities: {', '.join(parent_instances)}. "
            # f"While all instances of '{child_class}' are derived from '{parent_class}', not all entities of the parent class are necessarily members of the child class. "
            f"Return a list of all {parent_identifier_key} values for the class {child_class}"
        )

        # Generate Attribute Prompt
        attribute_descriptions = [
            f"{attr_name} ({attr_details.get('description', '')})" 
            if attr_details.get("description") else attr_name
            for attr_name, attr_details in {**parent_attributes, **child_attributes}.items()
        ]
        
        attribute_prompt = (
            f"For each {parent_identifier_key} identified as an instance of class '{child_class}', extract the following attributes: "
            f"{', '.join(attribute_descriptions)}. "
        )

        # Extract response formats
        schema_response_format = response_formats.get(child_class, {}).get("schemaResponseFormat", None)
        attribute_response_format = response_formats.get(child_class, {}).get("attributeResponseFormat", None)

        combined_responses[child_class] = {"schemaResponse": None, "attributeResponse": None}
        extracted_labels = []

        # Call GPT for Schema Response
        if schema_response_format:
            try:
                schema_response = client.chat.completions.create(
                    model="gpt-4o-2024-08-06",
                    messages=[
                        {"role": "system", "content": "You are an expert in entity and relation extraction from plain text."},
                        {"role": "user", "content": schema_prompt},
                        {"role": "user", "content": f"Text:\n{text}"}
                    ],
                    response_format={"type": "json_schema", "json_schema": schema_response_format["json_schema"]}
                )
                schema_response_json = json.loads(schema_response.choices[0].message.content)
                combined_responses[child_class]["schemaResponse"] = schema_response_json
                extracted_labels = list(schema_response_json.values())[0] if schema_response_json else []
                print(f"✅ Entity extraction completed for '{child_class}'")
            except Exception as e:
                print(f"❌ Error processing schemaPrompt for {child_class}: {e}")

        # Call GPT for Attribute Response
        if attribute_response_format:
            try:
                attribute_prompt = f"{attribute_prompt}. The identifiers should match the Identified entities in the previous step: {', '.join(extracted_labels)}."
                attribute_response = client.chat.completions.create(
                    model="gpt-4o-2024-08-06",
                    messages=[
                        {"role": "system", "content": "You are an expert in entity and relation extraction from plain text."},
                        {"role": "user", "content": attribute_prompt},
                        {"role": "user", "content": f"Text:\n{text}"}
                    ],
                    response_format={"type": "json_schema", "json_schema": attribute_response_format["json_schema"]}
                )
                combined_responses[child_class]["attributeResponse"] = json.loads(attribute_response.choices[0].message.content)
                print(f"✅ Attributes extraction completed for '{child_class}'")
            except Exception as e:
                print(f"❌ Error processing attributePrompt for {child_class}: {e}")

        # Save responses
        with open(output_responses_path, "w") as response_file:
            json.dump(combined_responses, response_file, indent=4)
        print(f"✅ Responses saved to {output_responses_path}")

        # Save prompts for this class
        generated_prompts[child_class] = {
            "schemaPrompts": schema_prompt,
            "attributePrompts": attribute_prompt
        }

        # Save prompts incrementally to avoid losing progress
        with open(prompts_save_path, "w") as prompts_file:
            json.dump(generated_prompts, prompts_file, indent=4)

    print(f"\n✅ Prompts for inherited classes saved to {prompts_save_path}.")
    


