import json
from openai import OpenAI

# Initialize OpenAI client

def call_gpt_for_relationship_extraction(
    response_formats_path, text_sample_path, prompts_save_path, 
    two_dependency_classes, schema_path, generated_responses_path
):
    """
    Call GPT to process relationship-type entity extraction using generated response formats.
    Constructs a fully dynamic prompt using schema details and identified instances.

    Args:
        response_formats_path (str): Path to the response formats JSON file.
        text_sample_path (str): Path to the text sample file.
        prompts_save_path (str): Path to save the generated prompts.
        two_dependency_classes (dict): Dictionary containing relationship-type classes.
        schema_path (str): Path to the JSON schema file.
        generated_responses_path (str): Path to the file containing previously identified instances.

    Returns:
        None: Saves the generated responses and prompts.
    """
    # Load response formats
    with open(response_formats_path, "r") as schema_file:
        response_formats = json.load(schema_file)

    # Load schema
    with open(schema_path, "r") as schema_file:
        schema = json.load(schema_file)

    # Load identified instances from previous entity extraction
    with open(generated_responses_path, "r") as responses_file:
        existing_responses = json.load(responses_file)

    # Load text sample
    with open(text_sample_path, "r") as file:
        text = file.read()

    combined_responses = {}
    generated_prompts = {}

    # Process only relationship-type classes (from two_dependency_classes)
    for class_name in two_dependency_classes.keys():
        if class_name in response_formats:
            response_format = response_formats[class_name].get("responseFormat", None)

            if response_format:
                # Extract details from schema
                class_info = schema["classes"].get(class_name, {})
                subject_info = class_info["attributes"].get("subject", {})
                object_info = class_info["attributes"].get("object", {})
                predicate_class = class_info["attributes"].get("predicate", {}).get("range", "")

                    # Extract schema title and description
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

                subject_class = subject_info.get("range", "")
                object_class = object_info.get("range", "")

                # Retrieve predicate value
                predicate_value = schema["classes"].get(predicate_class, {}).get("attributes", {}).get("id", {}).get("pattern", "")

                # ✅ Extract cardinalities dynamically (if they exist)
                subject_min_cardinality = subject_info.get("minimum_cardinality")
                subject_max_cardinality = subject_info.get("maximum_cardinality")

                object_min_cardinality = object_info.get("minimum_cardinality")
                object_max_cardinality = object_info.get("maximum_cardinality")

                # Extract attributes and their descriptions
                attribute_details = [
                    f"{attr_name} ({attr_info.get('description', '')})"
                    for attr_name, attr_info in class_info.get("attributes", {}).items()
                    if attr_name not in ["subject", "object", "predicate"]  # Exclude relationship keys
                ]

                # Extract identified instances of subject and object from generated_responses.json
                subject_instances = existing_responses.get(subject_class, {}).get("schemaResponse", {})
                subject_identifiers = list(subject_instances.values())[0] if subject_instances else []

                object_instances = existing_responses.get(object_class, {}).get("schemaResponse", {})
                object_identifiers = list(object_instances.values())[0] if object_instances else []

                # ✅ Construct dynamic prompt
                description_text = f"The '{predicate_value}' relationship is described as follows: \"{class_info.get('description', '')}\"\n" if class_info.get("description") else ""
                prompt = (
                    f"{schema_intro} Your task is to extract relationships of predicate '{predicate_value}' (and its synonyms) between entities of class '{subject_class}' and '{object_class}' "
                    f"that are **explicitly mentioned in the provided text**.  **If a protein is not explicitly written in the text, do not include it in the response, even if it is commonly associated with the entities mentioned.** The extraction should be strictly limited to the words present in the text."
                    f"{description_text}"
                    f"From the text below, you have to identify and extract relationships of predicate '{predicate_value}' among instances: "
                    f"{', '.join(subject_identifiers)} of the class '{subject_class}' and instances {', '.join(object_identifiers)} of the class '{object_class}'. "
                    f"Entities involved in '{predicate_value}' relationships must belong to these sets.\n"
                )

                # ✅ Only include cardinality constraints if they exist
                if (subject_min_cardinality is not None and subject_max_cardinality is not None) or \
                   (object_min_cardinality is not None and object_max_cardinality is not None):

                    prompt += "Cardinality constraints:\n"

                    if subject_min_cardinality is not None and subject_max_cardinality is not None:
                        prompt += (
                            f"- A '{object_class}' can be followed by a minimum of {subject_min_cardinality} and a maximum of {subject_max_cardinality} '{subject_class}'.\n"
                        )

                    if object_min_cardinality is not None and object_max_cardinality is not None:
                        prompt += (
                            f"- A '{subject_class}' can follow a minimum of {object_min_cardinality} and a maximum of {object_max_cardinality} '{object_class}'.\n"
                        )

                    prompt += "\n"

                # ✅ Add extracted attributes
                prompt += f"Extract and include the following attributes for each relationship:\n{', '.join(attribute_details)}.\n"

                # Save the prompt for this class
                generated_prompts[class_name] = prompt

                try:
                    print(f"Processing relationship extraction for class: {class_name}")
                    schema_response = client.chat.completions.create(
                        model="gpt-4o-2024-08-06",
                        messages=[
                            {"role": "system", "content": "You are an expert in entity and relation extraction from plain text."},
                            {"role": "user", "content": prompt},
                            {"role": "user", "content": f"Text:\n{text}"}
                        ],
                        response_format=response_format
                    )

                    combined_responses[class_name] = json.loads(schema_response.choices[0].message.content)
                    print(f"✅ Result for {class_name}: {combined_responses[class_name]}")
                except Exception as e:
                    print(f"❌ Error processing {class_name}: {e}")

    # ✅ Append responses to existing `generated_responses.json`
    existing_responses.update(combined_responses)
    with open(generated_responses_path, "w") as output_file:
        json.dump(existing_responses, output_file, indent=4)

    # Save prompts
    with open(prompts_save_path, "w") as prompts_file:
        json.dump(generated_prompts, prompts_file, indent=4)

    print(f"✅ All responses appended and saved to {generated_responses_path}.")
    print(f"✅ All prompts saved to {prompts_save_path}.")



def call_gpt_for_relationship_extraction_without_dependencies(
    response_formats_path, text_sample_path, prompts_save_path, 
    two_dependency_classes, schema_path, generated_responses_path
):
    """
    Call GPT to process relationship-type entity extraction using generated response formats.
    Constructs a fully dynamic prompt using schema details and identified instances.

    Args:
        response_formats_path (str): Path to the response formats JSON file.
        text_sample_path (str): Path to the text sample file.
        prompts_save_path (str): Path to save the generated prompts.
        two_dependency_classes (dict): Dictionary containing relationship-type classes.
        schema_path (str): Path to the JSON schema file.
        generated_responses_path (str): Path to the file containing previously identified instances.

    Returns:
        None: Saves the generated responses and prompts.
    """
    # Load response formats
    with open(response_formats_path, "r") as schema_file:
        response_formats = json.load(schema_file)

    # Load schema
    with open(schema_path, "r") as schema_file:
        schema = json.load(schema_file)

    # Load identified instances from previous entity extraction
    with open(generated_responses_path, "r") as responses_file:
        existing_responses = json.load(responses_file)

    # Load text sample
    with open(text_sample_path, "r") as file:
        text = file.read()

    combined_responses = {}
    generated_prompts = {}

    # Process only relationship-type classes (from two_dependency_classes)
    for class_name in two_dependency_classes.keys():
        if class_name in response_formats:
            response_format = response_formats[class_name].get("responseFormat", None)

            if response_format:
                # Extract details from schema
                class_info = schema["classes"].get(class_name, {})
                subject_info = class_info["attributes"].get("subject", {})
                object_info = class_info["attributes"].get("object", {})
                predicate_class = class_info["attributes"].get("predicate", {}).get("range", "")

                    # Extract schema title and description
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

                subject_class = subject_info.get("range", "")
                object_class = object_info.get("range", "")

                subject_description = schema["classes"].get(subject_class, {}).get("description", "")
                object_description = schema["classes"].get(object_class, {}).get("description", "")

                subject_desc_text = f"A '{subject_class}' is defined as: {subject_description}.\n" if subject_description else ""
                object_desc_text = f"A '{object_class}' is defined as: {object_description}.\n" if object_description else ""

                # Retrieve predicate value
                predicate_value = schema["classes"].get(predicate_class, {}).get("attributes", {}).get("id", {}).get("pattern", "")

                predicate_parts = predicate_value.split("|")
                if len(predicate_parts) > 1:
                    predicate_text = (
                        f"The relationship can be described by one or more of the following predicate values: "
                        f"**{'**, **'.join(predicate_parts)}**. Identify and extract only the predicates that are explicitly mentioned in the text."
                    )
                else:
                    predicate_text = f"The '{predicate_value}' relationship is described as follows: \"{class_info.get('description', '')}\""


                # ✅ Extract cardinalities dynamically (if they exist)
                subject_min_cardinality = subject_info.get("minimum_cardinality")
                subject_max_cardinality = subject_info.get("maximum_cardinality")

                object_min_cardinality = object_info.get("minimum_cardinality")
                object_max_cardinality = object_info.get("maximum_cardinality")

                # Extract attributes and their descriptions
                attribute_details = [
                    f"{attr_name} ({attr_info.get('description', '')})"
                    for attr_name, attr_info in class_info.get("attributes", {}).items()
                    if attr_name not in ["subject", "object", "predicate"]  # Exclude relationship keys
                ]

                # Extract identified instances of subject and object from generated_responses.json
                subject_instances = existing_responses.get(subject_class, {}).get("schemaResponse", {})
                subject_identifiers = list(subject_instances.values())[0] if subject_instances else []

                object_instances = existing_responses.get(object_class, {}).get("schemaResponse", {})
                object_identifiers = list(object_instances.values())[0] if object_instances else []

                # ✅ Construct dynamic prompt
                description_text = f"The '{predicate_value}' relationship is described as follows: \"{class_info.get('description', '')}\"\n" if class_info.get("description") else ""
                prompt = (
                    f"{schema_intro} Your task is to extract relationships of predicate '{predicate_value}' (and its synonyms) between entities of class '{subject_class}' and '{object_class}' "
                    f"that are **explicitly mentioned in the provided text**.  **If a protein is not explicitly written in the text, do not include it in the response, even if it is commonly associated with the entities mentioned.** The extraction should be strictly limited to the words present in the text."
                    f"{predicate_text}\n"
                    f"{subject_desc_text}"
                    f"{object_desc_text}"
                )

                # ✅ Only include cardinality constraints if they exist
                if (subject_min_cardinality is not None and subject_max_cardinality is not None) or \
                   (object_min_cardinality is not None and object_max_cardinality is not None):

                    prompt += "Cardinality constraints:\n"

                    if subject_min_cardinality is not None and subject_max_cardinality is not None:
                        prompt += (
                            f"- A '{object_class}' can be followed by a minimum of {subject_min_cardinality} and a maximum of {subject_max_cardinality} '{subject_class}'.\n"
                        )

                    if object_min_cardinality is not None and object_max_cardinality is not None:
                        prompt += (
                            f"- A '{subject_class}' can follow a minimum of {object_min_cardinality} and a maximum of {object_max_cardinality} '{object_class}'.\n"
                        )

                    prompt += "\n"

                # ✅ Add extracted attributes
                prompt += f"Extract and include the following attributes for each relationship:\n{', '.join(attribute_details)}.\n"

                # Save the prompt for this class
                generated_prompts[class_name] = prompt

                try:
                    print(f"Processing relationship extraction for class: {class_name}")
                    schema_response = client.chat.completions.create(
                        model="gpt-4o-2024-08-06",
                        messages=[
                            {"role": "system", "content": "You are an expert in entity and relation extraction from plain text."},
                            {"role": "user", "content": prompt},
                            {"role": "user", "content": f"Text:\n{text}"}
                        ],
                        response_format=response_format
                    )

                    combined_responses[class_name] = json.loads(schema_response.choices[0].message.content)
                    print(f"✅ Result for {class_name}: {combined_responses[class_name]}")
                except Exception as e:
                    print(f"❌ Error processing {class_name}: {e}")

    # ✅ Append responses to existing `generated_responses.json`
    existing_responses.update(combined_responses)
    with open(generated_responses_path, "w") as output_file:
        json.dump(existing_responses, output_file, indent=4)

    # Save prompts
    with open(prompts_save_path, "w") as prompts_file:
        json.dump(generated_prompts, prompts_file, indent=4)

    print(f"✅ All responses appended and saved to {generated_responses_path}.")
    print(f"✅ All prompts saved to {prompts_save_path}.")


